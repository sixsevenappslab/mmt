"""Generate a synthetic geo panel with a marketing experiment whose true lift is known.

`synthetic_mmm.py` makes one national series. Geo methods — Meridian GeoX, GeoLift,
CausalImpact, CausalPy — need a panel of regions instead, and to be worth anything as a test
they need an effect somebody injected on purpose, so you can ask whether the method finds it.

The point of this generator is that the true lift is *derived, not declared*. Every run
simulates two branches over the same random draws:

    counterfactual — nobody touched the media plan
    observed       — the treated regions got the experiment during the test window

Both share the same noise, so subtracting them over the treated regions and the test window
gives the incremental KPI the experiment really caused, to the euro. That number is what a
geo method is supposed to recover, and it is what lands in `<out>.truth.json`.

Three designs, named as Meridian GeoX names them:

    go-dark    spend of every channel cut in the treated regions
    holdback   spend of one channel cut in the treated regions
    heavy-up   spend raised in the treated regions

`--effect-size 0` leaves the media plan untouched in all three: an A/A placebo, which is how
you measure how often a method reports a lift that does not exist. That half of the lesson is
the one nobody teaches.

Two ROIs, on purpose. Average ROI is not a fixed property of a channel: it is contribution
divided by spend, and a channel that spends less sits lower on its saturation curve and returns
more per euro. So an experiment that cuts spend *raises* the measured ROI, and the number moves
with the design you asked for. `truth.json` therefore carries both — `true_roi` for the panel as
written, which is what a model fitted on this CSV should recover, and `true_roi_without_experiment`
for the same panel had nobody run the test, which no model can recover from this file. The fixed
parameters that do not move are in `channels`.

The CSV rounds spend to cents and the KPI to four decimals, which the national generator does
not. Readable files are worth more here than the last decimal of a series that already carries
5 % noise; the truth is computed before rounding, so read `truth.json`, not a sum of the CSV, when
you want the exact figure.

Known limitation, inherited on purpose: the KPI comes from the same adstock + Hill mechanism an
MMM assumes, so a model tested here is being graded on a world built to its own rules — honest
but easy, in the words of `libs/amss.md`. Generating from a different mechanism is AMSS's job,
not this file's.

Usage:
    python generators/synthetic_geo_mmm.py --weeks 104 --geos 20 --seed 42 \
        --design go-dark --treated 5 --test-start 80 --test-weeks 12 --out data/synthetic/geo
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generators.synthetic_mmm import (
    DEFAULT_CHANNELS,
    Channel,
    geometric_adstock,
    hill,
)

DESIGNS = ("none", "go-dark", "holdback", "heavy-up")
MIN_PRE_PERIODS = 4
EXIT_INPUT_ERROR = 2
CANONICAL_COLUMNS = (
    "date",
    "geo",
    "channel",
    "spend",
    "impressions",
    "clicks",
    "kpi",
    "control_price_index",
)


class GeneratorInputError(Exception):
    """A bad combination of flags, reported as one line and exit code 2."""


@dataclass
class Region:
    """One geography and the true parameters that make it differ from the others."""

    name: str
    population_share: float  # fraction of the national population, sums to 1
    baseline_index: float  # how rich this region's baseline is, per head, around 1.0
    spend_bias: float  # how much media it gets relative to its size, around 1.0


def build_regions(count: int, rng: np.random.Generator) -> list[Region]:
    """Regions of uneven size, as they are in reality — not a tidy equal split.

    A Dirichlet with a low concentration gives a few large regions and a long tail of small
    ones, which is what makes geo methods interesting: the small ones are noisy and the large
    ones dominate any naive average.
    """
    shares = rng.dirichlet(np.full(count, 2.5))
    baseline_index = rng.normal(1.0, 0.12, count)
    spend_bias = rng.normal(1.0, 0.15, count)
    width = len(str(count))
    return [
        Region(
            name=f"geo_{index + 1:0{width}d}",
            population_share=float(shares[index]),
            baseline_index=float(max(baseline_index[index], 0.5)),
            spend_bias=float(max(spend_bias[index], 0.4)),
        )
        for index in range(count)
    ]


def _regional_spend(
    rng: np.random.Generator, channel: Channel, region: Region, weeks: int
) -> np.ndarray:
    """Weekly spend for one region and channel: the national profile, scaled and re-drawn.

    Flighting is drawn per region so the channels are not collinear across the panel either —
    if every region went dark in the same week, no method could separate media from calendar.
    """
    national = channel.spend_mean * region.population_share * region.spend_bias
    sigma = np.sqrt(np.log(1 + channel.spend_cv**2))
    mu = np.log(max(national, 1e-6)) - 0.5 * sigma**2
    spend = rng.lognormal(mu, sigma, weeks)
    active = rng.random(weeks) < channel.flight_prob
    return spend * active


def _apply_design(
    spend: dict[tuple[str, str], np.ndarray],
    design: str,
    treated: list[str],
    window: slice,
    effect_size: float,
    holdback_channel: str | None,
) -> dict[tuple[str, str], np.ndarray]:
    """Return the observed media plan: the counterfactual with the experiment applied."""
    observed = {key: series.copy() for key, series in spend.items()}
    if design == "none":
        return observed
    for (geo, channel), series in observed.items():
        if geo not in treated:
            continue
        if design == "holdback" and channel != holdback_channel:
            continue
        factor = (1.0 + effect_size) if design == "heavy-up" else (1.0 - effect_size)
        series[window] = series[window] * factor
    return observed


def _kpi_from_spend(
    spend: dict[tuple[str, str], np.ndarray],
    regions: list[Region],
    channels: list[Channel],
    baseline: dict[str, np.ndarray],
    noise: dict[str, np.ndarray],
) -> tuple[dict[str, np.ndarray], dict[tuple[str, str], np.ndarray]]:
    """KPI per region, plus the media contribution per region and channel.

    The same `baseline` and `noise` go into both branches, so the only thing that can move the
    KPI between them is the media plan. That is what makes the subtraction a clean lift.
    """
    contributions: dict[tuple[str, str], np.ndarray] = {}
    kpi: dict[str, np.ndarray] = {}
    for region in regions:
        total = np.zeros_like(baseline[region.name])
        for channel in channels:
            adstocked = geometric_adstock(spend[(region.name, channel.name)], channel.adstock_decay)
            # Half-saturation scales with the region: a small region saturates on less money.
            half_sat = max(channel.hill_half_sat * region.population_share, 1e-6)
            contribution = (
                channel.beta
                * region.population_share
                * hill(adstocked, half_sat, channel.hill_slope)
            )
            contributions[(region.name, channel.name)] = contribution
            total = total + contribution
        kpi[region.name] = baseline[region.name] + total + noise[region.name]
    return kpi, contributions


def _validate(
    weeks: int,
    geos: int,
    design: str,
    treated: int,
    test_start: int,
    test_weeks: int,
    effect_size: float,
) -> None:
    if geos < 2:
        raise GeneratorInputError("Hacen falta al menos 2 regiones para un panel geo.")
    if weeks < MIN_PRE_PERIODS:
        raise GeneratorInputError(
            f"--weeks {weeks}: hacen falta al menos {MIN_PRE_PERIODS} periodos para que la "
            "serie tenga forma."
        )
    # Out-of-range --treated is a typo whether or not a design was asked for, so it is checked
    # before the early return: silently ignoring it is how a flag stops meaning anything.
    if treated < 0 or treated >= geos:
        raise GeneratorInputError(
            f"--treated {treated} con --geos {geos}: tienen que quedar regiones de control; "
            f"el maximo es {geos - 1}."
        )
    if design == "none":
        return
    if treated < 1:
        raise GeneratorInputError(
            f"--treated {treated}: hace falta al menos una region tratada para un experimento."
        )
    if test_start < MIN_PRE_PERIODS:
        raise GeneratorInputError(
            f"--test-start {test_start}: hacen falta al menos {MIN_PRE_PERIODS} periodos de "
            "pre-test para que un control sintetico tenga con que ajustarse."
        )
    if test_weeks < 1:
        raise GeneratorInputError(f"--test-weeks {test_weeks}: la ventana tiene que durar algo.")
    if test_start + test_weeks > weeks:
        raise GeneratorInputError(
            f"La ventana de test ({test_start} + {test_weeks}) se sale de las {weeks} semanas; "
            f"el maximo --test-start para esa duracion es {weeks - test_weeks}."
        )
    if effect_size < 0:
        raise GeneratorInputError(f"--effect-size {effect_size}: no puede ser negativo.")
    if design in ("go-dark", "holdback") and effect_size > 1:
        raise GeneratorInputError(
            f"--effect-size {effect_size} en {design}: es la fraccion de gasto que se retira, "
            "asi que va entre 0 y 1."
        )


def generate(
    weeks: int = 104,
    seed: int = 42,
    geos: int = 20,
    channels: list[Channel] | None = None,
    design: str = "none",
    treated: int = 0,
    test_start: int = 0,
    test_weeks: int = 0,
    effect_size: float = 1.0,
    holdback_channel: str | None = None,
    intercept_per_head: float = 400_000.0,
    trend_per_week: float = 800.0,
    seasonality_amp: float = 0.12,
    price_beta: float = -150_000.0,
    noise_sd_pct: float = 0.05,
    start: str = "2023-01-02",
) -> tuple[pd.DataFrame, dict]:
    """Build the panel and the truth that goes with it."""
    channels = channels or DEFAULT_CHANNELS
    _validate(weeks, geos, design, treated, test_start, test_weeks, effect_size)
    if design == "holdback":
        names = [channel.name for channel in channels]
        if holdback_channel not in names:
            raise GeneratorInputError(
                f"--holdback-channel {holdback_channel!r} no es un canal; opciones: {names}."
            )

    rng = np.random.default_rng(seed)
    regions = build_regions(geos, rng)
    weeks_index = np.arange(weeks)
    dates = pd.date_range(start, periods=weeks, freq="W-MON")

    # One national price index, so it stays invariant within a date and geo as the schema asks.
    price = 1.0 + rng.normal(0, 0.05, weeks)
    seasonality = 1 + seasonality_amp * np.sin(2 * np.pi * weeks_index / 52.0)

    baseline: dict[str, np.ndarray] = {}
    noise: dict[str, np.ndarray] = {}
    for region in regions:
        head = intercept_per_head * region.population_share * region.baseline_index
        trend = head + trend_per_week * region.population_share * weeks_index
        baseline[region.name] = trend * seasonality + price_beta * region.population_share * (
            price - 1.0
        )
        noise[region.name] = rng.normal(
            0, noise_sd_pct * float(np.mean(baseline[region.name])), weeks
        )

    counterfactual_spend = {
        (region.name, channel.name): _regional_spend(rng, channel, region, weeks)
        for region in regions
        for channel in channels
    }

    treated_names = (
        sorted(rng.choice([r.name for r in regions], size=treated, replace=False).tolist())
        if design != "none"
        else []
    )
    window = slice(test_start, test_start + test_weeks)
    observed_spend = _apply_design(
        counterfactual_spend, design, treated_names, window, effect_size, holdback_channel
    )

    kpi_cf, contributions_cf = _kpi_from_spend(
        counterfactual_spend, regions, channels, baseline, noise
    )
    kpi_obs, contributions = _kpi_from_spend(observed_spend, regions, channels, baseline, noise)

    frame = _to_canonical(dates, regions, channels, observed_spend, kpi_obs, price)
    truth = _build_truth(
        weeks=weeks,
        seed=seed,
        regions=regions,
        channels=channels,
        design=design,
        treated_names=treated_names,
        test_start=test_start,
        test_weeks=test_weeks,
        effect_size=effect_size,
        holdback_channel=holdback_channel,
        observed_spend=observed_spend,
        counterfactual_spend=counterfactual_spend,
        contributions=contributions,
        contributions_cf=contributions_cf,
        baseline=baseline,
        kpi_obs=kpi_obs,
        kpi_cf=kpi_cf,
        window=window,
        start=start,
        dates=dates,
        noise_sd_pct=noise_sd_pct,
    )
    return frame, truth


def _to_canonical(
    dates: pd.DatetimeIndex,
    regions: list[Region],
    channels: list[Channel],
    spend: dict[tuple[str, str], np.ndarray],
    kpi: dict[str, np.ndarray],
    price: np.ndarray,
) -> pd.DataFrame:
    """The long MMM-ready table of FEAT-001: one row per date, geo and channel."""
    blocks = []
    for region in regions:
        for channel in channels:
            blocks.append(
                pd.DataFrame(
                    {
                        "date": dates.strftime("%Y-%m-%d"),
                        "geo": region.name,
                        "channel": channel.name,
                        "spend": np.round(spend[(region.name, channel.name)], 2),
                        "impressions": pd.NA,
                        "clicks": pd.NA,
                        "kpi": np.round(kpi[region.name], 4),
                        "control_price_index": np.round(price, 6),
                    }
                )
            )
    frame = pd.concat(blocks, ignore_index=True)
    frame = frame.sort_values(["date", "geo", "channel"]).reset_index(drop=True)
    return frame.loc[:, list(CANONICAL_COLUMNS)]


def _build_truth(**kw) -> dict:
    """Everything a model is supposed to recover, and nothing it could not have known."""
    regions: list[Region] = kw["regions"]
    channels: list[Channel] = kw["channels"]
    contributions = kw["contributions"]
    observed_spend = kw["observed_spend"]

    total_baseline = float(sum(series.sum() for series in kw["baseline"].values()))

    def totals(contrib, spend) -> tuple[dict, dict]:
        contribution = {
            channel.name: float(
                sum(contrib[(region.name, channel.name)].sum() for region in regions)
            )
            for channel in channels
        }
        roi = {
            channel.name: contribution[channel.name]
            / max(
                float(sum(spend[(region.name, channel.name)].sum() for region in regions)), 1e-9
            )
            for channel in channels
        }
        return contribution, roi

    contribution_obs, roi_obs = totals(contributions, observed_spend)
    contribution_cf, roi_cf = totals(kw["contributions_cf"], kw["counterfactual_spend"])
    total_kpi_obs = float(sum(series.sum() for series in kw["kpi_obs"].values()))
    total_kpi_cf = float(sum(series.sum() for series in kw["kpi_cf"].values()))

    truth = {
        "generated_with": {
            "weeks": kw["weeks"],
            "seed": kw["seed"],
            "geos": len(regions),
            "start": kw["start"],
            "noise_sd_pct": kw["noise_sd_pct"],
        },
        "regions": {region.name: asdict(region) for region in regions},
        # Meridian needs a population per geo to fit a multi-geo model, and FEAT-001's schema
        # says that dimension is never invented. Here it is, because here it is known.
        "population_by_geo": {region.name: region.population_share for region in regions},
        "channels": {channel.name: asdict(channel) for channel in channels},
        # Two worlds, two ROIs, and the difference is not a rounding error — see the note.
        "roi_basis": (
            "true_contribution and true_roi describe the panel as written, experiment included. "
            "Average ROI is not a fixed channel property: a channel that spends less sits lower "
            "on its saturation curve and returns more per euro, so an experiment that cuts spend "
            "raises it. Fit a model on this CSV and true_roi is what it should recover. The "
            "*_without_experiment pair is the same panel had nobody run the test, and no model "
            "can recover it from this file. The fixed channel parameters live in 'channels'."
        ),
        "true_contribution": contribution_obs,
        "true_roi": roi_obs,
        "true_baseline_share": total_baseline / total_kpi_obs,
        "true_contribution_without_experiment": contribution_cf,
        "true_roi_without_experiment": roi_cf,
        "true_baseline_share_without_experiment": total_baseline / total_kpi_cf,
    }

    if kw["design"] == "none":
        return truth

    window = kw["window"]
    treated_names = kw["treated_names"]
    incremental = float(
        sum(kw["kpi_obs"][name][window].sum() - kw["kpi_cf"][name][window].sum() for name in treated_names)
    )
    counterfactual_total = float(sum(kw["kpi_cf"][name][window].sum() for name in treated_names))
    spend_delta = float(
        sum(
            observed_spend[(name, channel.name)][window].sum()
            for name in treated_names
            for channel in channels
        )
    )
    dates = kw["dates"]
    truth["experiment"] = {
        "design": kw["design"],
        "effect_size": kw["effect_size"],
        "holdback_channel": kw["holdback_channel"],
        "treatment_geos": treated_names,
        "control_geos": sorted(r.name for r in regions if r.name not in treated_names),
        "test_window": {
            "start_index": kw["test_start"],
            "weeks": kw["test_weeks"],
            "start_date": dates[window.start].strftime("%Y-%m-%d"),
            "end_date": dates[window.stop - 1].strftime("%Y-%m-%d"),
        },
        "treated_spend_in_window": spend_delta,
    }
    # Flat, not nested, because this is the number every geo method is scored against.
    truth["true_incremental_kpi"] = incremental
    truth["true_lift_pct"] = (
        100.0 * incremental / counterfactual_total if counterfactual_total else 0.0
    )
    # Adstock keeps paying after the window closes. GeoLift and GeoX score the in-window figure,
    # so that one stays the headline; but somebody measuring total incrementality would be off
    # by this much and would blame the method, so the whole-series number is here too.
    total_incremental = float(
        sum(kw["kpi_obs"][name].sum() - kw["kpi_cf"][name].sum() for name in treated_names)
    )
    truth["true_incremental_kpi_including_carryover"] = total_incremental
    truth["carryover_share_of_effect"] = (
        (total_incremental - incremental) / incremental if incremental else 0.0
    )
    truth["incremental_basis"] = (
        "true_incremental_kpi covers the test window only, which is what GeoLift and Meridian "
        "GeoX estimate and what a geo method should be scored against. "
        "true_incremental_kpi_including_carryover covers the whole series, because adstock keeps "
        "paying after the window closes; carryover_share_of_effect is the gap between them, as a "
        "fraction of the in-window effect."
    )
    return truth


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", type=int, default=104, help="number of weekly periods")
    parser.add_argument("--geos", type=int, default=20, help="number of regions in the panel")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--design", choices=DESIGNS, default="none")
    parser.add_argument("--treated", type=int, default=0, help="how many regions get the test")
    parser.add_argument("--test-start", type=int, default=0, help="week index the test starts on")
    parser.add_argument("--test-weeks", type=int, default=0, help="how long the test window lasts")
    parser.add_argument(
        "--effect-size",
        type=float,
        default=1.0,
        help="fraction of spend removed (go-dark, holdback) or added (heavy-up); 0 is an A/A placebo",
    )
    parser.add_argument("--holdback-channel", default=None, help="channel to cut in a holdback")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/synthetic/geo"),
        help="output prefix; writes <prefix>.csv and <prefix>.truth.json",
    )
    args = parser.parse_args()

    try:
        frame, truth = generate(
            weeks=args.weeks,
            seed=args.seed,
            geos=args.geos,
            design=args.design,
            treated=args.treated,
            test_start=args.test_start,
            test_weeks=args.test_weeks,
            effect_size=args.effect_size,
            holdback_channel=args.holdback_channel,
        )
    except GeneratorInputError as error:
        print(f"ERROR: {' '.join(str(error).split())}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out.with_suffix(".csv"), index=False)
    Path(f"{args.out}.truth.json").write_text(json.dumps(truth, indent=2))
    Path(f"{args.out}.meta.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "currency": "EUR",
                "granularity": "weekly-mon",
                "timezone": "Europe/Madrid",
                "geos": sorted(truth["population_by_geo"]),
                "channels": sorted(truth["channels"]),
            },
            indent=2,
        )
    )

    print(
        f"wrote {args.out}.csv ({len(frame)} rows, {args.geos} geos, {args.weeks} weeks), "
        f"{args.out}.truth.json and {args.out}.meta.json"
    )
    print("true ROI (KPI units per EUR):")
    for name, roi in truth["true_roi"].items():
        print(f"  {name:<10} {roi:6.2f}")
    print(f"baseline share of KPI: {truth['true_baseline_share']:.1%}")
    if args.design != "none":
        experiment = truth["experiment"]
        print(
            f"experiment: {experiment['design']} on {len(experiment['treatment_geos'])} geos, "
            f"{experiment['test_window']['start_date']} to {experiment['test_window']['end_date']}"
        )
        print(
            f"TRUE incremental KPI: {truth['true_incremental_kpi']:,.0f} "
            f"({truth['true_lift_pct']:+.2f}%) — this is what a geo method has to recover"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
