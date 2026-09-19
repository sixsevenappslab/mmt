"""Build a synthetic Meta MMM export shaped like the Marketing API breakdown.

The header is the candidate one documented for the API, not a confirmed Ads Reporting export,
so this fixture proves the mapping works — not that the contract is right. Every value is
synthetic: the account, campaign and adset identifiers are placeholders, the media numbers
come from `generators/synthetic_mmm.py` plus a stated CPM/CTR assumption, and the currency is
EUR. It is not a trimmed real export.

    python3 skills/import-meta-mmm/fixtures/generate_fixture.py --out /tmp/meta_fixture.csv
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SKILL_DIR.parent / "_lib"))

import fixtures_common
import mmm_import_common as common

from generators.synthetic_mmm import DEFAULT_CHANNELS, generate

META_COLUMNS = [
    "account_id",
    "campaign_id",
    "adset_id",
    "date_start",
    "date_stop",
    "impressions",
    "spend",
    "country",
    "region",
    "dma",
    "device_platform",
    "platform_position",
    "publisher_platform",
    "creative_media_type",
]
# The synthetic paid-social series is the one that stands in for Meta.
SOURCE_CHANNEL = "social"
COUNTRY = "ES"


def build_media_frame(weeks: int, seed: int) -> pd.DataFrame:
    """One daily row per date for the paid-social channel: date, spend, impressions, clicks."""
    wide, truth = generate(weeks, seed, DEFAULT_CHANNELS)
    with tempfile.TemporaryDirectory() as workdir:
        base = Path(workdir) / "base"
        wide.to_csv(base.with_suffix(".csv"), index=False)
        Path(f"{base}.truth.json").write_text(json.dumps(truth))
        frame = fixtures_common.derive_media_fixture(
            base.with_suffix(".csv"),
            Path(f"{base}.truth.json"),
            fixtures_common.DEFAULT_CPM,
            fixtures_common.DEFAULT_CTR,
            rng_seed=seed,
        )
    frame = frame[frame["channel"] == SOURCE_CHANNEL].reset_index(drop=True)
    return fixtures_common.explode_to_daily(frame, rng_seed=seed)


def to_meta_export(frame: pd.DataFrame) -> pd.DataFrame:
    dates = frame["date"].dt.strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "account_id": "SYNTHETIC-ACCOUNT",
            "campaign_id": "SYNTHETIC-CAMPAIGN",
            "adset_id": "SYNTHETIC-ADSET",
            "date_start": dates,
            "date_stop": dates,
            "impressions": frame["impressions"],
            "spend": frame["spend"],
            "country": COUNTRY,
            "region": "",
            "dma": "",
            "device_platform": "mobile_app",
            "platform_position": "feed",
            "publisher_platform": "facebook",
            "creative_media_type": "video",
        }
    ).loc[:, META_COLUMNS]


def to_expected_canonical(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].dt.strftime("%Y-%m-%d"),
            "geo": COUNTRY,
            "channel": "meta",
            "spend": frame["spend"],
            "impressions": frame["impressions"],
            "clicks": pd.NA,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="path of the fixture CSV")
    parser.add_argument("--weeks", type=int, default=4, help="weeks of source data, exploded daily")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--expected-out",
        type=Path,
        default=None,
        help="also write the canonical table the importer must reproduce",
    )
    parser.add_argument("--allow-tracked", action="store_true")
    args = parser.parse_args()

    common.guard_untracked_path(args.out, args.allow_tracked, "salida")
    if args.expected_out is not None:
        common.guard_untracked_path(args.expected_out, args.allow_tracked, "canonico esperado")

    frame = build_media_frame(args.weeks, args.seed)
    export = to_meta_export(frame)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(args.out, index=False)
    print(f"wrote {args.out} ({len(export)} rows, daily)")

    if args.expected_out is not None:
        expected = to_expected_canonical(frame)
        args.expected_out.parent.mkdir(parents=True, exist_ok=True)
        expected.to_csv(args.expected_out, index=False)
        print(f"wrote {args.expected_out} ({len(expected)} rows)")


if __name__ == "__main__":
    main()
