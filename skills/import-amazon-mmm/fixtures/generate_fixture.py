"""Illustrative Amazon Ads fixture — NOT verified against a real export.

Amazon's MMM data feed schema page is a JavaScript application that served no column list, so
the header below is made up from the little the marketing pages state: dates, a country, spend
and a chosen granularity. It exists only to prove that `import.py` refuses any header while
the contract is unconfirmed. These names are a guess, deliberately kept out of
`expected_headers.json`.

    python3 skills/import-amazon-mmm/fixtures/generate_fixture.py --out /tmp/amazon_fixture.csv
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SKILL_DIR.parent / "_lib"))

import fixtures_common
import mmm_import_common as common

from generators.synthetic_mmm import DEFAULT_CHANNELS, generate

ILLUSTRATIVE_COLUMNS = ["date", "country", "spend", "granularity"]
SOURCE_CHANNEL = "display"


def build(weeks: int, seed: int) -> pd.DataFrame:
    wide, truth = generate(weeks, seed, DEFAULT_CHANNELS)
    with tempfile.TemporaryDirectory() as workdir:
        base = Path(workdir) / "base"
        wide.to_csv(base.with_suffix(".csv"), index=False)
        Path(f"{base}.truth.json").write_text(json.dumps(truth))
        frame = fixtures_common.derive_media_fixture(
            base.with_suffix(".csv"),
            Path(f"{base}.truth.json"),
            fixtures_common.DEFAULT_CPM,
            fixtures_common.DEFAULT_CTR,
            rng_seed=seed,
        )
    frame = frame[frame["channel"] == SOURCE_CHANNEL].reset_index(drop=True)
    daily = fixtures_common.explode_to_daily(frame, rng_seed=seed)
    return pd.DataFrame(
        {
            "date": daily["date"].dt.strftime("%Y-%m-%d"),
            "country": "ES",
            "spend": daily["spend"],
            "granularity": "daily",
        }
    ).loc[:, ILLUSTRATIVE_COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="path of the fixture CSV")
    parser.add_argument("--weeks", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-tracked", action="store_true")
    args = parser.parse_args()

    common.guard_untracked_path(args.out, args.allow_tracked, "salida")
    export = build(args.weeks, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(args.out, index=False)
    print(f"wrote {args.out} ({len(export)} rows, illustrative header, not verified)")


if __name__ == "__main__":
    main()
