from __future__ import annotations

import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMA_PY = ROOT / "skills" / "mmm-ready-schema" / "schema.py"
PYMC_PY = ROOT / ".venvs" / "pymc" / "bin" / "python"

# Runs inside the PyMC-Marketing venv: convert the fixture and instantiate MMM without fitting.
SCRIPT = textwrap.dedent(
    """
    import importlib.util, sys
    import pandas as pd
    from pymc_marketing.mmm import MMM, GeometricAdstock, HillSaturation

    spec = importlib.util.spec_from_file_location("schema", sys.argv[1])
    schema = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema)

    wide = schema.long_to_pymc_wide(pd.read_csv(sys.argv[2]))
    channel_columns = ["spend_search", "spend_social"]
    model = MMM(
        date_column="time",
        channel_columns=channel_columns,
        adstock=GeometricAdstock(l_max=4),
        saturation=HillSaturation(),
        control_columns=["control_price_index"],
    )
    assert model.date_column == "time"
    assert set(channel_columns + ["time", "kpi", "control_price_index"]) <= set(wide.columns)
    print(len(wide), list(wide.columns))
    """
)


@unittest.skipUnless(PYMC_PY.exists(), "pymc venv not installed")
class PymcConversionTests(unittest.TestCase):
    def test_constructs_mmm_without_fitting(self) -> None:
        result = subprocess.run(
            [str(PYMC_PY), "-c", SCRIPT, str(SCHEMA_PY), str(FIXTURES / "tiny_canonical.csv")],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertTrue(result.stdout.strip().splitlines()[-1].startswith("8 ["))


if __name__ == "__main__":
    unittest.main()
