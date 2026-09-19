"""Experiment 01: PyMC-Marketing MMM vs. known ground truth.

Fits a standard MMM (geometric adstock + Hill saturation + yearly seasonality + controls)
on the synthetic dataset from generators/synthetic_mmm.py and compares the recovered
per-channel ROI, contribution and adstock decay against the *.truth.json.

Usage (from the repo root, inside the pymc venv):
    .venvs/pymc/bin/python experiments/01-pymc-vs-verdad/run.py --draws 1000 --tune 1000
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd

from pymc_extras.prior import Prior
from pymc_marketing.mmm import MMM, GeometricAdstock, HillSaturation, LogisticSaturation

HERE = Path(__file__).parent
ROOT = HERE.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=ROOT / "data/synthetic/base", type=Path)
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--tune", type=int, default=1000)
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-accept", type=float, default=0.95)
    parser.add_argument(
        "--saturation",
        choices=["hill-default", "logistic-default", "hill-informed"],
        default="hill-default",
        help="hill-default: same functional form as the generator, library default priors. "
        "logistic-default: the saturation used in the official examples. "
        "hill-informed: Hill with priors that keep kappa and slope away from degenerate values.",
    )
    parser.add_argument("--out", default=None, type=Path)
    args = parser.parse_args()
    if args.out is None:
        args.out = HERE / "results" / args.saturation

    df = pd.read_csv(args.data.with_suffix(".csv"), parse_dates=["date"])
    truth = json.loads(Path(f"{args.data}.truth.json").read_text())
    channels = [c for c in df.columns if c.startswith("spend_")]
    names = [c.removeprefix("spend_") for c in channels]

    # An analyst would see the upward drift in the KPI and add a trend regressor.
    # The model has no trend component by default, so we give it one as a control.
    df["trend"] = np.arange(len(df)) / len(df)
    X = df[["date", *channels, "price_index", "trend"]]
    y = df["kpi"]

    if args.saturation == "hill-default":
        saturation = HillSaturation()
    elif args.saturation == "logistic-default":
        saturation = LogisticSaturation()
    else:
        # Channel spend is scaled to [0, 1] inside the model, so kappa (half-saturation) in
        # (0, 1) with mass in the middle, and a slope around 1-2 like real response curves.
        saturation = HillSaturation(
            priors={
                "kappa": Prior("Beta", alpha=2, beta=2, dims="channel"),
                "slope": Prior("Gamma", mu=1.5, sigma=0.5, dims="channel"),
                "beta": Prior("HalfNormal", sigma=1.5, dims="channel"),
            }
        )

    mmm = MMM(
        date_column="date",
        channel_columns=channels,
        target_column="kpi",
        # Half-life parametrisation: the default alpha ~ Beta(1, 3) let a chain underflow to
        # alpha == 0 and crash the sampler ("0 < alpha <= 1") on the first full run.
        adstock=GeometricAdstock(l_max=12, parametrization="halflife"),
        saturation=saturation,
        control_columns=["price_index", "trend"],
        yearly_seasonality=2,
    )

    t0 = time.time()
    mmm.fit(
        X,
        y,
        chains=args.chains,
        draws=args.draws,
        tune=args.tune,
        cores=min(args.chains, 4),
        random_seed=args.seed,
        target_accept=args.target_accept,
        # nutpie treats a logp evaluation error as a divergence instead of aborting the
        # chain; PyMC's default sampler crashed twice with NaN alpha during early tuning.
        nuts_sampler="nutpie",
    )
    fit_seconds = time.time() - t0
    print(f"sampling took {fit_seconds:.0f}s")

    idata = mmm.idata
    post = idata.posterior
    sat_vars = [v for v in post.data_vars if str(v).startswith("saturation_")]
    diag = az.summary(post, var_names=["adstock_halflife", *sat_vars, "gamma_control"])
    print(diag)
    divergences = int(idata.sample_stats["diverging"].sum())

    # Per-channel contribution on the original scale, full posterior: (chain, draw, date, channel)
    # One variable per channel column; stack them into a (channel, chain, draw, date) array.
    cf = mmm.compute_counterfactual_contributions_dataset()
    contrib = cf[channels].to_array("channel")
    total = contrib.sum("date")  # (chain, draw, channel)
    spend = df[channels].sum().to_numpy()

    rows = []
    for i, (col, name) in enumerate(zip(channels, names)):
        c = total.sel(channel=col).values.ravel()
        roi = c / spend[i]
        q = np.quantile(roi, [0.03, 0.5, 0.97])
        # decay alpha = 0.5 ** (1 / halflife); compare on the alpha scale the generator uses
        alpha = 0.5 ** (1 / post["adstock_halflife"].sel(channel=col).values.ravel())
        rows.append(
            {
                "channel": name,
                "spend_eur": float(spend[i]),
                "true_roi": truth["true_roi"][name],
                "roi_median": float(q[1]),
                "roi_hdi94_low": float(q[0]),
                "roi_hdi94_high": float(q[2]),
                "true_contribution": truth["true_contribution"][name],
                "contribution_median": float(np.median(c)),
                "true_adstock_decay": truth["channels"][name]["adstock_decay"],
                "adstock_alpha_median": float(np.median(alpha)),
                "adstock_alpha_hdi94": [float(v) for v in np.quantile(alpha, [0.03, 0.97])],
            }
        )
    table = pd.DataFrame(rows)
    table["roi_error_pct"] = 100 * (table["roi_median"] / table["true_roi"] - 1)
    table["truth_inside_hdi"] = (table["true_roi"] >= table["roi_hdi94_low"]) & (
        table["true_roi"] <= table["roi_hdi94_high"]
    )

    # Baseline share: everything that is not media. Also print the full decomposition so
    # the reader can see where the model puts the non-media KPI (intercept, trend, ...).
    media_total = contrib.sum(("date", "channel")).values.ravel()
    baseline_share = 1 - media_total / y.sum()
    decomposition = {}
    for var in cf.data_vars:
        v = cf[var]
        tot = v.sum("date") if "date" in v.dims else v * len(df)
        decomposition[var] = float(np.median(tot.values))
    print("median total contribution per component (KPI units):")
    for k, v in decomposition.items():
        print(f"  {k:<20} {v:>14,.0f}  ({v / y.sum():6.1%} of KPI)")

    pd.set_option("display.width", 200)
    print(table[["channel", "true_roi", "roi_median", "roi_hdi94_low", "roi_hdi94_high",
                 "roi_error_pct", "truth_inside_hdi", "true_adstock_decay",
                 "adstock_alpha_median"]].round(3).to_string(index=False))
    bs_q = np.quantile(baseline_share, [0.03, 0.5, 0.97])
    print(f"baseline share: true {truth['true_baseline_share']:.3f} | "
          f"model median {bs_q[1]:.3f}  94% interval [{bs_q[0]:.3f}, {bs_q[2]:.3f}]")
    print(f"sum of per-channel median contributions: "
          f"{table['contribution_median'].sum() / y.sum():.1%} of KPI "
          f"(true media share {1 - truth['true_baseline_share']:.1%})")

    args.out.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out / "roi_vs_truth.csv", index=False)
    diag.to_csv(args.out / "diagnostics.csv")
    summary = {
        "variant": args.saturation,
        "pymc_marketing": __import__("pymc_marketing").__version__,
        "pymc": __import__("pymc").__version__,
        "sampler": {"chains": args.chains, "draws": args.draws, "tune": args.tune,
                    "target_accept": args.target_accept, "nuts_sampler": "nutpie",
                    "seconds": round(fit_seconds)},
        "divergences": divergences,
        "max_rhat": float(diag["r_hat"].max()),
        "min_ess_bulk": float(diag["ess_bulk"].min()),
        "baseline_share": {"true": truth["true_baseline_share"], "median": float(bs_q[1]),
                           "hdi94": [float(bs_q[0]), float(bs_q[2])]},
        "decomposition": decomposition,
        "channels": table.to_dict(orient="records"),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    mmm.save(str(args.out / "model.nc"))
    print(f"results in {args.out}")


if __name__ == "__main__":
    main()
