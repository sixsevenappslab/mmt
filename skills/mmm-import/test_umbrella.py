"""Contract tests for the umbrella importer: detection, skipping, alignment and refusals.

Run with the project venv: `.venv/bin/python skills/mmm-import/test_umbrella.py`.
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
UMBRELLA = SKILL_DIR / "detect_and_import.py"
GOOGLE_FIXTURES = REPO_ROOT / "skills" / "import-google-mmm" / "fixtures" / "generate_fixture.py"
META_FIXTURES = REPO_ROOT / "skills" / "import-meta-mmm" / "fixtures" / "generate_fixture.py"


def run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )


class UmbrellaTests(unittest.TestCase):
    def setUp(self) -> None:
        self._workdir = tempfile.TemporaryDirectory()
        self.work = Path(self._workdir.name)
        self.folder = self.work / "exports"
        self.folder.mkdir()

    def tearDown(self) -> None:
        self._workdir.cleanup()

    def google(self, name: str, *arguments: str) -> Path:
        target = self.folder / name
        result = run(GOOGLE_FIXTURES, "--out", str(target), *arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return target

    def umbrella(self, *extra: str) -> tuple:
        out = self.work / "union"
        report = self.work / "report.json"
        result = run(
            UMBRELLA, str(self.folder), "--out", str(out), "--report", str(report), *extra
        )
        payload = json.loads(report.read_text()) if report.exists() else None
        return result, out, payload

    def statuses(self, payload: dict) -> dict[str, str]:
        return {Path(entry["path"]).name: entry["status"] for entry in payload["files"]}

    def test_single_google_export_becomes_a_valid_union(self) -> None:
        self.google("google.csv")

        result, out, payload = self.umbrella()

        self.assertEqual(result.returncode, 0, result.stderr)
        frame = pd.read_csv(out.with_suffix(".csv"))
        self.assertEqual(
            list(frame.columns), ["date", "geo", "channel", "spend", "impressions", "clicks"]
        )
        self.assertEqual(payload["imported_count"], 1)
        self.assertEqual(payload["currency_detected"], "EUR")
        self.assertIn("ReportDate", payload["column_mapping"])

    def test_daily_and_weekly_are_aligned_to_the_weekly_anchor(self) -> None:
        self.google("google_weekly.csv", "--granularity", "weekly-mon", "--geo", "Spain")
        self.google("google_daily.csv", "--granularity", "daily", "--geo", "Portugal")

        result, out, payload = self.umbrella()

        self.assertEqual(result.returncode, 0, result.stderr)
        meta = json.loads(Path(f"{out}.meta.json").read_text())
        self.assertEqual(meta["granularity"], "weekly-mon")
        frame = pd.read_csv(out.with_suffix(".csv"))
        self.assertEqual(sorted(frame["geo"].unique()), ["Portugal", "Spain"])
        resampled = {Path(note["path"]).name for note in payload["resampling"]}
        self.assertEqual(resampled, {"google_daily.csv"})
        self.assertEqual(payload["resampling"][0]["resampled_to"], "weekly-mon")

    def test_a_missing_day_drops_that_week_instead_of_undercounting_it(self) -> None:
        """A platform that omits a day with no activity must not shrink the weekly total."""
        self.google("google_weekly.csv", "--granularity", "weekly-mon", "--geo", "Spain")
        daily = self.google("google_daily.csv", "--granularity", "daily", "--geo", "Portugal")
        frame = pd.read_csv(daily)
        gap = (frame["ReportDate"] == "2023-01-04") & (frame["Product"] == "Search")
        self.assertTrue(gap.any())
        frame[~gap].to_csv(daily, index=False)

        result, out, payload = self.umbrella()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        dropped = payload["resampling"][0]["dropped_partial_weeks"]
        self.assertTrue(
            any(
                item["week"] == "2023-01-02"
                and item["geo"] == "Portugal"
                and item["channel"] == "search"
                and item["days_present"] == 6
                for item in dropped
            ),
            dropped,
        )
        union = pd.read_csv(out.with_suffix(".csv"))
        holed = union[
            (union["date"] == "2023-01-02")
            & (union["geo"] == "Portugal")
            & (union["channel"] == "search")
        ]
        self.assertTrue(holed.empty, "la semana incompleta no debe llegar a la union")
        intact = union[
            (union["date"] == "2023-01-02")
            & (union["geo"] == "Portugal")
            & (union["channel"] == "video")
        ]
        self.assertEqual(len(intact), 1, "las demas series de esa semana siguen enteras")

    def test_two_weekly_anchors_stop_the_run(self) -> None:
        self.google("google_mon.csv", "--granularity", "weekly-mon", "--geo", "Spain")
        self.google("google_sun.csv", "--granularity", "weekly-sun", "--geo", "Portugal")

        result, out, payload = self.umbrella()

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        message = result.stdout + result.stderr
        self.assertIn("ancla", message)
        self.assertIn("google_mon.csv", message)
        self.assertIn("google_sun.csv", message)
        self.assertFalse(out.with_suffix(".csv").exists())
        self.assertIsNotNone(payload, "el informe debe escribirse tambien al abortar")
        self.assertIn("ancla", payload["aborted_because"])
        anchors = {
            Path(entry["path"]).name: entry.get("granularity")
            for entry in payload["files"]
            if entry["status"] == "imported"
        }
        self.assertEqual(anchors, {"google_mon.csv": "weekly-mon", "google_sun.csv": "weekly-sun"})

    def test_mixed_currency_between_files_stops_the_run(self) -> None:
        self.google("google_eur.csv")
        self.google("dv360_usd.csv", "--feed", "dv360", "--currency", "USD", "--geo", "Portugal")

        result, out, payload = self.umbrella()

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        message = result.stdout + result.stderr
        self.assertIn("monedas", message)
        self.assertIn("dv360_usd.csv", message)
        self.assertFalse(out.with_suffix(".csv").exists())
        self.assertIsNotNone(payload, "el informe debe escribirse tambien al abortar")
        currencies = {
            Path(entry["path"]).name: entry.get("currency")
            for entry in payload["files"]
            if entry["status"] == "imported"
        }
        self.assertEqual(currencies, {"google_eur.csv": "EUR", "dv360_usd.csv": "USD"})

    def test_unknown_and_unreadable_files_are_skipped_not_fatal(self) -> None:
        self.google("google.csv")
        (self.folder / "notes.txt").write_text("not an export\n")
        (self.folder / "random.csv").write_text("alpha,beta\n1,2\n")
        (self.folder / "empty.csv").write_bytes(b"")
        meta_fixture = self.folder / "meta.csv"
        self.assertEqual(run(META_FIXTURES, "--out", str(meta_fixture)).returncode, 0)

        result, out, payload = self.umbrella()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        statuses = self.statuses(payload)
        self.assertEqual(statuses["google.csv"], "imported")
        for name in ("notes.txt", "random.csv", "empty.csv", "meta.csv"):
            self.assertEqual(statuses[name], "skipped", name)
        reasons = {
            Path(entry["path"]).name: entry["reason"] or ""
            for entry in payload["files"]
            if entry["status"] == "skipped"
        }
        self.assertIn("solo CSV", reasons["notes.txt"])
        self.assertIn("ningun contrato confirmado", reasons["random.csv"])
        self.assertIn("ningun contrato confirmado", reasons["meta.csv"])
        self.assertTrue(out.with_suffix(".csv").exists())

    def test_folder_with_nothing_importable_exits_two_with_a_report(self) -> None:
        (self.folder / "notes.txt").write_text("not an export\n")
        (self.folder / "random.csv").write_text("alpha,beta\n1,2\n")

        result, out, payload = self.umbrella()

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(payload["imported_count"], 0)
        self.assertEqual(payload["skipped_count"], 2)
        self.assertFalse(out.with_suffix(".csv").exists())

    def test_overlapping_files_are_left_for_the_validator(self) -> None:
        self.google("google_a.csv")
        shutil.copyfile(self.folder / "google_a.csv", self.folder / "google_b.csv")

        result, _out, payload = self.umbrella()

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(payload["imported_count"], 2)
        self.assertIn("duplicates an earlier primary key", result.stdout)

    def test_tracked_paths_need_the_explicit_flag(self) -> None:
        self.google("google.csv")
        blocked_out = run(
            UMBRELLA, str(self.folder), "--out", str(REPO_ROOT / "tests" / "_guard_union")
        )
        blocked_report = run(
            UMBRELLA,
            str(self.folder),
            "--out",
            str(self.work / "guard_union"),
            "--report",
            str(REPO_ROOT / "tests" / "_guard_union_report.json"),
        )
        probe_dir = REPO_ROOT / "tests" / "_guard_probe_dir"
        probe_dir.mkdir(exist_ok=True)
        shutil.copyfile(self.folder / "google.csv", probe_dir / "google.csv")
        try:
            blocked_input = run(
                UMBRELLA, str(probe_dir), "--out", str(self.work / "guard_union_in")
            )
            allowed = run(
                UMBRELLA,
                str(probe_dir),
                "--out",
                str(self.work / "guard_union_allowed"),
                "--allow-tracked",
            )
        finally:
            shutil.rmtree(probe_dir, ignore_errors=True)

        for blocked in (blocked_out, blocked_report, blocked_input):
            self.assertEqual(blocked.returncode, 2, blocked.stdout + blocked.stderr)
            self.assertIn("--allow-tracked", blocked.stdout + blocked.stderr)
            self.assertNotIn("Traceback", blocked.stdout + blocked.stderr)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertFalse((REPO_ROOT / "tests" / "_guard_union.csv").exists())
        self.assertFalse((REPO_ROOT / "tests" / "_guard_union_report.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
