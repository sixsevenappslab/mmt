"""The geo panel generator: valid canonical output, honest lift, and refusals that explain."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "generators" / "synthetic_geo_mmm.py"
VALIDATOR = ROOT / "skills" / "mmm-data-validate" / "validate.py"
BASE = ("--weeks", "60", "--geos", "12", "--seed", "7")
WINDOW = ("--treated", "3", "--test-start", "40", "--test-weeks", "10")


def run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    )


class GeoGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._workdir = tempfile.TemporaryDirectory()
        cls.work = Path(cls._workdir.name)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._workdir.cleanup()

    def build(self, name: str, *extra: str) -> tuple[Path, dict]:
        prefix = self.work / name
        result = run(GENERATOR, *BASE, "--out", str(prefix), *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        truth = json.loads(Path(f"{prefix}.truth.json").read_text())
        return prefix, truth

    def assert_single_line_failure(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        output = (result.stdout + result.stderr).strip()
        self.assertNotIn("Traceback", output)
        self.assertEqual(len(output.splitlines()), 1, output)

    def test_output_passes_the_full_schema_validator(self) -> None:
        prefix, _ = self.build("valid", "--design", "go-dark", *WINDOW)

        result = run(VALIDATOR, "--input", str(prefix.with_suffix(".csv")), "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["ok"], payload["errors"][:5])
        self.assertEqual(len(payload["summary"]["geos"]), 12)
        frame = pd.read_csv(prefix.with_suffix(".csv"))
        self.assertEqual(
            list(frame.columns),
            ["date", "geo", "channel", "spend", "impressions", "clicks", "kpi",
             "control_price_index"],
        )

    def test_population_is_a_real_distribution(self) -> None:
        _, truth = self.build("population", "--design", "none")

        population = truth["population_by_geo"]
        self.assertEqual(len(population), 12)
        self.assertAlmostEqual(sum(population.values()), 1.0, places=9)
        self.assertTrue(all(share > 0 for share in population.values()), population)

    def test_no_design_means_no_experiment_keys(self) -> None:
        _, truth = self.build("plain", "--design", "none")

        self.assertNotIn("experiment", truth)
        self.assertNotIn("true_incremental_kpi", truth)
        self.assertIn("true_roi", truth)

    def test_each_design_moves_the_kpi_the_right_way(self) -> None:
        cases = {
            "go-dark": (("--design", "go-dark"), -1),
            "holdback": (("--design", "holdback", "--holdback-channel", "video"), -1),
            "heavy-up": (("--design", "heavy-up", "--effect-size", "1.0"), 1),
        }
        for name, (flags, sign) in cases.items():
            with self.subTest(design=name):
                _, truth = self.build(f"design_{name}", *flags, *WINDOW)
                incremental = truth["true_incremental_kpi"]
                self.assertEqual(
                    sign, 1 if incremental > 0 else -1, f"{name} dio {incremental}"
                )
                self.assertEqual(truth["experiment"]["design"], name)
                self.assertEqual(len(truth["experiment"]["treatment_geos"]), 3)
                self.assertEqual(len(truth["experiment"]["control_geos"]), 9)

    def test_roi_without_experiment_does_not_move_with_the_design(self) -> None:
        """The fixed channel property has to stay fixed; the observed one is allowed to move.

        Average ROI is contribution over spend, so cutting spend pushes a channel down its
        saturation curve and raises what it returns per euro. `true_roi` therefore moves with
        the design — correctly, it describes the panel as written — and
        `true_roi_without_experiment` must not, because it describes the untouched world.
        """
        _, plain = self.build("roi_plain", "--design", "none")
        _, mild = self.build("roi_mild", "--design", "go-dark", *WINDOW)
        _, wide = self.build(
            "roi_wide", "--design", "go-dark", "--treated", "11",
            "--test-start", "5", "--test-weeks", "55",
        )

        for channel, baseline_roi in plain["true_roi"].items():
            with self.subTest(channel=channel):
                self.assertAlmostEqual(
                    baseline_roi, mild["true_roi_without_experiment"][channel], places=9
                )
                self.assertAlmostEqual(
                    baseline_roi, wide["true_roi_without_experiment"][channel], places=9
                )
        self.assertAlmostEqual(
            plain["true_baseline_share"],
            wide["true_baseline_share_without_experiment"],
            places=9,
        )
        # And the observed one really does move, which is the fact the note exists to explain.
        self.assertNotAlmostEqual(
            plain["true_roi"]["social"], wide["true_roi"]["social"], places=2
        )
        self.assertIn("saturation curve", wide["roi_basis"])

    def test_placebo_leaves_both_the_plan_and_the_lift_untouched(self) -> None:
        placebo, truth = self.build("placebo", "--design", "go-dark", "--effect-size", "0", *WINDOW)
        plain, _ = self.build("plain_spend", "--design", "none")

        self.assertEqual(truth["true_incremental_kpi"], 0.0)
        self.assertEqual(truth["true_lift_pct"], 0.0)
        placebo_spend = pd.read_csv(placebo.with_suffix(".csv"))["spend"]
        plain_spend = pd.read_csv(plain.with_suffix(".csv"))["spend"]
        pd.testing.assert_series_equal(placebo_spend, plain_spend)

    def test_control_geos_come_out_bit_identical(self) -> None:
        """The property the whole panel rests on: the experiment must not leak into controls.

        GeoLift and CausalImpact build their counterfactual out of the control regions. If a
        treated region could move a control one — through shared noise, shared adstock, a
        mutated array — every estimate built on those controls would be quietly wrong. So the
        controls of an experimental run have to match a no-experiment run to the bit.
        """
        for design, extra in (
            ("go-dark", ()),
            ("holdback", ("--holdback-channel", "video")),
            ("heavy-up", ("--effect-size", "1.0")),
        ):
            with self.subTest(design=design):
                treated_run, truth = self.build(
                    f"leak_{design}", "--design", design, *extra, *WINDOW
                )
                plain_run, _ = self.build(f"leak_plain_{design}", "--design", "none")

                treated = set(truth["experiment"]["treatment_geos"])
                with_experiment = pd.read_csv(treated_run.with_suffix(".csv"))
                without = pd.read_csv(plain_run.with_suffix(".csv"))
                controls = ~with_experiment["geo"].isin(treated)
                pd.testing.assert_frame_equal(
                    with_experiment[controls].reset_index(drop=True),
                    without[controls.to_numpy()].reset_index(drop=True),
                )

    def test_placebo_is_exact_in_every_design(self) -> None:
        for design, extra in (
            ("go-dark", ()),
            ("holdback", ("--holdback-channel", "video")),
            ("heavy-up", ()),
        ):
            with self.subTest(design=design):
                _, truth = self.build(
                    f"placebo_{design}", "--design", design, "--effect-size", "0", *extra, *WINDOW
                )
                self.assertEqual(truth["true_incremental_kpi"], 0.0)
                self.assertEqual(truth["true_incremental_kpi_including_carryover"], 0.0)

    def test_carryover_is_reported_and_points_the_same_way(self) -> None:
        """Adstock keeps paying after the window; the truth has to say so, not hide it."""
        _, truth = self.build("carryover", "--design", "go-dark", *WINDOW)

        in_window = truth["true_incremental_kpi"]
        total = truth["true_incremental_kpi_including_carryover"]
        self.assertLess(abs(in_window), abs(total), "el eco posterior tiene que sumar efecto")
        self.assertEqual(in_window < 0, total < 0, "los dos miran al mismo lado")
        self.assertGreater(truth["carryover_share_of_effect"], 0)
        self.assertIn("adstock keeps", truth["incremental_basis"])

    def test_nothing_pathological_across_seeds_and_sizes(self) -> None:
        """A generator nobody sweeps is a generator that breaks on the seed you happen to pick."""
        for geos in (2, 3, 50):
            for seed in (1, 99):
                with self.subTest(geos=geos, seed=seed):
                    prefix = self.work / f"sweep_{geos}_{seed}"
                    result = run(
                        GENERATOR, "--weeks", "40", "--geos", str(geos), "--seed", str(seed),
                        "--design", "go-dark", "--treated", "1", "--test-start", "20",
                        "--test-weeks", "8", "--out", str(prefix),
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    frame = pd.read_csv(prefix.with_suffix(".csv"))
                    self.assertFalse(frame[["spend", "kpi"]].isna().any().any())
                    self.assertGreater(frame["kpi"].min(), 0)
                    self.assertGreaterEqual(frame["spend"].min(), 0)
                    truth = json.loads(Path(f"{prefix}.truth.json").read_text())
                    self.assertAlmostEqual(sum(truth["population_by_geo"].values()), 1.0, places=9)
                    self.assertLess(truth["true_incremental_kpi"], 0)

    def test_holdback_only_touches_its_channel(self) -> None:
        prefix, truth = self.build(
            "holdback_scope", "--design", "holdback", "--holdback-channel", "video", *WINDOW
        )

        frame = pd.read_csv(prefix.with_suffix(".csv"))
        window = truth["experiment"]["test_window"]
        treated = truth["experiment"]["treatment_geos"]
        inside = (
            frame["geo"].isin(treated)
            & (frame["date"] >= window["start_date"])
            & (frame["date"] <= window["end_date"])
        )
        self.assertEqual(frame.loc[inside & (frame["channel"] == "video"), "spend"].sum(), 0.0)
        self.assertGreater(frame.loc[inside & (frame["channel"] != "video"), "spend"].sum(), 0.0)

    def test_same_seed_is_byte_identical(self) -> None:
        first, _ = self.build("det_a", "--design", "go-dark", *WINDOW)
        second, _ = self.build("det_b", "--design", "go-dark", *WINDOW)

        self.assertEqual(
            first.with_suffix(".csv").read_bytes(), second.with_suffix(".csv").read_bytes()
        )
        self.assertEqual(
            Path(f"{first}.truth.json").read_bytes(), Path(f"{second}.truth.json").read_bytes()
        )

    def test_invalid_combinations_stop_with_one_line(self) -> None:
        cases = {
            "treated 0": ("--design", "go-dark", "--treated", "0", "--test-start", "40",
                          "--test-weeks", "10"),
            "treated = geos": ("--design", "go-dark", "--treated", "12", "--test-start", "40",
                               "--test-weeks", "10"),
            "treated > geos": ("--design", "go-dark", "--treated", "99", "--test-start", "40",
                               "--test-weeks", "10"),
            "window overflows": ("--design", "go-dark", "--treated", "3", "--test-start", "55",
                                 "--test-weeks", "10"),
            "pre-test too short": ("--design", "go-dark", "--treated", "3", "--test-start", "2",
                                   "--test-weeks", "10"),
            "effect-size over 1": ("--design", "go-dark", "--effect-size", "1.5", *WINDOW),
            "unknown channel": ("--design", "holdback", "--holdback-channel", "tiktok", *WINDOW),
            "no weeks": ("--weeks", "0", "--design", "none"),
            "too few weeks": ("--weeks", "2", "--design", "none"),
            "treated without a design": ("--design", "none", "--treated", "99"),
            "negative treated": ("--design", "none", "--treated", "-1"),
        }
        for name, flags in cases.items():
            with self.subTest(case=name):
                result = run(GENERATOR, *BASE, "--out", str(self.work / "never"), *flags)
                self.assert_single_line_failure(result)
                self.assertFalse((self.work / "never.csv").exists())

    def test_metadata_sidecar_matches_the_panel(self) -> None:
        prefix, truth = self.build("sidecar", "--design", "none")

        meta = json.loads(Path(f"{prefix}.meta.json").read_text())
        self.assertEqual(meta["schema_version"], "1.0")
        self.assertEqual(meta["currency"], "EUR")
        self.assertEqual(meta["granularity"], "weekly-mon")
        self.assertEqual(meta["geos"], sorted(truth["population_by_geo"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
