"""Convert a canonical MMM-ready CSV to the wide input of Meridian or PyMC-Marketing."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
from schema import long_to_meridian_wide, long_to_pymc_wide, meta_path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _ignored_by_git(path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(path)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def guard_path(path: Path, allow_tracked: bool) -> Path:
    resolved = path.expanduser().resolve()
    data_dir = REPO_ROOT / "data"
    if (
        _inside(resolved, REPO_ROOT)
        and not _inside(resolved, data_dir)
        and not _ignored_by_git(resolved)
    ):
        if not allow_tracked:
            raise ValueError(
                "Refusing a non-ignored path inside this repository; use --allow-tracked explicitly."
            )
    return resolved


def read_csv(path: Path) -> pd.DataFrame:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
        if not sample.strip():
            raise ValueError("Input CSV is empty.")
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error as error:
            raise ValueError("Could not recognise the CSV delimiter.") from error
        if dialect.delimiter != ",":
            raise ValueError("Canonical MMM-ready CSV files must use a comma delimiter.")
        frame = pd.read_csv(path, encoding="utf-8-sig", sep=dialect.delimiter)
    except (OSError, UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        raise ValueError(f"Could not read CSV: {error}") from error
    if frame.empty:
        raise ValueError("Input CSV has a header but no data rows.")
    return frame


def read_meta(csv_path: Path) -> dict:
    path = meta_path(csv_path)
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read metadata sidecar {path.name}: {error}") from error
    if not isinstance(meta, dict):
        raise ValueError(f"Metadata sidecar {path.name} must contain a JSON object.")
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--to", required=True, choices=("meridian", "pymc"))
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-tracked", action="store_true")
    args = parser.parse_args()

    try:
        input_path = guard_path(args.input, args.allow_tracked)
        output_path = guard_path(args.out, args.allow_tracked)
        frame = read_csv(input_path)
        meta = read_meta(input_path)
        converted = (
            long_to_meridian_wide(frame, meta)
            if args.to == "meridian"
            else long_to_pymc_wide(frame, meta)
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        converted.to_csv(output_path, index=False)
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(f"Wrote {output_path} ({len(converted)} rows) for {args.to}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
