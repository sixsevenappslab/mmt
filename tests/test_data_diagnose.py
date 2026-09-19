from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCRIPT = ROOT / "skills" / "mmm-data-diagnose" / "diagnose.py"


def run_diagnose(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments], text=True, capture_output=True, check=False
    )


class DataDiagnoseTests(unittest.TestCase):
    def test_reports_each_requested_risk_without_failing(self) -> None:
        result = run_diagnose(
            "--input", str(FIXTURES / "diagnostic_canonical.csv"), "--allow-tracked", "--json"
        )

        payload = json.loads(result.stdout)
        checks = {finding["check"] for finding in payload["findings"]}
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            {
                "duplicate_dates",
                "missing_dates",
                "spend_without_impressions",
                "impressions_without_spend",
                "incomplete_impression_coverage",
                "scale_jump",
                "low_variation",
                "short_time_range",
            }.issubset(checks)
        )
        self.assertTrue(all(finding["recommendation"] for finding in payload["findings"]))

    def test_media_only_is_explicit_in_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "media.csv"
            frame = pd.read_csv(FIXTURES / "tiny_canonical.csv").drop(
                columns=["kpi", "control_price_index"]
            )
            frame.to_csv(path, index=False)
            path.with_suffix(".meta.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "currency": "EUR",
                        "granularity": "weekly-mon",
                        "timezone": "Europe/Madrid",
                    }
                )
            )
            result = run_diagnose("--input", str(path), "--media-only", "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["summary"]["mode"], "media-only")
        self.assertEqual(payload["summary"]["checks_omitted"], [])
        self.assertNotIn("kpi", payload["summary"]["columns_used"])

    def test_unreadable_input_returns_one_clean_error_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "empty.csv"
            empty.write_text("")
            result = run_diagnose("--input", str(empty))

        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(len(result.stderr.splitlines()), 1)


    def test_weekly_series_not_anchored_on_monday_has_no_missing_dates(self) -> None:
        """A regular Tuesday-to-Tuesday weekly export is not a series with gaps."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tuesday.csv"
            frame = pd.read_csv(FIXTURES / "tiny_canonical.csv")
            frame["date"] = (pd.to_datetime(frame["date"]) + pd.Timedelta(days=1)).dt.strftime(
                "%Y-%m-%d"
            )
            frame.to_csv(path, index=False)
            path.with_suffix(".meta.json").write_text(
                (FIXTURES / "tiny_canonical.meta.json").read_text()
            )
            result = run_diagnose("--input", str(path), "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("missing_dates", {finding["check"] for finding in payload["findings"]})


if __name__ == "__main__":
    unittest.main()
