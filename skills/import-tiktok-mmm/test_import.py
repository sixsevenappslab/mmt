"""Contract tests for the TikTok stub: it must fail, with that exact message, every time.

Run with the project venv: `.venv/bin/python skills/import-tiktok-mmm/test_import.py`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[1]
IMPORTER = SKILL_DIR / "import.py"
GENERATOR = SKILL_DIR / "fixtures" / "generate_fixture.py"
CONTRACT = SKILL_DIR / "expected_headers.json"
UNCONFIRMED = "sin cabecera confirmada"


def run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )


class TikTokStubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._workdir = tempfile.TemporaryDirectory()
        cls.work = Path(cls._workdir.name)
        cls.fixture = cls.work / "tiktok.csv"
        result = run(GENERATOR, "--out", str(cls.fixture))
        assert result.returncode == 0, result.stderr

    @classmethod
    def tearDownClass(cls) -> None:
        cls._workdir.cleanup()

    def assert_single_line_failure(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        output = (result.stdout + result.stderr).strip()
        self.assertNotIn("Traceback", output)
        self.assertEqual(len(output.splitlines()), 1, output)

    def test_contract_stays_unconfirmed(self) -> None:
        contract = json.loads(CONTRACT.read_text())

        self.assertFalse(contract["confirmed"])
        self.assertEqual(contract["columns"], ["_TODO_bring_real_export_header"])
        self.assertTrue(contract["source_url"])
        self.assertTrue(contract["caveat"])

    def test_illustrative_fixture_is_rejected(self) -> None:
        result = run(IMPORTER, str(self.fixture))

        self.assert_single_line_failure(result)
        self.assertIn(UNCONFIRMED, result.stdout + result.stderr)

    def test_any_other_header_is_rejected_too(self) -> None:
        other = self.work / "whatever.csv"
        other.write_text("a,b,c\n1,2,3\n")

        result = run(IMPORTER, str(other))

        self.assert_single_line_failure(result)
        self.assertIn(UNCONFIRMED, result.stdout + result.stderr)

    def test_utf8_bom_reaches_the_contract_check(self) -> None:
        bom = self.work / "tiktok_bom.csv"
        bom.write_text(self.fixture.read_text(), encoding="utf-8-sig")

        result = run(IMPORTER, str(bom))

        self.assert_single_line_failure(result)
        self.assertIn(UNCONFIRMED, result.stdout + result.stderr)

    def test_unreadable_inputs_fail_with_one_line(self) -> None:
        utf16 = self.work / "tiktok_utf16.csv"
        utf16.write_text(self.fixture.read_text(), encoding="utf-16")
        empty = self.work / "tiktok_empty.csv"
        empty.write_bytes(b"")
        header_only = self.work / "tiktok_header_only.csv"
        header_only.write_text(self.fixture.read_text().splitlines()[0] + "\n")
        book = self.work / "tiktok.xlsx"
        book.write_bytes(b"not really a workbook")

        for source in (utf16, empty, header_only, book):
            with self.subTest(source=source.name):
                result = run(IMPORTER, str(source))
                self.assert_single_line_failure(result)
                self.assertNotIn(UNCONFIRMED, result.stdout + result.stderr)

    def test_tracked_input_needs_the_explicit_flag(self) -> None:
        probe = REPO_ROOT / "tests" / "_guard_probe_tiktok.csv"
        shutil.copyfile(self.fixture, probe)
        try:
            blocked = run(IMPORTER, str(probe))
            allowed = run(IMPORTER, str(probe), "--allow-tracked")
        finally:
            probe.unlink(missing_ok=True)

        self.assert_single_line_failure(blocked)
        self.assertIn("--allow-tracked", blocked.stdout + blocked.stderr)
        self.assert_single_line_failure(allowed)
        self.assertIn(UNCONFIRMED, allowed.stdout + allowed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
