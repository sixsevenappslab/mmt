"""Diagnose data-quality risks of a canonical MMM-ready CSV; informs, never blocks."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("date", "geo", "channel", "spend", "kpi")
MEDIA_ONLY_COLUMNS = ("date", "geo", "channel", "spend")
REPO_ROOT = Path(__file__).resolve().parents[2]
# Weekly series are checked as 7-day steps anchored on the first observed date: exports
# reported on any weekday are regular series, not gaps. The declared anchor is metadata.
FREQUENCIES = {"daily": "D", "weekly-mon": "7D", "weekly-sun": "7D"}
ALWAYS_ON_THRESHOLD = 0.95
LOW_VARIATION_CV = 0.2
MINIMUM_PERIODS = 104
# Diagnostics that need kpi/control_* columns; none exist today, so --media-only omits nothing.
KPI_DEPENDENT_CHECKS: tuple[str, ...] = ()


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
    path = csv_path.with_suffix(".meta.json")
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read metadata sidecar {path.name}: {error}") from error
    if not isinstance(meta, dict) or meta.get("granularity") not in FREQUENCIES:
        raise ValueError("Metadata must contain a recognised granularity.")
    return meta


def _finding(check: str, channel: str, geo: str, detail: str, recommendation: str) -> dict:
    return {
        "check": check,
        "channel": channel,
        "geo": geo,
        "detail": detail,
        "recommendation": recommendation,
    }


def _required_columns(frame: pd.DataFrame, media_only: bool) -> None:
    required = MEDIA_ONLY_COLUMNS if media_only else REQUIRED_COLUMNS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}. Run the validator first."
        )


def diagnose_frame(
    frame: pd.DataFrame, meta: dict, media_only: bool = False
) -> tuple[dict, list[dict]]:
    _required_columns(frame, media_only)
    working = frame.copy()
    working["_date"] = pd.to_datetime(working["date"], errors="coerce")
    if working["_date"].isna().any():
        raise ValueError("Input has unparseable dates. Run the validator first.")
    working["_spend"] = pd.to_numeric(working["spend"], errors="coerce")
    if working["_spend"].isna().any():
        raise ValueError("Input has non-numeric spend values. Run the validator first.")

    findings: list[dict] = []
    frequency = FREQUENCIES[meta["granularity"]]
    for (geo, channel), group in working.groupby(["geo", "channel"], dropna=False):
        label_geo, label_channel = str(geo), str(channel)
        ordered = group.sort_values("_date")
        duplicate_count = int(ordered.duplicated("_date", keep=False).sum())
        if duplicate_count:
            findings.append(
                _finding(
                    "duplicate_dates",
                    label_channel,
                    label_geo,
                    f"{duplicate_count} rows share a date.",
                    "Deduplicate date, geo, channel rows before modelling.",
                )
            )
        unique_dates = ordered["_date"].drop_duplicates().sort_values()
        expected = pd.date_range(unique_dates.iloc[0], unique_dates.iloc[-1], freq=frequency)
        missing_dates = expected.difference(unique_dates)
        if len(missing_dates):
            findings.append(
                _finding(
                    "missing_dates",
                    label_channel,
                    label_geo,
                    f"{len(missing_dates)} expected periods are missing.",
                    "Fill or explicitly account for missing periods before modelling.",
                )
            )
        if len(unique_dates) < MINIMUM_PERIODS:
            findings.append(
                _finding(
                    "short_time_range",
                    label_channel,
                    label_geo,
                    f"Only {len(unique_dates)} periods are available; MMM needs at least {MINIMUM_PERIODS}.",
                    f"Collect at least {MINIMUM_PERIODS} periods or treat estimates as exploratory.",
                )
            )

        positive = ordered["_spend"].gt(0)
        active_share = float(positive.mean())
        mean_spend = float(ordered["_spend"].mean())
        cv = float(ordered["_spend"].std(ddof=0) / mean_spend) if mean_spend > 0 else float("inf")
        if active_share > ALWAYS_ON_THRESHOLD and cv < LOW_VARIATION_CV:
            findings.append(
                _finding(
                    "low_variation",
                    label_channel,
                    label_geo,
                    f"Active in {active_share:.0%} of periods with spend CV {cv:.2f}.",
                    "Create spend variation or use an external calibration experiment.",
                )
            )

        previous = ordered["_spend"].shift()
        ratio = ordered["_spend"] / previous
        jumps = (previous.gt(0) & ((ratio > 10) | (ratio < 0.1))).sum()
        if jumps:
            findings.append(
                _finding(
                    "scale_jump",
                    label_channel,
                    label_geo,
                    f"{int(jumps)} consecutive spend changes exceed 10x.",
                    "Check currency, units, and platform export settings around those dates.",
                )
            )

        if "impressions" in ordered:
            impressions = pd.to_numeric(ordered["impressions"], errors="coerce")
            missing_coverage = impressions.isna()
            if missing_coverage.any():
                findings.append(
                    _finding(
                        "incomplete_impression_coverage",
                        label_channel,
                        label_geo,
                        f"{int(missing_coverage.sum())} rows have missing impressions; they are not zero.",
                        "Recover the missing reporting coverage before using impression diagnostics.",
                    )
                )
            spend_without_impressions = positive & impressions.eq(0)
            impressions_without_spend = ordered["_spend"].eq(0) & impressions.gt(0)
            if spend_without_impressions.any():
                findings.append(
                    _finding(
                        "spend_without_impressions",
                        label_channel,
                        label_geo,
                        f"{int(spend_without_impressions.sum())} rows have spend above zero and zero impressions.",
                        "Check the media metric join or platform reporting definition.",
                    )
                )
            if impressions_without_spend.any():
                findings.append(
                    _finding(
                        "impressions_without_spend",
                        label_channel,
                        label_geo,
                        f"{int(impressions_without_spend.sum())} rows have impressions above zero and zero spend.",
                        "Check currency fields, billing timing, and the media metric join.",
                    )
                )

    required = MEDIA_ONLY_COLUMNS if media_only else REQUIRED_COLUMNS
    return {
        "rows": len(frame),
        "mode": "media-only" if media_only else "full",
        "columns_used": list(required),
        "checks_omitted": list(KPI_DEPENDENT_CHECKS) if media_only else [],
        "granularity": meta["granularity"],
    }, findings


def _print_text(summary: dict, findings: list[dict]) -> None:
    print(f"DIAGNOSIS: {summary['rows']} rows, {len(findings)} findings.")
    for finding in findings:
        print(
            f"{finding['check']} [{finding['geo']}/{finding['channel']}]: "
            f"{finding['detail']} Recommendation: {finding['recommendation']}"
        )


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
        summary, findings = diagnose_frame(frame, meta, args.media_only)
    except ValueError as error:
        if args.json:
            print(json.dumps({"summary": None, "findings": [], "error": str(error)}))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"summary": summary, "findings": findings}))
    else:
        _print_text(summary, findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
