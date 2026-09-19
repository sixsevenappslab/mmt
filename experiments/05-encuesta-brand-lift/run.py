"""Experiment 05: brand lift survey estimators vs. known ground truth.

Runs four estimators of the campaign lift on the synthetic brand lift surveys from
generators/synthetic_brand_lift.py (randomised and observational exposure) and scores each
against the true lift in *.truth.json:

  naive       difference in "yes" share, exposed minus control, among respondents
  adjusted    logistic regression on covariates, lift = average effect among the exposed
  reweighted  respondents reweighted to the population reference with `balance` (IPW),
              then the naive difference with weights
  both        reweighted + adjusted

Also reports what a typical-sized study (n=2000 respondents) would conclude.

Usage (inside the surveys venv):
    .venvs/surveys/bin/python experiments/05-encuesta-brand-lift/run.py
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

logging.getLogger("balance").setLevel(logging.ERROR)
from balance import Sample  # noqa: E402

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
COVARS = ["age_group", "heavy_digital", "existing_customer"]


def naive_lift(df: pd.DataFrame, w: np.ndarray | None = None) -> tuple[float, float]:
    """Weighted difference in proportions, with a 95% CI half-width (percentage points)."""
    w = np.ones(len(df)) if w is None else np.asarray(w)
    out = []
    for g in (1, 0):
        m = df["exposed"].values == g
        p = np.average(df["answer_yes"].values[m], weights=w[m])
        # Kish effective sample size so the CI reflects the weights.
        n_eff = w[m].sum() ** 2 / (w[m] ** 2).sum()
        out.append((p, p * (1 - p) / n_eff))
    diff = out[0][0] - out[1][0]
    half = 1.96 * np.sqrt(out[0][1] + out[1][1])
    return 100 * diff, 100 * half


def adjusted_lift(df: pd.DataFrame, w: np.ndarray | None = None) -> float:
    """Logit with covariates; lift = mean over the exposed of p(exposed=1) - p(exposed=0)."""
    X = pd.get_dummies(df[COVARS + ["exposed"]], columns=["age_group"], drop_first=True, dtype=float)
    X = sm.add_constant(X)
    freq = np.ones(len(df)) if w is None else np.asarray(w)
    model = sm.GLM(df["answer_yes"], X, family=sm.families.Binomial(), freq_weights=freq).fit()
    exposed = X[df["exposed"] == 1]
    x1 = exposed.copy(); x1["exposed"] = 1.0
    x0 = exposed.copy(); x0["exposed"] = 0.0
    fw = freq[df["exposed"].values == 1]
    return 100 * float(np.average(model.predict(x1) - model.predict(x0), weights=fw))


def reweight(df: pd.DataFrame, reference: pd.DataFrame) -> np.ndarray:
    """IPW weights that make the respondents look like the population reference on COVARS."""
    sample = Sample.from_frame(df[["respondent_id", *COVARS]], id_column="respondent_id")
    target = Sample.from_frame(reference[["person_id", *COVARS]], id_column="person_id")
    adjusted = sample.set_target(target).adjust(method="ipw")
    # balance stores ids as strings
    weights = adjusted.df.assign(respondent_id=lambda d: d["respondent_id"].astype(int))
    w = weights.set_index("respondent_id").loc[df["respondent_id"], "weight"].to_numpy()
    return w / w.mean()


def run_dataset(prefix: Path, seed: int) -> dict:
    df = pd.read_csv(prefix.with_suffix(".csv"))
    reference = pd.read_csv(f"{prefix}.population.csv")
    truth = json.loads(Path(f"{prefix}.truth.json").read_text())
    w = reweight(df, reference)

    res = {"truth_att_pp": truth["true_lift_att_pp"], "truth_ate_pp": truth["true_lift_ate_pp"],
           "n_respondents": len(df), "estimates": {}}
    n_lift, n_ci = naive_lift(df)
    r_lift, r_ci = naive_lift(df, w)
    res["estimates"]["naive"] = {"lift_pp": n_lift, "ci95_half_pp": n_ci}
    res["estimates"]["adjusted"] = {"lift_pp": adjusted_lift(df)}
    res["estimates"]["reweighted"] = {"lift_pp": r_lift, "ci95_half_pp": r_ci}
    res["estimates"]["both"] = {"lift_pp": adjusted_lift(df, w)}

    # Heterogeneity: naive lift within each segment vs. the true segment lift.
    res["by_segment"] = {}
    for seg, sub in df.groupby("heavy_digital"):
        lift, ci = naive_lift(sub)
        res["by_segment"][f"heavy_digital={seg}"] = {
            "naive_lift_pp": lift, "ci95_half_pp": ci,
            "true_lift_pp": truth["true_lift_by_segment_pp"][f"heavy_digital={seg}"],
        }

    # What a typical study size sees: 2000 respondents, 200 random subsamples.
    rng = np.random.default_rng(seed)
    small = [naive_lift(df.sample(2000, random_state=int(rng.integers(1e9)))) for _ in range(200)]
    lifts = np.array([s[0] for s in small]); halves = np.array([s[1] for s in small])
    res["n2000"] = {
        "lift_pp_mean": float(lifts.mean()), "lift_pp_sd": float(lifts.std()),
        "ci95_half_pp_mean": float(halves.mean()),
        "share_ci_excludes_zero": float(np.mean(lifts - halves > 0)),
        "share_ci_covers_truth": float(np.mean(np.abs(lifts - truth["true_lift_att_pp"]) <= halves)),
    }
    res["bias_diagnostics"] = truth["bias_diagnostics"]
    return res


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=HERE / "results")
    args = parser.parse_args()

    results = {}
    for name in ("brandlift_rct", "brandlift_obs"):
        results[name] = run_dataset(ROOT / "data/synthetic" / name, args.seed)
        r = results[name]
        print(f"\n== {name}  (n={r['n_respondents']}, true ATT {r['truth_att_pp']:.2f} pp, "
              f"ATE {r['truth_ate_pp']:.2f} pp)")
        for est, v in r["estimates"].items():
            ci = f" ± {v['ci95_half_pp']:.2f}" if "ci95_half_pp" in v else ""
            print(f"  {est:<11} {v['lift_pp']:6.2f}{ci}   error {v['lift_pp'] - r['truth_att_pp']:+.2f} pp")
        for seg, v in r["by_segment"].items():
            print(f"  segment {seg}: naive {v['naive_lift_pp']:.2f} ± {v['ci95_half_pp']:.2f} "
                  f"(true {v['true_lift_pp']:.2f})")
        s = r["n2000"]
        print(f"  n=2000: lift {s['lift_pp_mean']:.2f} ± {s['ci95_half_pp_mean']:.2f}, "
              f"CI excludes 0 in {s['share_ci_excludes_zero']:.0%} of studies, "
              f"covers truth in {s['share_ci_covers_truth']:.0%}")

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(results, indent=2))
    print(f"\nresults in {args.out}")


if __name__ == "__main__":
    main()
