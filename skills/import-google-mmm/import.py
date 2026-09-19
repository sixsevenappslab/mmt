"""Import a Google MMM Data Platform export (Google Ads or DV360 feed) into canonical form.

Both feeds arrive as one row per reporting dimension combination. This importer maps columns
by name, never by position, and refuses anything it cannot map from a fixed table: a product
or line item type that is not in the table is an error, not a guess. Rows are written as they
come — no deduplication, no aggregation, no currency conversion — so the FEAT-001 validator is
the one that judges the result, and its exit code is the one this CLI returns.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR.parent / "_lib"))

import mmm_import_common as common

SOURCE_PLATFORM = {"google_ads": "google-ads-mmm", "dv360": "dv360-mmm"}
GRANULARITY_BY_LABEL = {
    "daily": "daily",
    "weekly-monday": "weekly-mon",
    "weekly-sunday": "weekly-sun",
}
CHANNEL_BY_PRODUCT = {
    "Search": "search",
    "Shopping": "shopping",
    "Display": "display",
    "Video": "video",
    "YouTube": "video",
    "Demand Gen": "demand_gen",
    "Discovery": "discovery",
    "Performance Max": "performance_max",
    "App": "app",
    "Local": "local",
}
CHANNEL_BY_LINE_ITEM_TYPE = {
    "Display": "display",
    "Video": "video",
    "Audio": "audio",
    "TrueView": "video",
}
COLUMN_MAPPING = {
    "google_ads": {
        "ReportDate": "date",
        "RegionName": "geo",
        "CountryName": "geo",
        "Product": "channel",
        "Cost": "spend",
        "Impressions": "impressions",
        "Clicks": "clicks",
    },
    "dv360": {
        "ReportDate": "date",
        "RegionName": "geo",
        "LineItemType": "channel",
        "MediaCost": "spend",
        "Impressions": "impressions",
        "Clicks": "clicks",
    },
}


def detect_feed(columns: list[str], contract: dict) -> str:
    """Return the feed whose header contract matches, or exit 2 listing both diffs."""
    diffs = {}
    for feed, expected in contract["feeds"].items():
        missing, unknown = common.header_diff(columns, expected)
        if not missing and not unknown:
            return feed
        diffs[feed] = (missing, unknown)
    detail = "; ".join(
        f"{feed} espera {common.contract_columns(contract['feeds'][feed])[0]} "
        f"(faltan {missing}, sobran {unknown})"
        for feed, (missing, unknown) in diffs.items()
    )
    common.fail(
        f"Cabecera de Google no reconocida. Encontradas: {columns}. Contratos probados -> {detail}."
    )


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].astype("string").fillna("").str.strip()


def _map_channel(values: pd.Series, table: dict[str, str], source_column: str) -> pd.Series:
    unknown = sorted({value for value in values.unique() if value not in table})
    if unknown:
        common.fail(
            f"Valores de {source_column} sin equivalente en la tabla de canales: {unknown}. "
            f"Conocidos: {sorted(table)}. No se adivina el canal."
        )
    return values.map(table)


def _resolve_geo(frame: pd.DataFrame, feed: str) -> pd.Series:
    """Take the most specific non-empty geography the feed reports."""
    region = _series(frame, "RegionName")
    if feed == "dv360":
        geo = region
    else:
        geo = region.where(region != "", _series(frame, "CountryName"))
    if (geo == "").any():
        rows = [index + 2 for index in geo[geo == ""].index.tolist()]
        common.fail(f"Filas sin ninguna geografia (RegionName/CountryName vacios): {rows[:10]}.")
    return geo


def _resolve_granularity(frame: pd.DataFrame, feed: str) -> str:
    if feed != "google_ads":
        return common.detect_granularity(frame["ReportDate"])
    labels = sorted(_series(frame, "TimeGranularity").str.lower().unique().tolist())
    if len(labels) > 1:
        raise common.ImportDataError(
            f"El fichero mezcla granularidades ({labels}); vuelve a pedir el export con una "
            "sola granularidad (Daily, Weekly-Monday o Weekly-Sunday). No se re-muestrea solo."
        )
    if labels[0] not in GRANULARITY_BY_LABEL:
        raise common.ImportDataError(
            f"TimeGranularity desconocida ('{labels[0]}'); se esperaba Daily, Weekly-Monday o "
            "Weekly-Sunday."
        )
    return GRANULARITY_BY_LABEL[labels[0]]


def _resolve_currency(frame: pd.DataFrame, feed: str, fallback: str) -> str:
    if "CurrencyCode" not in frame.columns:
        return fallback
    currencies = sorted(code for code in _series(frame, "CurrencyCode").unique() if code)
    if len(currencies) > 1:
        raise common.ImportDataError(
            f"El fichero mezcla monedas ({currencies}); vuelve a pedir el export filtrado a una "
            "sola moneda. Este importador nunca convierte divisas."
        )
    return currencies[0] if currencies else fallback


def build_canonical(frame: pd.DataFrame, feed: str) -> pd.DataFrame:
    """Map one platform frame to the canonical columns, row for row and in input order."""
    dates = pd.to_datetime(frame["ReportDate"], errors="coerce")
    if dates.isna().any():
        rows = [index + 2 for index in dates[dates.isna()].index.tolist()]
        common.fail(f"Fechas ilegibles en ReportDate, filas {rows[:10]}; se esperaba YYYY-MM-DD.")
    if feed == "google_ads":
        channel = _map_channel(_series(frame, "Product"), CHANNEL_BY_PRODUCT, "Product")
        spend_column = "Cost"
    else:
        channel = _map_channel(
            _series(frame, "LineItemType"), CHANNEL_BY_LINE_ITEM_TYPE, "LineItemType"
        )
        spend_column = "MediaCost"
    return pd.DataFrame(
        {
            "date": dates.dt.strftime("%Y-%m-%d"),
            "geo": _resolve_geo(frame, feed),
            "channel": channel,
            "spend": frame[spend_column],
            "impressions": frame["Impressions"],
            "clicks": frame["Clicks"],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="export CSV exactly as Google delivers it")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output prefix for .csv/.meta.json; omit for a dry run that writes nothing",
    )
    parser.add_argument("--report", type=Path, default=None, help="path of the JSON mapping report")
    parser.add_argument(
        "--currency",
        default="EUR",
        help="currency of the Google Ads feed, which carries no CurrencyCode column",
    )
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
    feed = detect_feed(list(frame.columns), contract)
    common.check_header(list(frame.columns), contract["feeds"][feed], f"Google ({feed})")

    try:
        granularity = _resolve_granularity(frame, feed)
        currency = _resolve_currency(frame, feed, args.currency)
        canonical = build_canonical(frame, feed)
    except common.ImportDataError as error:
        common.fail(str(error))

    mapping = {
        source: target
        for source, target in COLUMN_MAPPING[feed].items()
        if source in frame.columns
    }
    with common.canonical_output(args.out) as (out_prefix, dry_run):
        common.write_canonical(
            canonical, out_prefix, currency, granularity, args.timezone, SOURCE_PLATFORM[feed]
        )
        common.write_mapping_report(
            {
                "source_platform": SOURCE_PLATFORM[feed],
                "feed_detected": feed,
                "input_file": str(args.input_csv),
                "dry_run": dry_run,
                "column_mapping": mapping,
                "ignored_columns": [c for c in frame.columns if c not in mapping],
                "dropped_rows": [],
                "currency_detected": currency,
                "granularity_detected": granularity,
                "rows_in": len(frame),
                "rows_out": len(canonical),
            },
            args.report,
        )
        return common.run_schema_validator(
            out_prefix.with_suffix(".csv"), args.allow_tracked
        )


if __name__ == "__main__":
    raise SystemExit(main())
