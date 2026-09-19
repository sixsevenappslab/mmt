"""Validate a canonical MMM-ready CSV and report every schema error at once."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

REQUIRED_COLUMNS = ("date", "geo", "channel", "spend", "kpi")
MEDIA_ONLY_COLUMNS = ("date", "geo", "channel", "spend")
OPTIONAL_MEDIA_COLUMNS = ("impressions", "clicks")
CONTROL_PREFIX = "control_"
META_REQUIRED_KEYS = ("schema_version", "currency", "granularity", "timezone")
GRANULARITIES = ("daily", "weekly-mon", "weekly-sun")
CHANNEL_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
REPO_ROOT = Path(__file__).resolve().parents[2]
INVARIANCE_CAUSE = (
    "kpi/control inconsistente entre canales de la misma fecha/geo "
    "(must be invariant within each date and geo)"
)


def control_columns(frame: pd.DataFrame) -> list[str]:
    """List the control_* columns of a frame in a stable order."""
    return sorted(column for column in frame.columns if column.startswith(CONTROL_PREFIX))


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
    if (
        _inside(resolved, REPO_ROOT)
        and not _inside(resolved, REPO_ROOT / "data")
        and not _ignored_by_git(resolved)
        and not allow_tracked
    ):
        raise ValueError(
            "Refusing a non-ignored path inside this repository; use --allow-tracked explicitly."
        )
    return resolved


def _meta_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(".meta.json")


def _read_csv(path: Path) -> pd.DataFrame:
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


def _read_meta(csv_path: Path) -> dict:
    path = _meta_path(csv_path)
    try:
        contents = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read metadata sidecar {path.name}: {error}") from error
    if not isinstance(contents, dict):
        raise ValueError(f"Metadata sidecar {path.name} must contain a JSON object.")
    return contents


def _error(row: int | None, column: str, cause: str) -> dict:
    return {"row": row, "column": column, "cause": cause}


def _row_numbers(mask: pd.Series) -> list[int]:
    return (mask[mask].index + 2).tolist()


def _metadata_errors(meta: dict, frame: pd.DataFrame) -> list[dict]:
    errors: list[dict] = []
    for key in META_REQUIRED_KEYS:
        if key not in meta:
            errors.append(_error(None, key, "is required in the metadata sidecar"))
    if meta.get("schema_version") != "1.0":
        errors.append(_error(None, "schema_version", "must be '1.0'"))
    currency = meta.get("currency")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        errors.append(_error(None, "currency", "must be a three-letter ISO-4217 code"))
    if meta.get("granularity") not in GRANULARITIES:
        errors.append(_error(None, "granularity", f"must be one of {', '.join(GRANULARITIES)}"))
    timezone = meta.get("timezone")
    if not isinstance(timezone, str):
        errors.append(_error(None, "timezone", "must be an IANA timezone"))
    else:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            errors.append(_error(None, "timezone", "must be an IANA timezone"))
    for key in ("geos", "channels"):
        if key in meta and not isinstance(meta[key], list):
            errors.append(_error(None, key, "must be a JSON array when present"))
    if isinstance(meta.get("geos"), list) and "geo" in frame:
        if sorted(map(str, meta["geos"])) != sorted(frame["geo"].dropna().astype(str).unique()):
            errors.append(_error(None, "geos", "does not match the geos in the CSV"))
    if isinstance(meta.get("channels"), list) and "channel" in frame:
        if sorted(map(str, meta["channels"])) != sorted(
            frame["channel"].dropna().astype(str).unique()
        ):
            errors.append(_error(None, "channels", "does not match the channels in the CSV"))
    return errors


def validate_frame(
    frame: pd.DataFrame, meta: dict, media_only: bool = False
) -> tuple[dict | None, list[dict]]:
    errors = _metadata_errors(meta, frame)
    required = MEDIA_ONLY_COLUMNS if media_only else REQUIRED_COLUMNS
    missing = [column for column in required if column not in frame.columns]
    errors.extend(_error(None, column, "required column is missing") for column in missing)

    parsed_dates: pd.Series | None = None
    if "date" in frame:
        text_dates = frame["date"].astype("string")
        parsed_dates = pd.to_datetime(text_dates, errors="coerce")
        invalid = parsed_dates.isna() | ~text_dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
        errors.extend(_error(row, "date", "must use YYYY-MM-DD") for row in _row_numbers(invalid))
    if "geo" in frame:
        invalid = frame["geo"].isna() | frame["geo"].astype("string").str.strip().eq("")
        errors.extend(
            _error(row, "geo", "must be a non-empty string") for row in _row_numbers(invalid)
        )
    if "channel" in frame:
        channels = frame["channel"].astype("string")
        invalid = channels.isna() | ~channels.str.fullmatch(CHANNEL_PATTERN.pattern, na=False)
        errors.extend(
            _error(
                row,
                "channel",
                "must start with a lowercase letter and use lowercase letters, digits, or underscores",
            )
            for row in _row_numbers(invalid)
        )

    for column in ("spend", *OPTIONAL_MEDIA_COLUMNS):
        if column not in frame:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid = values.lt(0) | (values.isna() & frame[column].notna())
        if column == "spend":
            invalid = invalid | values.isna()
        errors.extend(
            _error(row, column, "must be a non-negative number") for row in _row_numbers(invalid)
        )

    numeric_columns = [] if media_only else ["kpi", *control_columns(frame)]
    for column in numeric_columns:
        if column not in frame:
            continue
        invalid = pd.to_numeric(frame[column], errors="coerce").isna()
        errors.extend(_error(row, column, "must be a number") for row in _row_numbers(invalid))

    key_columns = [column for column in ("date", "geo", "channel") if column in frame]
    if len(key_columns) == 3:
        duplicate = frame.duplicated(key_columns, keep="first")
        errors.extend(
            _error(row, "date,geo,channel", "duplicates an earlier primary key")
            for row in _row_numbers(duplicate)
        )

    group_columns = [column for column in ("date", "geo") if column in frame]
    invariant_columns = []
    if not media_only:
        invariant_columns = ["kpi", *control_columns(frame)]
    if len(group_columns) == 2:
        for column in invariant_columns:
            if column not in frame:
                continue
            conflicting = (
                frame.groupby(group_columns, dropna=False)[column]
                .transform("nunique", dropna=False)
                .gt(1)
            )
            errors.extend(
                _error(row, column, INVARIANCE_CAUSE)
                for row in _row_numbers(conflicting)
            )

    if errors:
        return None, errors
    assert parsed_dates is not None
    omitted = ["kpi_invariance", "control_invariance"] if media_only else []
    return {
        "rows": len(frame),
        "date_range": [
            parsed_dates.min().strftime("%Y-%m-%d"),
            parsed_dates.max().strftime("%Y-%m-%d"),
        ],
        "geos": sorted(frame["geo"].astype(str).unique().tolist()),
        "channels": sorted(frame["channel"].astype(str).unique().tolist()),
        "currency": meta["currency"],
        "granularity": meta["granularity"],
        "timezone": meta["timezone"],
        "mode": "media-only" if media_only else "full",
        "columns_used": list(required),
        "checks_omitted": omitted,
    }, []


def _print_text(summary: dict | None, errors: list[dict]) -> None:
    if summary:
        print(
            f"VALID: {summary['rows']} rows, {summary['date_range'][0]} to "
            f"{summary['date_range'][1]}, {len(summary['geos'])} geos, "
            f"{len(summary['channels'])} channels, {summary['currency']}."
        )
        return
    for error in errors:
        prefix = f"row {error['row']}, " if error["row"] is not None else ""
        print(f"ERROR: {prefix}{error['column']}: {error['cause']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--media-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-tracked", action="store_true")
    args = parser.parse_args()

    try:
        path = guard_path(args.input, args.allow_tracked)
        frame = _read_csv(path)
        meta = _read_meta(path)
    except ValueError as error:
        errors = [_error(None, "input", str(error))]
        if args.json:
            print(json.dumps({"ok": False, "summary": None, "errors": errors}))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    summary, errors = validate_frame(frame, meta, args.media_only)
    if args.json:
        print(json.dumps({"ok": not errors, "summary": summary, "errors": errors}))
    else:
        _print_text(summary, errors)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
