from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMA_DIR = ROOT / "skills" / "mmm-ready-schema"
sys.path.insert(0, str(SCHEMA_DIR))
from schema import long_to_meridian_wide, long_to_pymc_wide


class SchemaConvertTests(unittest.TestCase):
    def test_national_conversions_are_wide(self) -> None:
        frame = pd.read_csv(FIXTURES / "tiny_canonical.csv")

        meridian = long_to_meridian_wide(frame)
        pymc = long_to_pymc_wide(frame)

        base = ["time", "kpi", "control_price_index", "spend_search", "spend_social"]
        self.assertEqual(meridian.columns.tolist(), base + ["impressions_search", "impressions_social"])
        self.assertEqual(pymc.columns.tolist(), base)
        self.assertEqual(meridian.loc[0, "impressions_search"], 1000)
        self.assertEqual(len(meridian), 8)
        self.assertEqual(meridian.loc[0, "time"], "2024-01-01")

    def test_meridian_keeps_multi_geo_and_pymc_rejects_it(self) -> None:
        frame = pd.read_csv(FIXTURES / "tiny_canonical_2geo.csv")

        meridian = long_to_meridian_wide(frame)

        self.assertEqual(meridian.columns.tolist()[0:2], ["time", "geo"])
        self.assertEqual(len(meridian), 8)
        with self.assertRaisesRegex(ValueError, "dims"):
            long_to_pymc_wide(frame)

    def test_cli_requires_explicit_allow_for_tracked_fixture(self) -> None:
        command = [
            sys.executable,
            str(SCHEMA_DIR / "convert.py"),
            "--input",
            str(FIXTURES / "tiny_canonical.csv"),
            "--to",
            "meridian",
            "--out",
            str(Path(tempfile.gettempdir()) / "mmt-convert-guard.csv"),
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)

        self.assertEqual(result.returncode, 2)
        self.assertIn("--allow-tracked", result.stderr)

    def test_cli_converts_and_guards_tracked_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            output = temp / "pymc.csv"
            command = [
                sys.executable,
                str(SCHEMA_DIR / "convert.py"),
                "--input",
                str(FIXTURES / "tiny_canonical.csv"),
                "--to",
                "pymc",
                "--out",
                str(output),
                "--allow-tracked",
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())

            guarded_output = ROOT / "must-not-write.csv"
            outside_input = temp / "input.csv"
            outside_input.write_text((FIXTURES / "tiny_canonical.csv").read_text())
            guarded = subprocess.run(
                [
                    sys.executable,
                    str(SCHEMA_DIR / "convert.py"),
                    "--input",
                    str(outside_input),
                    "--to",
                    "meridian",
                    "--out",
                    str(guarded_output),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(guarded.returncode, 2)
            self.assertIn("--allow-tracked", guarded.stderr)
            self.assertFalse(guarded_output.exists())

    def test_cli_reports_missing_metadata_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "without-meta.csv"
            path.write_text((FIXTURES / "tiny_canonical.csv").read_text())
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCHEMA_DIR / "convert.py"),
                    "--input",
                    str(path),
                    "--to",
                    "meridian",
                    "--out",
                    str(Path(directory) / "output.csv"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(len(result.stderr.splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
