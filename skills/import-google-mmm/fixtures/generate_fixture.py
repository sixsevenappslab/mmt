"""Build a synthetic Google MMM Data Platform export, plus the canonical table it must yield.

The fixture has the exact header of the documented feed and entirely synthetic values: it is
derived from `generators/synthetic_mmm.py`, never from a real export. Currency is EUR and the
account, campaign and geography labels are made up.

The expected canonical table is built here from the same long frame the export is rendered
from, so it does not travel through the importer's own mapping code — that is what makes the
comparison in `test_import.py` worth running.

    python3 skills/import-google-mmm/fixtures/generate_fixture.py --out /tmp/google_fixture.csv
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

GOOGLE_ADS_COLUMNS = [
    "GroupName",
    "ReportDate",
    "TimeGranularity",
    "Product",
    "CountryCriteriaId",
    "CountryName",
    "RegionCriteriaId",
    "RegionName",
    "MetroCriteriaId",
    "MetroName",
    "Device",
    "Targeting",
    "Impressions",
    "Clicks",
    "CostUsd",
    "Cost",
]
DV360_COLUMNS = [
    "AdvertiserName",
    "AdvertiserId",
    "CurrencyCode",
    "CampaignName",
    "CampaignId",
    "InsertionOrderName",
    "LineItemName",
    "LineItemId",
    "LineItemType",
    "CreativeType",
    "DeviceType",
    "RegionName",
    "ReportDate",
    "Impressions",
    "Clicks",
    "MediaCost",
]
# Google Ads has no "social" product; Demand Gen is the closest documented equivalent.
PRODUCT_BY_CHANNEL = {
    "search": "Search",
    "social": "Demand Gen",
    "video": "Video",
    "display": "Display",
}
CANONICAL_BY_PRODUCT = {
    "Search": "search",
    "Demand Gen": "demand_gen",
    "Video": "video",
    "Display": "display",
}
# DV360 sells no search inventory, so only three synthetic channels map onto it.
LINE_ITEM_TYPE_BY_CHANNEL = {"search": "Display", "social": "Video", "video": "Audio"}
CANONICAL_BY_LINE_ITEM_TYPE = {"Display": "display", "Video": "video", "Audio": "audio"}
GRANULARITY_LABEL = {
    "daily": "Daily",
    "weekly-mon": "Weekly-Monday",
    "weekly-sun": "Weekly-Sunday",
}
DEFAULT_GEO = "Spain"
USD_PER_EUR = 1.08  # illustrative constant, only to fill the CostUsd column of the fixture


def build_media_frame(weeks: int, seed: int, granularity: str) -> pd.DataFrame:
    """Long `date, channel, spend, impressions, clicks` at the requested granularity."""
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
    if granularity == "daily":
        frame = fixtures_common.explode_to_daily(frame, rng_seed=seed)
    elif granularity == "weekly-sun":
        frame = fixtures_common.shift_to_sunday_weeks(frame)
    return frame


def to_google_ads(frame: pd.DataFrame, granularity: str, geo: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "GroupName": "mmt-synthetic",
            "ReportDate": frame["date"].dt.strftime("%Y-%m-%d"),
            "TimeGranularity": GRANULARITY_LABEL[granularity],
            "Product": frame["channel"].map(PRODUCT_BY_CHANNEL),
            "CountryCriteriaId": 2724,
            "CountryName": geo,
            "RegionCriteriaId": "",
            "RegionName": "",
            "MetroCriteriaId": "",
            "MetroName": "",
            "Device": "ALL",
            "Targeting": "ALL",
            "Impressions": frame["impressions"],
            "Clicks": frame["clicks"],
            "CostUsd": (frame["spend"] * USD_PER_EUR).round(2),
            "Cost": frame["spend"],
        }
    ).loc[:, GOOGLE_ADS_COLUMNS]


def to_dv360(frame: pd.DataFrame, currency: str, geo: str) -> pd.DataFrame:
    selected = frame[frame["channel"].isin(LINE_ITEM_TYPE_BY_CHANNEL)].reset_index(drop=True)
    return pd.DataFrame(
        {
            "AdvertiserName": "MMT Synthetic Advertiser",
            "AdvertiserId": "SYNTHETIC-ADVERTISER",
            "CurrencyCode": currency,
            "CampaignName": "MMT Synthetic Campaign",
            "CampaignId": "SYNTHETIC-CAMPAIGN",
            "InsertionOrderName": "MMT Synthetic IO",
            "LineItemName": "MMT Synthetic Line Item",
            "LineItemId": "SYNTHETIC-LINE-ITEM",
            "LineItemType": selected["channel"].map(LINE_ITEM_TYPE_BY_CHANNEL),
            "CreativeType": "Standard",
            "DeviceType": "ALL",
            "RegionName": geo,
            "ReportDate": selected["date"].dt.strftime("%Y-%m-%d"),
            "Impressions": selected["impressions"],
            "Clicks": selected["clicks"],
            "MediaCost": selected["spend"],
        }
    ).loc[:, DV360_COLUMNS]


def to_expected_canonical(frame: pd.DataFrame, feed: str, geo: str) -> pd.DataFrame:
    if feed == "google_ads":
        channel = frame["channel"].map(PRODUCT_BY_CHANNEL).map(CANONICAL_BY_PRODUCT)
        selected = frame
    else:
        selected = frame[frame["channel"].isin(LINE_ITEM_TYPE_BY_CHANNEL)].reset_index(drop=True)
        channel = selected["channel"].map(LINE_ITEM_TYPE_BY_CHANNEL).map(
            CANONICAL_BY_LINE_ITEM_TYPE
        )
    return pd.DataFrame(
        {
            "date": selected["date"].dt.strftime("%Y-%m-%d"),
            "geo": geo,
            "channel": channel,
            "spend": selected["spend"],
            "impressions": selected["impressions"],
            "clicks": selected["clicks"],
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="path of the fixture CSV")
    parser.add_argument("--feed", choices=("google_ads", "dv360"), default="google_ads")
    parser.add_argument("--granularity", choices=common.GRANULARITIES, default="weekly-mon")
    parser.add_argument("--weeks", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--currency", default="EUR", help="CurrencyCode written by the DV360 feed")
    parser.add_argument(
        "--geo",
        default=DEFAULT_GEO,
        help="geography written into the export, so two fixtures can share a folder",
    )
    parser.add_argument(
        "--expected-out",
        type=Path,
        default=None,
        help="also write the canonical table the importer must reproduce",
    )
    parser.add_argument("--allow-tracked", action="store_true")
    args = parser.parse_args()

    common.guard_untracked_path(args.out, args.allow_tracked, "salida")
    if args.expected_out is not None:
        common.guard_untracked_path(args.expected_out, args.allow_tracked, "canonico esperado")

    frame = build_media_frame(args.weeks, args.seed, args.granularity)
    export = (
        to_google_ads(frame, args.granularity, args.geo)
        if args.feed == "google_ads"
        else to_dv360(frame, args.currency, args.geo)
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(args.out, index=False)
    print(f"wrote {args.out} ({len(export)} rows, feed {args.feed}, {args.granularity})")

    if args.expected_out is not None:
        expected = to_expected_canonical(frame, args.feed, args.geo)
        args.expected_out.parent.mkdir(parents=True, exist_ok=True)
        expected.to_csv(args.expected_out, index=False)
        print(f"wrote {args.expected_out} ({len(expected)} rows)")


if __name__ == "__main__":
    main()
