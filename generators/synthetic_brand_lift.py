"""Generate a synthetic brand lift survey with known ground truth.

A brand lift study asks a survey question (e.g. "which of these brands would you consider?")
to people exposed to a campaign and to a control group, and reads the lift as the difference.
Real studies are hard to evaluate because nobody knows the true lift. Here we simulate the
whole chain, so every bias has a known size:

1. A population of individuals with covariates (age group, heavy digital user, existing
   customer). These drive everything below, which is what makes the biases appear.
2. Exposure. Either randomised (a true holdout, like platform brand-lift studies with ghost
   ads) or observational (exposure follows the covariates: heavy digital users see more ads).
3. The true outcome. Baseline propensity to answer "yes" depends on covariates; exposure adds
   a *known* lift that can differ by segment (heterogeneous effect).
4. Survey response. Not everyone answers, and who answers depends on the covariates
   (non-response bias). Only respondents end up in the CSV.

Output: <prefix>.csv with respondents only (what an analyst actually gets),
<prefix>.population.csv with the covariates of a random reference sample of the population
(what a census or a panel would give, for reweighting; no exposure, no outcome), and
<prefix>.truth.json with the true lift in the population (ATE), among the exposed (ATT),
per segment, and the size of every bias mechanism.

Usage:
    python generators/synthetic_brand_lift.py --n 200000 --seed 7 --out data/synthetic/brandlift_rct
    python generators/synthetic_brand_lift.py --n 200000 --seed 7 --observational --out data/synthetic/brandlift_obs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate(
    n: int,
    seed: int,
    observational: bool,
    exposure_rate: float = 0.5,
    response_rate: float = 0.08,
    lift_pp: float = 0.06,
    lift_pp_heavy_digital: float = 0.03,
) -> tuple[pd.DataFrame, dict]:
    """Simulate the population, exposure, outcome and survey response.

    lift_pp is the true lift for the reference segment, in percentage points of the outcome.
    Heavy digital users get lift_pp + lift_pp_heavy_digital: the campaign works better on
    them, which matters because they are also more exposed and respond more.
    """
    rng = np.random.default_rng(seed)

    # --- 1. population -----------------------------------------------------------------
    age_group = rng.choice(["18-24", "25-34", "35-54", "55+"], size=n, p=[0.15, 0.25, 0.35, 0.25])
    heavy_digital = (rng.random(n) < np.select(
        [age_group == "18-24", age_group == "25-34", age_group == "35-54"], [0.7, 0.55, 0.35], 0.15
    )).astype(int)
    existing_customer = (rng.random(n) < 0.12).astype(int)

    # --- 2. exposure -------------------------------------------------------------------
    if observational:
        # Exposure follows digital behaviour and youth: the classic confounder.
        logit = -0.6 + 1.6 * heavy_digital + 0.4 * (age_group == "18-24") - 0.3 * (age_group == "55+")
        p_exposed = sigmoid(logit)
    else:
        p_exposed = np.full(n, exposure_rate)
    exposed = (rng.random(n) < p_exposed).astype(int)

    # --- 3. true outcome (brand consideration, yes/no) ----------------------------------
    base_logit = (
        -1.4
        + 0.5 * heavy_digital
        + 1.8 * existing_customer
        + 0.2 * (age_group == "18-24")
        - 0.3 * (age_group == "55+")
    )
    p0 = sigmoid(base_logit)  # potential outcome without exposure
    individual_lift = lift_pp + lift_pp_heavy_digital * heavy_digital
    p1 = np.clip(p0 + individual_lift, 0, 1)  # potential outcome with exposure, additive lift
    y0 = (rng.random(n) < p0).astype(int)
    # Same uniform draw for y1 so that lift shows up as extra 1s, not as noise.
    y1 = np.maximum(y0, (rng.random(n) < (individual_lift / np.maximum(1 - p0, 1e-9))).astype(int))
    y = np.where(exposed == 1, y1, y0)

    # --- 4. survey response ------------------------------------------------------------
    # Who answers: older people and existing customers answer more, heavy digital users
    # less. Exposure itself nudges response up a little (people who saw the ad engage more),
    # which is a real and nasty mechanism.
    resp_logit = (
        np.log(response_rate / (1 - response_rate))
        + 0.5 * (age_group == "55+")
        + 0.7 * existing_customer
        - 0.4 * heavy_digital
        + 0.15 * exposed
    )
    responded = (rng.random(n) < sigmoid(resp_logit)).astype(int)

    pop = pd.DataFrame(
        {
            "age_group": age_group,
            "heavy_digital": heavy_digital,
            "existing_customer": existing_customer,
            "exposed": exposed,
            "answer_yes": y,
            "responded": responded,
        }
    )
    respondents = pop[pop["responded"] == 1].drop(columns="responded").reset_index(drop=True)
    respondents.insert(0, "respondent_id", np.arange(len(respondents)))
    reference = pop[["age_group", "heavy_digital", "existing_customer"]].sample(
        n=min(20_000, n), random_state=seed
    ).reset_index(drop=True)
    reference.insert(0, "person_id", np.arange(len(reference)))

    # --- ground truth ------------------------------------------------------------------
    ate = float((p1 - p0).mean())
    att = float((p1 - p0)[exposed == 1].mean())
    naive_pop_diff = float(y[exposed == 1].mean() - y[exposed == 0].mean())
    truth = {
        "generated_with": {
            "n": n, "seed": seed, "observational": observational, "exposure_rate": exposure_rate,
            "response_rate": response_rate, "lift_pp": lift_pp,
            "lift_pp_heavy_digital": lift_pp_heavy_digital,
        },
        # What a model is supposed to recover, in percentage points of "yes".
        "true_lift_ate_pp": 100 * ate,
        "true_lift_att_pp": 100 * att,
        "true_lift_by_segment_pp": {
            "heavy_digital=0": 100 * lift_pp,
            "heavy_digital=1": 100 * (lift_pp + lift_pp_heavy_digital),
        },
        "population_baseline_yes_pct": 100 * float(p0.mean()),
        # Size of each bias mechanism, so the experiment can say *why* an estimator failed.
        "bias_diagnostics": {
            "naive_diff_in_population_pp": 100 * naive_pop_diff,
            "confounding_pp": 100 * (naive_pop_diff - att),
            "exposure_rate_population": float(exposed.mean()),
            "exposure_rate_respondents": float(respondents["exposed"].mean()),
            "response_rate_exposed": float(responded[exposed == 1].mean()),
            "response_rate_control": float(responded[exposed == 0].mean()),
            "heavy_digital_share_population": float(heavy_digital.mean()),
            "heavy_digital_share_respondents": float(respondents["heavy_digital"].mean()),
        },
        "n_respondents": len(respondents),
    }
    return respondents, reference, truth


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=200_000, help="population size")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--observational", action="store_true",
                        help="exposure follows covariates instead of being randomised")
    parser.add_argument("--out", type=Path, default=Path("data/synthetic/brandlift_rct"))
    args = parser.parse_args()

    df, reference, truth = generate(args.n, args.seed, args.observational)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out.with_suffix(".csv"), index=False)
    reference.to_csv(f"{args.out}.population.csv", index=False)
    Path(f"{args.out}.truth.json").write_text(json.dumps(truth, indent=2))

    print(f"wrote {args.out}.csv ({len(df)} respondents of {args.n}) and {args.out}.truth.json")
    print(f"true lift: ATE {truth['true_lift_ate_pp']:.2f} pp · ATT {truth['true_lift_att_pp']:.2f} pp")
    b = truth["bias_diagnostics"]
    print(f"naive diff in population: {b['naive_diff_in_population_pp']:.2f} pp "
          f"(confounding {b['confounding_pp']:+.2f} pp)")
    print(f"heavy-digital share: population {b['heavy_digital_share_population']:.2f} → "
          f"respondents {b['heavy_digital_share_respondents']:.2f}")


if __name__ == "__main__":
    main()
