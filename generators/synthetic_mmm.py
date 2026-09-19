"""Generate a synthetic MMM dataset with known ground truth.

The point of a synthetic dataset is that the true contribution of every media channel
is known, so a model can be scored on whether it recovers it. Real data never offers
that. The data generating process here is the standard MMM one:

    kpi[t] = baseline[t] + sum_c beta_c * hill(adstock(spend_c))[t] + controls[t] + noise[t]

- geometric adstock (carryover), one decay rate per channel
- Hill saturation (diminishing returns), one half-saturation point and slope per channel
- baseline = intercept + linear trend + yearly seasonality
- one control variable (price index) with a negative coefficient

Output: a wide weekly CSV ready for Meridian / PyMC-Marketing, plus a JSON with every
true parameter and the true ROI per channel.

Usage:
    python generators/synthetic_mmm.py --weeks 156 --seed 42 --out data/synthetic/base
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Channel:
    """A media channel and the true parameters used to generate its contribution."""

    name: str
    spend_mean: float  # average weekly spend, EUR
    spend_cv: float  # coefficient of variation of the spend series
    flight_prob: float  # probability the channel is active on a given week
    adstock_decay: float  # geometric carryover rate in [0, 1)
    hill_half_sat: float  # adstocked spend at which the response is half of beta
    hill_slope: float  # steepness of the saturation curve
    beta: float  # max incremental KPI units attributable to the channel


DEFAULT_CHANNELS = [
    # Always-on, fast decay, easily saturated: the classic branded search profile.
    Channel("search", 12_000, 0.25, 1.00, 0.20, 6_000, 1.4, 90_000),
    # Bursty, medium carryover: paid social.
    Channel("social", 9_000, 0.55, 0.85, 0.45, 5_000, 1.1, 70_000),
    # Heavily flighted, long carryover, expensive: video / CTV.
    Channel("video", 20_000, 0.70, 0.45, 0.70, 12_000, 1.8, 120_000),
    # Cheap but weak: affiliate / display.
    Channel("display", 4_000, 0.40, 0.90, 0.30, 2_500, 1.0, 18_000),
]


def geometric_adstock(x: np.ndarray, decay: float, max_lag: int = 12) -> np.ndarray:
    """Apply geometric carryover: each week keeps a decayed echo of previous weeks."""
    weights = decay ** np.arange(max_lag + 1)
    weights /= weights.sum()
    padded = np.concatenate([np.zeros(max_lag), x])
    return np.array([np.dot(weights, padded[t : t + max_lag + 1][::-1]) for t in range(len(x))])


def hill(x: np.ndarray, half_sat: float, slope: float) -> np.ndarray:
    """Hill saturation, normalised to [0, 1). 0.5 exactly at x == half_sat."""
    xs = np.maximum(x, 0.0) ** slope
    return xs / (xs + half_sat**slope)


def make_spend(rng: np.random.Generator, ch: Channel, weeks: int) -> np.ndarray:
    """Lognormal spend with on/off flighting, so channels are not collinear by construction."""
    sigma = np.sqrt(np.log(1 + ch.spend_cv**2))
    mu = np.log(ch.spend_mean) - 0.5 * sigma**2
    spend = rng.lognormal(mu, sigma, weeks)
    active = rng.random(weeks) < ch.flight_prob
    return spend * active


def generate(
    weeks: int,
    seed: int,
    channels: list[Channel],
    intercept: float = 400_000.0,
    trend_per_week: float = 800.0,
    seasonality_amp: float = 0.12,
    price_beta: float = -150_000.0,
    noise_sd_pct: float = 0.05,
    start: str = "2023-01-02",
) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    t = np.arange(weeks)

    trend = intercept + trend_per_week * t
    seasonality = 1 + seasonality_amp * np.sin(2 * np.pi * t / 52.0)
    # Price index around 1.0; higher price depresses the KPI.
    price = 1.0 + rng.normal(0, 0.05, weeks)
    baseline = trend * seasonality + price_beta * (price - 1.0)

    frame = {"date": pd.date_range(start, periods=weeks, freq="W-MON")}
    contributions = {}
    for ch in channels:
        spend = make_spend(rng, ch, weeks)
        contribution = ch.beta * hill(
            geometric_adstock(spend, ch.adstock_decay), ch.hill_half_sat, ch.hill_slope
        )
        frame[f"spend_{ch.name}"] = spend
        contributions[ch.name] = contribution

    media_total = np.sum(list(contributions.values()), axis=0)
    noise = rng.normal(0, noise_sd_pct * float(np.mean(baseline)), weeks)
    kpi = baseline + media_total + noise

    frame["price_index"] = price
    frame["kpi"] = kpi
    df = pd.DataFrame(frame)

    truth = {
        "generated_with": {
            "weeks": weeks,
            "seed": seed,
            "intercept": intercept,
            "trend_per_week": trend_per_week,
            "seasonality_amp": seasonality_amp,
            "price_beta": price_beta,
            "noise_sd_pct": noise_sd_pct,
            "start": start,
        },
        "channels": {ch.name: asdict(ch) for ch in channels},
        # What a model is supposed to recover. ROI is in KPI units per EUR of spend.
        "true_contribution": {k: float(v.sum()) for k, v in contributions.items()},
        "true_roi": {
            ch.name: float(
                contributions[ch.name].sum() / max(df[f"spend_{ch.name}"].sum(), 1e-9)
            )
            for ch in channels
        },
        "true_baseline_share": float(baseline.sum() / kpi.sum()),
    }
    return df, truth


def to_canonical(df: pd.DataFrame, channels: list[Channel]) -> pd.DataFrame:
    records = []
    for channel in channels:
        records.append(
            pd.DataFrame(
                {
                    "date": pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d"),
                    "geo": "national",
                    "channel": channel.name,
                    "spend": df[f"spend_{channel.name}"],
                    "impressions": pd.NA,
                    "clicks": pd.NA,
                    "kpi": df["kpi"],
                    "control_price_index": df["price_index"],
                }
            )
        )
    return pd.concat(records, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", type=int, default=156, help="number of weekly rows")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/synthetic/base"),
        help="output prefix; writes <prefix>.csv and <prefix>.truth.json",
    )
    parser.add_argument(
        "--canonical",
        action="store_true",
        help="also write <prefix>.canonical.csv and its MMM-ready metadata sidecar",
    )
    args = parser.parse_args()

    df, truth = generate(args.weeks, args.seed, DEFAULT_CHANNELS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out.with_suffix(".csv"), index=False)
    Path(f"{args.out}.truth.json").write_text(json.dumps(truth, indent=2))

    if args.canonical:
        canonical_path = Path(f"{args.out}.canonical.csv")
        canonical = to_canonical(df, DEFAULT_CHANNELS)
        canonical.to_csv(canonical_path, index=False)
        canonical_meta = {
            "schema_version": "1.0",
            "currency": "EUR",
            "granularity": "weekly-mon",
            "timezone": "Europe/Madrid",
            "geos": ["national"],
            "channels": [channel.name for channel in DEFAULT_CHANNELS],
        }
        Path(f"{args.out}.canonical.meta.json").write_text(json.dumps(canonical_meta, indent=2))

    print(f"wrote {args.out}.csv ({len(df)} weeks) and {args.out}.truth.json")
    print("true ROI (KPI units per EUR):")
    for name, roi in truth["true_roi"].items():
        print(f"  {name:<10} {roi:6.2f}")
    print(f"baseline share of KPI: {truth['true_baseline_share']:.1%}")
    if args.canonical:
        print(f"wrote {args.out}.canonical.csv and {args.out}.canonical.meta.json")


if __name__ == "__main__":
    main()
