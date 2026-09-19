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
SCRIPT = ROOT / "skills" / "mmm-data-validate" / "validate.py"


def run_validate(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments], text=True, capture_output=True, check=False
    )


class DataValidateTests(unittest.TestCase):
    def test_valid_fixture_returns_summary_json(self) -> None:
        result = run_validate(
            "--input", str(FIXTURES / "tiny_canonical.csv"), "--allow-tracked", "--json"
        )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["rows"], 16)
        self.assertEqual(payload["summary"]["currency"], "EUR")
        self.assertEqual(payload["errors"], [])

    def test_accumulates_schema_errors(self) -> None:
        cases = {
            "broken_duplicate.csv": "duplicates an earlier primary key",
            "broken_inconsistent_kpi.csv": "must be invariant",
            "broken_negative_spend.csv": "must be a non-negative number",
            "tiny_canonical_broken.csv": "duplicates an earlier primary key",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                result = run_validate(
                    "--input", str(FIXTURES / filename), "--allow-tracked", "--json"
                )
                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse(payload["ok"])
                self.assertTrue(any(expected in error["cause"] for error in payload["errors"]))

    def test_media_only_omits_kpi_and_controls(self) -> None:
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
            result = run_validate("--input", str(path), "--media-only", "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["summary"]["mode"], "media-only")
        self.assertEqual(
            payload["summary"]["checks_omitted"], ["kpi_invariance", "control_invariance"]
        )

    def test_tracked_input_and_unreadable_input_return_clean_exit_two(self) -> None:
        guarded = run_validate("--input", str(FIXTURES / "tiny_canonical.csv"))
        self.assertEqual(guarded.returncode, 2)
        self.assertIn("--allow-tracked", guarded.stderr)

        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "empty.csv"
            empty.write_text("")
            unreadable = run_validate("--input", str(empty))
        self.assertEqual(unreadable.returncode, 2)
        self.assertNotIn("Traceback", unreadable.stderr)
        self.assertEqual(len(unreadable.stderr.splitlines()), 1)

    def test_bom_is_accepted_and_wrong_delimiter_is_cleanly_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bom = Path(directory) / "bom.csv"
            bom.write_bytes(b"\xef\xbb\xbf" + (FIXTURES / "tiny_canonical.csv").read_bytes())
            bom.with_suffix(".meta.json").write_text(
                (FIXTURES / "tiny_canonical.meta.json").read_text()
            )
            accepted = run_validate("--input", str(bom), "--json")

            semicolon = Path(directory) / "semicolon.csv"
            semicolon.write_text((FIXTURES / "tiny_canonical.csv").read_text().replace(",", ";"))
            semicolon.with_suffix(".meta.json").write_text(
                (FIXTURES / "tiny_canonical.meta.json").read_text()
            )
            rejected = run_validate("--input", str(semicolon))

        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(len(rejected.stderr.splitlines()), 1)


    def test_metadata_and_encoding_edge_cases(self) -> None:
        """Edge cases 4 and 10-13 of the spec: encoding, missing and invalid metadata."""
        valid_meta = json.loads((FIXTURES / "tiny_canonical.meta.json").read_text())
        invalid_meta = {
            "currency": ("EURO", "ISO-4217"),
            "granularity": ("monthly", "must be one of"),
            "timezone": ("Europe/Notreal", "IANA"),
        }
        with tempfile.TemporaryDirectory() as directory:
            latin = Path(directory) / "latin.csv"
            latin.write_bytes("date,geo,channel,spend,kpi\n2024-01-01,Espa\u00f1a,search,1,1\n".encode("latin-1"))
            latin.with_suffix(".meta.json").write_text(json.dumps(valid_meta))
            encoding = run_validate("--input", str(latin))
            self.assertEqual(encoding.returncode, 2)
            self.assertEqual(len(encoding.stderr.splitlines()), 1)
            self.assertNotIn("Traceback", encoding.stderr)

            no_meta = Path(directory) / "no_meta.csv"
            no_meta.write_text((FIXTURES / "tiny_canonical.csv").read_text())
            missing = run_validate("--input", str(no_meta))
            self.assertEqual(missing.returncode, 2)
            self.assertEqual(len(missing.stderr.splitlines()), 1)
            self.assertNotIn("Traceback", missing.stderr)

            for key, (value, expected) in invalid_meta.items():
                with self.subTest(key=key):
                    path = Path(directory) / f"bad_{key}.csv"
                    path.write_text((FIXTURES / "tiny_canonical.csv").read_text())
                    path.with_suffix(".meta.json").write_text(
                        json.dumps({**valid_meta, key: value})
                    )
                    result = run_validate("--input", str(path), "--json")
                    payload = json.loads(result.stdout)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual([error["column"] for error in payload["errors"]], [key])
                    self.assertIn(expected, payload["errors"][0]["cause"])


if __name__ == "__main__":
    unittest.main()
