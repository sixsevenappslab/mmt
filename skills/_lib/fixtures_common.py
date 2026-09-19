"""Turn the synthetic MMM dataset into media rows shaped like a platform export.

`generators/synthetic_mmm.py` emits spend and a business KPI, never impressions or clicks,
and platform exports carry no KPI at all. The fixtures of FEAT-002 need the mirror image, so
this module derives impressions and clicks from spend with an explicit CPM/CTR assumption.

Those CPM and CTR numbers are a fixture assumption, not a measurement: no platform published
them, and nothing here should be read as a benchmark. They exist so a fixture has plausible,
deterministic media columns. The base generator is never modified.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# Fixture-only assumptions, in EUR. Chosen to be plausible per channel, never measured.
DEFAULT_CPM = {"search": 45.0, "social": 8.0, "video": 14.0, "display": 3.5}
DEFAULT_CTR = {"search": 0.055, "social": 0.011, "video": 0.004, "display": 0.0008}


def derive_media_fixture(
    mmm_csv: Path,
    truth_json: Path,
    cpm_by_channel: dict[str, float],
    ctr_by_channel: dict[str, float],
    rng_seed: int,
) -> pd.DataFrame:
    """Read the wide synthetic dataset and return long `date, channel, spend, impressions, clicks`.

    `impressions = spend / cpm * 1000` and `clicks = impressions * ctr`, both with a small
    lognormal wobble so the series are not a deterministic multiple of spend. CPM and CTR are
    a fixture assumption (see module docstring), not data from any platform.
    """
    wide = pd.read_csv(mmm_csv)
    truth = json.loads(Path(truth_json).read_text(encoding="utf-8"))
    channels = list(truth["channels"].keys())
    rng = np.random.default_rng(rng_seed)

    records = []
    for channel in channels:
        spend = wide[f"spend_{channel}"].to_numpy(dtype=float)
        cpm = cpm_by_channel[channel]
        ctr = ctr_by_channel[channel]
        impressions = spend / cpm * 1000.0 * rng.lognormal(0.0, 0.08, len(spend))
        clicks = impressions * ctr * rng.lognormal(0.0, 0.12, len(spend))
        records.append(
            pd.DataFrame(
                {
                    "date": pd.to_datetime(wide["date"]),
                    "channel": channel,
                    "spend": np.round(spend, 2),
                    "impressions": np.rint(impressions).astype(int),
                    "clicks": np.rint(clicks).astype(int),
                }
            )
        )
    frame = pd.concat(records, ignore_index=True)
    return frame.sort_values(["date", "channel"]).reset_index(drop=True)


def explode_to_daily(frame: pd.DataFrame, rng_seed: int) -> pd.DataFrame:
    """Spread each weekly row over its seven days, keeping the weekly totals exact.

    The base generator is weekly; some platform feeds are daily. The split uses a Dirichlet
    draw so the days are uneven, and the last day absorbs the rounding so the week still sums
    to the weekly value.
    """
    rng = np.random.default_rng(rng_seed)
    rows = []
    for record in frame.to_dict("records"):
        weights = rng.dirichlet(np.full(7, 6.0))
        start = pd.Timestamp(record["date"])
        for offset in range(7):
            share = weights[offset]
            spend = round(float(record["spend"]) * share, 2)
            impressions = round(float(record["impressions"]) * share)
            clicks = round(float(record["clicks"]) * share)
            rows.append(
                {
                    "date": start + pd.Timedelta(days=offset),
                    "channel": record["channel"],
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                }
            )
    daily = pd.DataFrame(rows)
    return daily.sort_values(["date", "channel"]).reset_index(drop=True)


def shift_to_sunday_weeks(frame: pd.DataFrame) -> pd.DataFrame:
    """Move Monday-anchored weekly rows to the Sunday that starts the same seven days."""
    shifted = frame.copy()
    shifted["date"] = pd.to_datetime(shifted["date"]) - pd.Timedelta(days=1)
    return shifted
