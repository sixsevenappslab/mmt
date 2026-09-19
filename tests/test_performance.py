from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "skills" / "mmm-data-validate" / "validate.py"
DIAGNOSER = ROOT / "skills" / "mmm-data-diagnose" / "diagnose.py"
BUDGET_SECONDS = 5.0


class PerformanceTests(unittest.TestCase):
    def test_validate_and_diagnose_912k_rows_in_under_five_seconds(self) -> None:
        """5 years daily x 50 geos x 10 channels through both CLIs, seeded, in a temp dir."""
        rng = np.random.default_rng(20260907)
        dates = pd.date_range("2019-01-01", periods=1825, freq="D")
        geos = [f"geo_{number:02d}" for number in range(50)]
        channels = [f"channel_{number:02d}" for number in range(10)]
        index = pd.MultiIndex.from_product(
            [dates, geos, channels], names=["date", "geo", "channel"]
        )
        frame = index.to_frame(index=False)
        frame["date"] = frame["date"].dt.strftime("%Y-%m-%d")
        frame["spend"] = rng.uniform(50.0, 150.0, len(frame)).round(2)
        frame["impressions"] = (frame["spend"] * 10).round(0)
        frame["clicks"] = (frame["spend"] / 10).round(0)
        frame["kpi"] = np.repeat(rng.uniform(9_000.0, 11_000.0, 1825 * 50).round(2), 10)
        frame["control_price_index"] = np.repeat(
            1.0 + np.arange(1825 * 50, dtype=float) / 1_000_000, 10
        )
        meta = {
            "schema_version": "1.0",
            "currency": "EUR",
            "granularity": "daily",
            "timezone": "Europe/Madrid",
            "geos": geos,
            "channels": channels,
        }

        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "panel.csv"
            frame.to_csv(csv_path, index=False)
            csv_path.with_suffix(".meta.json").write_text(json.dumps(meta))

            started = time.perf_counter()
            validated = subprocess.run(
                [sys.executable, str(VALIDATOR), "--input", str(csv_path), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            diagnosed = subprocess.run(
                [sys.executable, str(DIAGNOSER), "--input", str(csv_path), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            elapsed = time.perf_counter() - started

        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(validated.stdout)["summary"]["rows"], 912_500)
        self.assertEqual(diagnosed.returncode, 0, diagnosed.stderr)
        self.assertIsInstance(json.loads(diagnosed.stdout)["findings"], list)
        self.assertLess(elapsed, BUDGET_SECONDS, f"CLIs took {elapsed:.2f}s on 912 500 rows")


if __name__ == "__main__":
    unittest.main()
