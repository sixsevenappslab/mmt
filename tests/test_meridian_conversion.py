from __future__ import annotations

import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMA_PY = ROOT / "skills" / "mmm-ready-schema" / "schema.py"
MERIDIAN_PY = ROOT / ".venvs" / "meridian" / "bin" / "python"

# Runs inside the Meridian venv: convert the fixture and build InputData without sampling.
SCRIPT = textwrap.dedent(
    """
    import importlib.util, sys
    import pandas as pd
    from meridian.data import data_frame_input_data_builder as builder

    spec = importlib.util.spec_from_file_location("schema", sys.argv[1])
    schema = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema)

    wide = schema.long_to_meridian_wide(pd.read_csv(sys.argv[2]))
    channels = ["search", "social"]
    spend_cols = [f"spend_{c}" for c in channels]
    impressions_cols = [f"impressions_{c}" for c in channels]
    data_builder = (
        builder.DataFrameInputDataBuilder(kpi_type="revenue", default_time_column="time")
        .with_kpi(wide, kpi_col="kpi")
        .with_media(
            wide,
            media_cols=impressions_cols,
            media_spend_cols=spend_cols,
            media_channels=channels,
        )
        .with_controls(wide, control_cols=["control_price_index"])
    )
    if "geo" in wide:
        wide["population"] = wide["geo"].map({"north": 1_000_000, "south": 800_000})
        data_builder.with_population(wide, population_col="population")
    input_data = data_builder.build()
    n_geos = wide["geo"].nunique() if "geo" in wide else 1
    assert input_data.kpi.sizes["time"] == len(wide) // n_geos, input_data.kpi.sizes
    print("geo" in wide, input_data.kpi.sizes["time"])
    """
)


@unittest.skipUnless(MERIDIAN_PY.exists(), "meridian venv not installed")
class MeridianConversionTests(unittest.TestCase):
    def test_builder_accepts_national_and_multi_geo_wide_data(self) -> None:
        for filename, expected in (
            ("tiny_canonical.csv", "False 8"),
            ("tiny_canonical_2geo.csv", "True 4"),
        ):
            with self.subTest(filename=filename):
                result = subprocess.run(
                    [str(MERIDIAN_PY), "-c", SCRIPT, str(SCHEMA_PY), str(FIXTURES / filename)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                self.assertEqual(result.stdout.strip().splitlines()[-1], expected)


if __name__ == "__main__":
    unittest.main()
