from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "generators" / "synthetic_mmm.py"
VALIDATOR = ROOT / "skills" / "mmm-data-validate" / "validate.py"
BASE_CSV_HASH = "832866dabdc0319d8cd95fae27be0a36f0182642ccf88e41f89a8dcfa0e2db01"
BASE_TRUTH_HASH = "93cb20a4f22f0f226f3757526d3cbeed485d0d4e21a38ad33eb38295f4df6414"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SyntheticMmmCanonicalTests(unittest.TestCase):
    def test_existing_output_is_byte_identical_and_canonical_validates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "base"
            baseline = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--weeks",
                    "156",
                    "--seed",
                    "42",
                    "--out",
                    str(output),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(baseline.returncode, 0, baseline.stderr)
            self.assertEqual(sha256(output.with_suffix(".csv")), BASE_CSV_HASH)
            self.assertEqual(sha256(Path(f"{output}.truth.json")), BASE_TRUTH_HASH)

            canonical = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--weeks",
                    "8",
                    "--seed",
                    "42",
                    "--out",
                    str(output),
                    "--canonical",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(canonical.returncode, 0, canonical.stderr)
            canonical_csv = Path(f"{output}.canonical.csv")
            canonical_meta = Path(f"{output}.canonical.meta.json")
            self.assertTrue(canonical_csv.exists())
            self.assertEqual(json.loads(canonical_meta.read_text())["currency"], "EUR")
            validated = subprocess.run(
                [sys.executable, str(VALIDATOR), "--input", str(canonical_csv), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)


if __name__ == "__main__":
    unittest.main()
