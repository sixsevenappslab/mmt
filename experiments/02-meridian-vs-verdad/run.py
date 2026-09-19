"""Experiment 02: Google Meridian MMM vs. known ground truth.

Fits Meridian (geometric adstock + Hill saturation, ROI priors) on the same synthetic
dataset as experiment 01 and produces the same table: per-channel ROI, contribution and
adstock decay against *.truth.json, plus sampling diagnostics and CPU time.

Usage (from the repo root, inside the meridian venv):
    .venvs/meridian/bin/python experiments/02-meridian-vs-verdad/run.py --variant roi-default
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from meridian import backend
from meridian.analysis import analyzer
from meridian.data import data_frame_input_data_builder as builder
from meridian.model import model, prior_distribution, spec

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
# Custom priors must come from Meridian's backend (float64, JAX in 2.0.0); a plain
# tfp.distributions object fails with a dtype mismatch at model build time.
tfd = backend.tfd
f = backend.np_float_dtype


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=ROOT / "data/synthetic/base", type=Path)
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--adapt", type=int, default=500)
    parser.add_argument("--burnin", type=int, default=500)
    parser.add_argument("--keep", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--knots", type=int, default=13)
    parser.add_argument(
        "--variant",
        choices=["roi-default", "roi-wide", "contribution", "roi-custom"],
        default="roi-default",
        help="roi-default: library default ROI prior, LogNormal(0.2, 0.9). "
        "roi-wide: ROI prior centred where the generator lives, LogNormal(log 4, 0.7). "
        "contribution: prior on each channel's share of the KPI instead of on ROI. "
        "roi-custom: your own LogNormal ROI prior, from --roi-median and --roi-sigma "
        "(lesson 04 asks you to defend one without looking at the truth).",
    )
    parser.add_argument("--roi-median", type=float, default=None,
                        help="roi-custom only: median ROI of the LogNormal prior, KPI units per euro")
    parser.add_argument("--roi-sigma", type=float, default=0.7,
                        help="roi-custom only: sigma of the LogNormal prior on the log scale")
    parser.add_argument("--out", default=None, type=Path)
    args = parser.parse_args()
    if args.variant == "roi-custom" and (args.roi_median is None or args.roi_median <= 0):
        parser.error("roi-custom needs --roi-median > 0")
    if args.roi_sigma <= 0:
        parser.error("--roi-sigma must be > 0")
    if args.out is None:
        args.out = HERE / "results" / args.variant

    df = pd.read_csv(args.data.with_suffix(".csv"), parse_dates=["date"])
    truth = json.loads(Path(f"{args.data}.truth.json").read_text())
    spend_cols = [c for c in df.columns if c.startswith("spend_")]
    names = [c.removeprefix("spend_") for c in spend_cols]
    df["time"] = df["date"].dt.strftime("%Y-%m-%d")

    # National model (one geo). No impressions in the generator, so spend doubles as the
    # media execution variable, which is what Meridian's docs recommend when there is
    # nothing better. KPI is treated as revenue so ROI comes out in KPI units per euro,
    # the same scale as experiment 01 and as base.truth.json.
    data = (
        builder.DataFrameInputDataBuilder(kpi_type="revenue", default_time_column="time")
        .with_kpi(df, kpi_col="kpi")
        .with_media(df, media_cols=spend_cols, media_spend_cols=spend_cols, media_channels=names)
        .with_controls(df, control_cols=["price_index"])
        .build()
    )

    if args.variant == "roi-default":
        prior = prior_distribution.PriorDistribution()
        prior_type = "roi"
    elif args.variant == "roi-wide":
        prior = prior_distribution.PriorDistribution(
            roi_m=tfd.LogNormal(f(np.log(4.0)), f(0.7), name="roi_m"),
        )
        prior_type = "roi"
    elif args.variant == "roi-custom":
        prior = prior_distribution.PriorDistribution(
            roi_m=tfd.LogNormal(f(np.log(args.roi_median)), f(args.roi_sigma), name="roi_m"),
        )
        prior_type = "roi"
    else:
        # Sum of channel contributions in the generator is ~25 % of the KPI. A prior with
        # mean 0.06 per channel and sd 0.05 says "each channel is a few percent, maybe up
        # to 15 %", without using the exact truth.
        prior = prior_distribution.PriorDistribution(
            contribution_m=tfd.TruncatedNormal(f(0.06), f(0.05), f(0.0), f(1.0), name="contribution_m"),
        )
        prior_type = "contribution"

    model_spec = spec.ModelSpec(
        prior=prior,
        paid_media_prior_type=prior_type,
        max_lag=12,
        # Meridian has no explicit trend or seasonality term: the baseline is a spline over
        # time. One knot every 12 weeks lets it follow the 30 % drift and the annual cycle.
        knots=args.knots,
    )
    mmm = model.Meridian(input_data=data, model_spec=model_spec)

    mmm.sample_prior(500, seed=args.seed)
    t0 = time.time()
    mmm.sample_posterior(
        n_chains=args.chains,
        n_adapt=args.adapt,
        n_burnin=args.burnin,
        n_keep=args.keep,
        seed=args.seed,
    )
    fit_seconds = time.time() - t0
    print(f"sampling took {fit_seconds:.0f}s")

    an = analyzer.Analyzer(mmm)
    rhat = an.rhat_summary()
    print(rhat)
    post = mmm.inference_data.posterior
    divergences = 0
    if "diverging" in mmm.inference_data.sample_stats:
        divergences = int(mmm.inference_data.sample_stats["diverging"].sum())

    # (chain, draw, channel), KPI units.
    roi = np.asarray(an.roi())
    inc = np.asarray(an.incremental_outcome())
    y_total = float(df["kpi"].sum())
    spend = df[spend_cols].sum().to_numpy()
    decay = an.adstock_decay()

    rows = []
    for i, name in enumerate(names):
        r = roi[..., i].ravel()
        c = inc[..., i].ravel()
        q = np.quantile(r, [0.03, 0.5, 0.97])
        alpha = np.asarray(post["alpha_m"].sel(media_channel=name)).ravel()
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

    media_total = inc.sum(axis=-1).ravel()
    baseline_share = 1 - media_total / y_total
    bs_q = np.quantile(baseline_share, [0.03, 0.5, 0.97])

    pd.set_option("display.width", 200)
    print(table[["channel", "true_roi", "roi_median", "roi_hdi94_low", "roi_hdi94_high",
                 "roi_error_pct", "truth_inside_hdi", "true_adstock_decay",
                 "adstock_alpha_median"]].round(3).to_string(index=False))
    print(f"baseline share: true {truth['true_baseline_share']:.3f} | "
          f"model median {bs_q[1]:.3f}  94% interval [{bs_q[0]:.3f}, {bs_q[2]:.3f}]")
    print(f"sum of per-channel median contributions: "
          f"{table['contribution_median'].sum() / y_total:.1%} of KPI "
          f"(true media share {1 - truth['true_baseline_share']:.1%})")

    args.out.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out / "roi_vs_truth.csv", index=False)
    rhat.to_csv(args.out / "diagnostics.csv")
    decay.to_csv(args.out / "adstock_decay.csv", index=False)
    summary = {
        "variant": args.variant,
        "meridian": __import__("meridian").__version__,
        "roi_prior": (
            {"median": args.roi_median, "sigma": args.roi_sigma}
            if args.variant == "roi-custom" else None
        ),
        "sampler": {"chains": args.chains, "adapt": args.adapt, "burnin": args.burnin,
                    "keep": args.keep, "knots": args.knots, "seconds": round(fit_seconds)},
        "divergences": divergences,
        "max_rhat": float(rhat["max_r_hat"].max()),
        "baseline_share": {"true": truth["true_baseline_share"], "median": float(bs_q[1]),
                           "hdi94": [float(bs_q[0]), float(bs_q[2])]},
        "channels": table.to_dict(orient="records"),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"results in {args.out}")


if __name__ == "__main__":
    main()
