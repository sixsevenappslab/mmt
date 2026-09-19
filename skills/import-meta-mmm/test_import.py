"""Contract tests for the Meta MMM importer, confirmed and unconfirmed paths alike.

Run with the project venv: `.venv/bin/python skills/import-meta-mmm/test_import.py`.
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
UNCONFIRMED = "sin cabecera confirmada"


def run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )


class MetaImporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._workdir = tempfile.TemporaryDirectory()
        cls.work = Path(cls._workdir.name)
        cls.fixture = cls.work / "meta.csv"
        result = run(GENERATOR, "--out", str(cls.fixture))
        assert result.returncode == 0, result.stderr

    @classmethod
    def tearDownClass(cls) -> None:
        cls._workdir.cleanup()

    def import_trusted(self, source: Path, name: str, *extra: str) -> tuple:
        out = self.work / f"canonical_{name}"
        result = run(IMPORTER, str(source), "--out", str(out), "--trust-unconfirmed", *extra)
        return result, out

    def assert_single_line_failure(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        output = (result.stdout + result.stderr).strip()
        self.assertNotIn("Traceback", output)
        self.assertEqual(len(output.splitlines()), 1, output)

    def test_default_run_refuses_an_unconfirmed_contract(self) -> None:
        result = run(IMPORTER, str(self.fixture), "--out", str(self.work / "never"))

        self.assert_single_line_failure(result)
        self.assertIn(UNCONFIRMED, result.stdout + result.stderr)
        self.assertFalse((self.work / "never.csv").exists())

    def test_bare_invocation_reports_the_contract_not_a_missing_flag(self) -> None:
        """`import.py <csv>` with no other argument, exactly as the spec writes it."""
        result = run(IMPORTER, str(self.fixture))

        self.assert_single_line_failure(result)
        self.assertIn(UNCONFIRMED, result.stdout + result.stderr)

    def test_dry_run_without_out_validates_and_writes_nothing(self) -> None:
        before = sorted(path.name for path in self.work.iterdir())

        result = run(IMPORTER, str(self.fixture), "--trust-unconfirmed")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry run", result.stdout)
        self.assertEqual(sorted(path.name for path in self.work.iterdir()), before)

    def test_trusted_run_matches_expected_canonical(self) -> None:
        report = self.work / "report.json"
        result, out = self.import_trusted(self.fixture, "happy", "--report", str(report))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(out.with_suffix(".csv").read_text(), EXPECTED_CANONICAL.read_text())
        frame = pd.read_csv(out.with_suffix(".csv"))
        self.assertEqual(
            list(frame.columns), ["date", "geo", "channel", "spend", "impressions", "clicks"]
        )
        self.assertEqual(sorted(frame["channel"].unique()), ["meta"])
        self.assertTrue(frame["clicks"].isna().all())
        meta = json.loads(Path(f"{out}.meta.json").read_text())
        self.assertEqual(meta["granularity"], "daily")
        self.assertEqual(meta["source_platform"], "meta-mmm")
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
        self.assertFalse(payload["header_contract_confirmed"])

    def test_channel_by_column_overrides_the_single_channel(self) -> None:
        result, out = self.import_trusted(
            self.fixture, "channel_by", "--channel-by", "publisher_platform"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        frame = pd.read_csv(out.with_suffix(".csv"))
        self.assertEqual(sorted(frame["channel"].unique()), ["facebook"])

    def test_utf8_bom_is_transparent(self) -> None:
        bom = self.work / "meta_bom.csv"
        bom.write_text(self.fixture.read_text(), encoding="utf-8-sig")

        result, out = self.import_trusted(bom, "bom")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(out.with_suffix(".csv").read_text(), EXPECTED_CANONICAL.read_text())

    def test_unreadable_inputs_fail_with_one_line(self) -> None:
        utf16 = self.work / "meta_utf16.csv"
        utf16.write_text(self.fixture.read_text(), encoding="utf-16")
        empty = self.work / "meta_empty.csv"
        empty.write_bytes(b"")
        header_only = self.work / "meta_header_only.csv"
        header_only.write_text(self.fixture.read_text().splitlines()[0] + "\n")
        book = self.work / "meta.xlsx"
        book.write_bytes(b"not really a workbook")

        for index, source in enumerate((utf16, empty, header_only, book)):
            with self.subTest(source=source.name):
                result, _ = self.import_trusted(source, f"unreadable{index}")
                self.assert_single_line_failure(result)

    def test_missing_column_lists_expected_and_found(self) -> None:
        frame = pd.read_csv(self.fixture)
        trimmed = self.work / "meta_missing.csv"
        frame.drop(columns=["dma"]).to_csv(trimmed, index=False)

        result, _ = self.import_trusted(trimmed, "missing")

        self.assertEqual(result.returncode, 2)
        message = result.stdout + result.stderr
        self.assertIn("dma", message)
        self.assertIn("encontradas", message.lower())

    def test_multi_period_row_is_rejected(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame.loc[0, "date_stop"] = "2023-12-31"
        spanning = self.work / "meta_multi_period.csv"
        frame.to_csv(spanning, index=False)

        result, _ = self.import_trusted(spanning, "multi_period")

        self.assertEqual(result.returncode, 2)
        self.assertIn("time_increment=1", result.stdout + result.stderr)

    def test_blank_date_stop_says_so_instead_of_blaming_the_period(self) -> None:
        frame = pd.read_csv(self.fixture)
        frame.loc[0, "date_stop"] = None
        blank = self.work / "meta_blank_stop.csv"
        frame.to_csv(blank, index=False)

        result, _ = self.import_trusted(blank, "blank_stop")

        self.assertEqual(result.returncode, 2)
        message = result.stdout + result.stderr
        self.assertIn("date_stop vacio", message)
        self.assertNotIn("mas de un periodo", message)

    def test_tracked_paths_need_the_explicit_flag(self) -> None:
        probe = REPO_ROOT / "tests" / "_guard_probe_meta.csv"
        shutil.copyfile(self.fixture, probe)
        try:
            blocked_input = run(
                IMPORTER, str(probe), "--out", str(self.work / "guard_in"), "--trust-unconfirmed"
            )
            blocked_out = run(
                IMPORTER,
                str(self.fixture),
                "--out",
                str(REPO_ROOT / "tests" / "_guard_out_meta"),
                "--trust-unconfirmed",
            )
            allowed = run(
                IMPORTER,
                str(probe),
                "--out",
                str(self.work / "guard_allowed"),
                "--trust-unconfirmed",
                "--allow-tracked",
            )
        finally:
            probe.unlink(missing_ok=True)

        for blocked in (blocked_input, blocked_out):
            self.assert_single_line_failure(blocked)
            self.assertIn("--allow-tracked", blocked.stdout + blocked.stderr)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertFalse((REPO_ROOT / "tests" / "_guard_out_meta.csv").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
