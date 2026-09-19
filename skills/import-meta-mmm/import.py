"""Import a Meta MMM data export into canonical form — header contract NOT confirmed.

Meta documents fourteen columns for the Marketing API's marketing-mix-modeling breakdown, but
nothing published describes what the Ads Reporting UI export actually writes; it may well use
readable labels such as "Amount spent (EUR)". So `expected_headers.json` is marked
`confirmed: false` and this importer refuses to run by default, exactly like the TikTok and
Amazon stubs. `--trust-unconfirmed` runs the mapping anyway against the candidate contract:
the fixture test uses it, and nobody should use it on a real export believing it is confirmed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR.parent / "_lib"))

import mmm_import_common as common

SOURCE_PLATFORM = "meta-mmm"
DEFAULT_CHANNEL = "meta"
GEO_COLUMNS = ("dma", "region", "country")  # most specific first
COLUMN_MAPPING = {
    "date_start": "date",
    "country": "geo",
    "region": "geo",
    "dma": "geo",
    "spend": "spend",
    "impressions": "impressions",
}


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].astype("string").fillna("").str.strip()


def _resolve_geo(frame: pd.DataFrame) -> pd.Series:
    """Most specific non-empty of dma, region, country."""
    geo = pd.Series("", index=frame.index, dtype="string")
    for column in reversed(GEO_COLUMNS):
        values = _series(frame, column)
        geo = values.where(values != "", geo)
    if (geo == "").any():
        rows = [index + 2 for index in geo[geo == ""].index.tolist()]
        common.fail(f"Filas sin ninguna geografia (dma/region/country vacios): {rows[:10]}.")
    return geo


def build_canonical(frame: pd.DataFrame, channel_by: str | None) -> pd.DataFrame:
    dates = pd.to_datetime(frame["date_start"], errors="coerce")
    stops = pd.to_datetime(frame["date_stop"], errors="coerce")
    if dates.isna().any():
        rows = [index + 2 for index in dates[dates.isna()].index.tolist()]
        common.fail(f"Fechas ilegibles en date_start, filas {rows[:10]}; se esperaba YYYY-MM-DD.")
    if stops.isna().any():
        rows = [index + 2 for index in stops[stops.isna()].index.tolist()]
        common.fail(
            f"Filas con date_stop vacio o ilegible: {rows[:10]}; se esperaba YYYY-MM-DD en "
            "cada fila, igual que date_start."
        )
    multi_period = dates.ne(stops)
    if multi_period.any():
        rows = [index + 2 for index in multi_period[multi_period].index.tolist()]
        common.fail(
            f"Filas que cubren mas de un periodo (date_start != date_stop): {rows[:10]}; "
            "vuelve a exportar con time_increment=1."
        )
    if channel_by is None:
        channel = pd.Series(DEFAULT_CHANNEL, index=frame.index, dtype="string")
    else:
        if channel_by not in frame.columns:
            common.fail(
                f"--channel-by {channel_by} no existe en el fichero; "
                f"columnas disponibles: {list(frame.columns)}."
            )
        channel = _series(frame, channel_by).str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True)
    return pd.DataFrame(
        {
            "date": dates.dt.strftime("%Y-%m-%d"),
            "geo": _resolve_geo(frame),
            "channel": channel,
            "spend": frame["spend"],
            "impressions": frame["impressions"],
            "clicks": pd.NA,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="export CSV exactly as Meta delivers it")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output prefix for .csv/.meta.json; omit for a dry run that writes nothing",
    )
    parser.add_argument("--report", type=Path, default=None, help="path of the JSON mapping report")
    parser.add_argument(
        "--trust-unconfirmed",
        action="store_true",
        help="run the mapping against the unconfirmed candidate contract (fixture tests only)",
    )
    parser.add_argument(
        "--channel-by",
        default=None,
        help="column to read the channel from; by default every row is the single channel 'meta'",
    )
    parser.add_argument("--currency", default="EUR", help="currency of the export, not reported")
    parser.add_argument("--timezone", default="Europe/Madrid", help="IANA timezone of the export")
    parser.add_argument("--allow-tracked", action="store_true")
    args = parser.parse_args()

    common.guard_untracked_path(args.input_csv, args.allow_tracked, "entrada")
    if args.out is not None:
        common.guard_untracked_path(args.out, args.allow_tracked, "salida")
    if args.report is not None:
        common.guard_untracked_path(args.report, args.allow_tracked, "informe")

    try:
        frame = common.read_export_csv(args.input_csv)
    except common.ImportDataError as error:
        common.fail(str(error))

    contract = common.load_expected_headers(SKILL_DIR)
    if args.trust_unconfirmed:
        contract = {**contract, "confirmed": True}
    common.check_header(list(frame.columns), contract, "Meta")

    try:
        granularity = common.detect_granularity(frame["date_start"])
    except common.ImportDataError as error:
        common.fail(str(error))
    canonical = build_canonical(frame, args.channel_by)

    mapping = {
        source: target for source, target in COLUMN_MAPPING.items() if source in frame.columns
    }
    with common.canonical_output(args.out) as (out_prefix, dry_run):
        common.write_canonical(
            canonical, out_prefix, args.currency, granularity, args.timezone, SOURCE_PLATFORM
        )
        common.write_mapping_report(
            {
                "source_platform": SOURCE_PLATFORM,
                "header_contract_confirmed": False,
                "input_file": str(args.input_csv),
                "dry_run": dry_run,
                "column_mapping": mapping,
                "columns_checked_not_mapped": ["date_stop"],
                "ignored_columns": [
                    c for c in frame.columns if c not in mapping and c != "date_stop"
                ],
                "dropped_rows": [],
                "currency_detected": args.currency,
                "granularity_detected": granularity,
                "rows_in": len(frame),
                "rows_out": len(canonical),
            },
            args.report,
        )
        return common.run_schema_validator(out_prefix.with_suffix(".csv"), args.allow_tracked)


if __name__ == "__main__":
    raise SystemExit(main())
