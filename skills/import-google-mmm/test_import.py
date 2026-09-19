"""Contract tests for the Google MMM Data Platform importer.

Run with the project venv: `.venv/bin/python skills/import-google-mmm/test_import.py`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[1]
IMPORTER = SKILL_DIR / "import.py"
GENERATOR = SKILL_DIR / "fixtures" / "generate_fixture.py"
EXPECTED_CANONICAL = SKILL_DIR / "fixtures" / "expected_canonical.csv"


def run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )


def make_fixture(target: Path, *arguments: str) -> Path:
    result = run(GENERATOR, "--out", str(target), *arguments)
    assert result.returncode == 0, result.stderr
    return target


class GoogleImporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._workdir = tempfile.TemporaryDirectory()
        cls.work = Path(cls._workdir.name)
        cls.fixture = make_fixture(cls.work / "google.csv")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._workdir.cleanup()

    def import_fixture(self, source: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        out = self.work / f"out_{source.stem}_{len(arguments)}"
        return run(IMPORTER, str(source), "--out", str(out), *arguments)

    def assert_single_line_failure(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        output = (result.stdout + result.stderr).strip()
        self.assertNotIn("Traceback", output)
        self.assertEqual(len(output.splitlines()), 1, output)

    def test_happy_path_matches_expected_canonical(self) -> None:
        out = self.work / "canonical"
        report = self.work / "report.json"
        result = run(
            IMPORTER, str(self.fixture), "--out", str(out), "--report", str(report)
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            out.with_suffix(".csv").read_text(), EXPECTED_CANONICAL.read_text()
        )
        frame = pd.read_csv(out.with_suffix(".csv"))
        self.assertEqual(
            list(frame.columns), ["date", "geo", "channel", "spend", "impressions", "clicks"]
        )
        meta = json.loads(Path(f"{out}.meta.json").read_text())
        self.assertEqual(
            set(meta),
            {"schema_version", "currency", "granularity", "timezone", "source_platform"},
        )
        self.assertEqual(meta["currency"], "EUR")
        self.assertEqual(meta["granularity"], "weekly-mon")
        payload = json.loads(report.read_text())
        self.assertLessEqual(
            {
                "column_mapping",
                "ignored_columns",
                "dropped_rows",
                "currency_detected",
                "granularity_detected",
            },
            set(payload),
        )
        self.assertEqual(payload["currency_detected"], "EUR")
        self.assertIn("CostUsd", payload["ignored_columns"])

    def test_dry_run_without_out_validates_and_writes_nothing(self) -> None:
        before = sorted(path.name for path in self.work.iterdir())

        result = run(IMPORTER, str(self.fixture))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry run", result.stdout)
        self.assertEqual(sorted(path.name for path in self.work.iterdir()), before)

    def test_dry_run_propagates_a_schema_failure(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame.loc[0, "Cost"] = -10.0
        negative = self.work / "dry_negative.csv"
        frame.to_csv(negative, index=False)

        result = run(IMPORTER, str(negative))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_report_defaults_to_stdout_summary(self) -> None:
        result = self.import_fixture(self.fixture)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("granularity weekly-mon", result.stdout)

    def test_utf8_bom_is_transparent(self) -> None:
        bom = self.work / "google_bom.csv"
        bom.write_text(self.fixture.read_text(), encoding="utf-8-sig")
        out = self.work / "canonical_bom"

        result = run(IMPORTER, str(bom), "--out", str(out))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            out.with_suffix(".csv").read_text(), EXPECTED_CANONICAL.read_text()
        )

    def test_utf16_fails_with_one_line(self) -> None:
        utf16 = self.work / "google_utf16.csv"
        utf16.write_text(self.fixture.read_text(), encoding="utf-16")

        self.assert_single_line_failure(self.import_fixture(utf16))

    def test_empty_file_fails_with_one_line(self) -> None:
        empty = self.work / "empty.csv"
        empty.write_bytes(b"")

        self.assert_single_line_failure(self.import_fixture(empty))

    def test_header_only_file_fails_with_one_line(self) -> None:
        header_only = self.work / "header_only.csv"
        header_only.write_text(self.fixture.read_text().splitlines()[0] + "\n")

        self.assert_single_line_failure(self.import_fixture(header_only))

    def test_xlsx_is_rejected(self) -> None:
        book = self.work / "google.xlsx"
        book.write_bytes(b"not really a workbook")

        result = self.import_fixture(book)

        self.assert_single_line_failure(result)
        self.assertIn("XLSX no soportado", result.stdout + result.stderr)

    def test_missing_column_lists_expected_and_found(self) -> None:
        frame = pd.read_csv(self.fixture)
        trimmed = self.work / "missing_column.csv"
        frame.drop(columns=["Clicks"]).to_csv(trimmed, index=False)

        result = self.import_fixture(trimmed)

        self.assertEqual(result.returncode, 2)
        message = result.stdout + result.stderr
        self.assertIn("Clicks", message)
        self.assertIn("encontradas", message.lower())
        self.assertIn("espera", message)
        self.assertIn("CostUsd", message)

    def test_unknown_extra_column_is_not_ignored(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame["ExtraCol"] = 1
        extended = self.work / "extra_column.csv"
        frame.to_csv(extended, index=False)

        result = self.import_fixture(extended)

        self.assertEqual(result.returncode, 2)
        self.assertIn("ExtraCol", result.stdout + result.stderr)

    def test_reordered_header_still_maps_by_name(self) -> None:
        frame = pd.read_csv(self.fixture)
        shuffled = self.work / "reordered.csv"
        frame.loc[:, list(reversed(frame.columns))].to_csv(shuffled, index=False)
        out = self.work / "canonical_reordered"

        result = run(IMPORTER, str(shuffled), "--out", str(out))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            out.with_suffix(".csv").read_text(), EXPECTED_CANONICAL.read_text()
        )

    def test_unknown_product_stops_the_import(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame.loc[0, "Product"] = "Something New"
        unknown = self.work / "unknown_product.csv"
        frame.to_csv(unknown, index=False)

        result = self.import_fixture(unknown)

        self.assertEqual(result.returncode, 2)
        self.assertIn("Something New", result.stdout + result.stderr)

    def test_mixed_granularity_inside_one_file_stops_the_import(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame.loc[0, "TimeGranularity"] = "Daily"
        mixed = self.work / "mixed_granularity.csv"
        frame.to_csv(mixed, index=False)

        result = self.import_fixture(mixed)

        self.assertEqual(result.returncode, 2)
        self.assertIn("granularidades", result.stdout + result.stderr)

    def test_mixed_currency_inside_one_dv360_file_stops_the_import(self) -> None:
        dv360 = make_fixture(self.work / "dv360.csv", "--feed", "dv360")
        frame = pd.read_csv(dv360)
        frame.loc[0, "CurrencyCode"] = "USD"
        mixed = self.work / "dv360_mixed_currency.csv"
        frame.to_csv(mixed, index=False)

        result = self.import_fixture(mixed)

        self.assertEqual(result.returncode, 2)
        self.assertIn("monedas", result.stdout + result.stderr)

    def test_dv360_feed_imports_and_infers_granularity(self) -> None:
        dv360 = make_fixture(self.work / "dv360_ok.csv", "--feed", "dv360")
        out = self.work / "canonical_dv360"

        result = run(IMPORTER, str(dv360), "--out", str(out))

        self.assertEqual(result.returncode, 0, result.stderr)
        meta = json.loads(Path(f"{out}.meta.json").read_text())
        self.assertEqual(meta["granularity"], "weekly-mon")
        self.assertEqual(meta["source_platform"], "dv360-mmm")
        frame = pd.read_csv(out.with_suffix(".csv"))
        self.assertEqual(sorted(frame["channel"].unique()), ["audio", "display", "video"])

    def test_duplicate_primary_key_is_left_for_the_validator(self) -> None:
        frame = pd.read_csv(self.fixture)
        duplicated = self.work / "duplicated.csv"
        pd.concat([frame, frame.head(1)], ignore_index=True).to_csv(duplicated, index=False)

        result = self.import_fixture(duplicated)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("duplicates an earlier primary key", result.stdout)

    def test_negative_spend_is_left_for_the_validator(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame.loc[0, "Cost"] = -10.0
        negative = self.work / "negative_spend.csv"
        frame.to_csv(negative, index=False)

        result = self.import_fixture(negative)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("non-negative", result.stdout)

    def test_empty_spend_is_left_for_the_validator(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame.loc[0, "Cost"] = None
        blank = self.work / "blank_spend.csv"
        frame.to_csv(blank, index=False)

        result = self.import_fixture(blank)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("spend", result.stdout)

    def test_tracked_paths_need_the_explicit_flag(self) -> None:
        probe = REPO_ROOT / "tests" / "_guard_probe_google.csv"
        shutil.copyfile(self.fixture, probe)
        try:
            blocked_input = run(IMPORTER, str(probe), "--out", str(self.work / "guard_in"))
            blocked_out = run(IMPORTER, str(self.fixture), "--out", str(REPO_ROOT / "tests" / "_guard_out"))
            blocked_report = run(
                IMPORTER,
                str(self.fixture),
                "--out",
                str(self.work / "guard_report"),
                "--report",
                str(REPO_ROOT / "tests" / "_guard_report.json"),
            )
            allowed = run(
                IMPORTER,
                str(probe),
                "--out",
                str(self.work / "guard_allowed"),
                "--allow-tracked",
            )
        finally:
            probe.unlink(missing_ok=True)

        for blocked in (blocked_input, blocked_out, blocked_report):
            self.assert_single_line_failure(blocked)
            self.assertIn("--allow-tracked", blocked.stdout + blocked.stderr)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertFalse((REPO_ROOT / "tests" / "_guard_out.csv").exists())
        self.assertFalse((REPO_ROOT / "tests" / "_guard_report.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
