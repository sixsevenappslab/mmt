"""Canonical MMM-ready long schema and pure pandas converters to wide model inputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("date", "geo", "channel", "spend", "kpi")
OPTIONAL_MEDIA_COLUMNS = ("impressions", "clicks")
CONTROL_PREFIX = "control_"
META_REQUIRED_KEYS = ("schema_version", "currency", "granularity", "timezone")
GRANULARITIES = ("daily", "weekly-mon", "weekly-sun")
SPEND_PREFIX = "spend_"
IMPRESSIONS_PREFIX = "impressions_"


def meta_path(csv_path: Path) -> Path:
    """Return the metadata sidecar path adjacent to a canonical CSV."""
    return csv_path.with_suffix(".meta.json")


def control_columns(frame: pd.DataFrame) -> list[str]:
    """List the control_* columns of a long frame in a stable order."""
    return sorted(column for column in frame.columns if column.startswith(CONTROL_PREFIX))


def _require_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def _pivot(working: pd.DataFrame, index: list[str], value: str, prefix: str) -> pd.DataFrame:
    wide = working.pivot(index=index, columns="channel", values=value)
    wide.columns = [f"{prefix}{channel}" for channel in wide.columns]
    return wide.reset_index()


def _wide_base(
    frame: pd.DataFrame, include_geo: bool, include_impressions: bool
) -> pd.DataFrame:
    """Pivot the long table to one row per time (and geo) with one column per channel."""
    _require_columns(frame)
    working = frame.copy()
    working["time"] = pd.to_datetime(working["date"], errors="raise").dt.strftime("%Y-%m-%d")
    controls = control_columns(working)
    index = ["time", "geo"]

    result = working[index + ["kpi", *controls]].drop_duplicates(subset=index)
    result = result.merge(_pivot(working, index, "spend", SPEND_PREFIX), on=index, how="inner")
    if include_impressions and "impressions" in working and working["impressions"].notna().any():
        impressions = _pivot(working, index, "impressions", IMPRESSIONS_PREFIX)
        impressions = impressions.dropna(axis="columns", how="all")
        result = result.merge(impressions, on=index, how="left")

    if not include_geo:
        result = result.drop(columns="geo")
    sort_keys = ["time", "geo"] if include_geo else ["time"]
    return result.sort_values(sort_keys).reset_index(drop=True)


def long_to_meridian_wide(frame: pd.DataFrame, meta: dict | None = None) -> pd.DataFrame:
    """Wide table for Meridian: time, geo if >1 geo, kpi, controls, spend_* and impressions_*.

    `meta` is accepted for signature parity with the spec; the pivot needs no metadata today.
    """
    geos = frame["geo"].dropna().astype(str).unique()
    return _wide_base(frame, include_geo=len(geos) > 1, include_impressions=True)


def long_to_pymc_wide(frame: pd.DataFrame, meta: dict | None = None) -> pd.DataFrame:
    """Wide table for PyMC-Marketing: time, kpi, controls and spend_*; single geo only."""
    _require_columns(frame)
    geos = frame["geo"].dropna().astype(str).unique()
    if len(geos) > 1:
        raise ValueError(
            "PyMC-Marketing conversion supports one geo only: multi-geo needs model dims, "
            "out of scope here. Use Meridian for multi-geo data or wait for a future FEAT."
        )
    return _wide_base(frame, include_geo=False, include_impressions=False)
