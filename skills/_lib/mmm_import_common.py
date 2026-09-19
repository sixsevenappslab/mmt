"""Shared plumbing for the platform export importers: guards, header contracts, output.

Every importer of FEAT-002 reads one CSV exactly as a platform hands it over and writes the
canonical MMM-ready media table of FEAT-001. The parts that must behave identically across
platforms live here so a change lands once: the git-tracked path guard, CSV reading (UTF-8
with or without BOM), the header contract diff, canonical output plus its metadata sidecar,
the mapping report, daily to weekly resampling, and the call to the FEAT-001 validator.

CLI user-facing messages are Spanish on purpose: the spec fixes two of them literally and QA
greps for them.
"""

from __future__ import annotations

import contextlib
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "skills" / "mmm-data-validate" / "validate.py"
CANONICAL_COLUMNS = ("date", "geo", "channel", "spend", "impressions", "clicks")
GRANULARITIES = ("daily", "weekly-mon", "weekly-sun")
WEEK_START_BY_GRANULARITY = {"weekly-mon": "MON", "weekly-sun": "SUN"}
DAYS_PER_WEEK = 7
EXIT_INPUT_ERROR = 2
UNCONFIRMED_MESSAGE = (
    "Importador de {platform} sin cabecera confirmada. Trae un export real (solo la fila de "
    "cabecera, sin datos), pegala en expected_headers.json, pon confirmed:true y vuelve a "
    "intentar. No hay contrato con el que comparar todavia."
)


class ImportDataError(Exception):
    """A readable failure a CLI turns into a single line and exit code 2."""


def one_line(text: object) -> str:
    """Collapse any message to one line, so a CLI never prints a multi-line error."""
    return " ".join(str(text).split())


def fail(message: str) -> NoReturn:
    """Print exactly one actionable line and exit 2. Never raises a traceback."""
    print(f"ERROR: {one_line(message)}", file=sys.stderr)
    raise SystemExit(EXIT_INPUT_ERROR)


# --- header contracts -------------------------------------------------------------------


def load_expected_headers(skill_dir: Path) -> dict:
    """Read the `expected_headers.json` contract that sits next to an importer."""
    path = Path(skill_dir) / "expected_headers.json"
    try:
        contents = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"No se pudo leer el contrato {path}: {error}")
    if not isinstance(contents, dict):
        fail(f"El contrato {path} debe contener un objeto JSON.")
    return contents


def contract_columns(expected: dict) -> tuple[list[str], list[str]]:
    """Return (required, allowed optional) columns of a contract, in contract order."""
    required = expected.get("required_columns")
    if required is None:
        required = expected.get("columns", [])
    return list(required), list(expected.get("allowed_optional_columns") or [])


def header_diff(actual_columns: list[str], expected: dict) -> tuple[list[str], list[str]]:
    """Compare a header against a contract by set, not by order.

    Returns (missing required columns, columns not in the contract). An empty pair means the
    header matches. This never exits, so callers that probe several contracts can keep going.
    """
    required, optional = contract_columns(expected)
    actual = list(actual_columns)
    missing = [column for column in required if column not in actual]
    unknown = [column for column in actual if column not in required and column not in optional]
    return missing, unknown


def check_header(actual_columns: list[str], expected: dict, platform: str = "la plataforma") -> None:
    """Enforce a header contract: exit 2 with a diff, or return when the header matches."""
    if not expected.get("confirmed", False):
        fail(UNCONFIRMED_MESSAGE.format(platform=platform))
    required, optional = contract_columns(expected)
    missing, unknown = header_diff(actual_columns, expected)
    if missing or unknown:
        fail(
            f"Cabecera de {platform} no reconocida. Requeridas: {required}; "
            f"opcionales permitidas: {optional}; encontradas: {list(actual_columns)}; "
            f"faltan: {missing}; sobran: {unknown}."
        )


# --- path guard -------------------------------------------------------------------------


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


def guard_untracked_path(path: Path, allow_tracked: bool, purpose: str) -> None:
    """Refuse to read or write a repository path git does not ignore, unless allowed.

    Same rule as FEAT-001's validator, applied here to inputs, outputs and reports alike:
    fixtures and user data belong outside the repository or under the ignored `data/` tree.
    """
    resolved = Path(path).expanduser().resolve()
    if allow_tracked or not _inside(resolved, REPO_ROOT):
        return
    if _inside(resolved, REPO_ROOT / "data") or _ignored_by_git(resolved):
        return
    fail(
        f"Ruta de {purpose} versionada dentro del repositorio ({resolved}); "
        "usa --allow-tracked de forma explicita si de verdad la quieres."
    )


# --- reading ----------------------------------------------------------------------------


def read_export_csv(path: Path) -> pd.DataFrame:
    """Read a platform export CSV, UTF-8 with or without BOM, comma separated.

    Raises ImportDataError — never a pandas traceback — for XLSX, an empty file, a
    header-only file, an unreadable encoding or a delimiter that is not a comma.
    """
    resolved = Path(path)
    if resolved.suffix.lower() in (".xlsx", ".xls"):
        raise ImportDataError("XLSX no soportado; exporta como CSV desde la plataforma.")
    try:
        with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
    except UnicodeDecodeError as error:
        raise ImportDataError(
            f"{resolved.name} no esta en UTF-8; vuelve a exportarlo como CSV UTF-8 "
            f"({one_line(error)})."
        ) from error
    except OSError as error:
        raise ImportDataError(f"No se pudo abrir {resolved.name}: {one_line(error)}") from error
    if not sample.strip():
        raise ImportDataError(f"{resolved.name} esta vacio; vuelve a exportarlo con datos.")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error as error:
        raise ImportDataError(
            f"No se reconoce el delimitador de {resolved.name}; exporta un CSV separado por comas."
        ) from error
    if dialect.delimiter != ",":
        raise ImportDataError(
            f"{resolved.name} usa '{dialect.delimiter}' como separador; "
            "exporta un CSV separado por comas."
        )
    try:
        frame = pd.read_csv(resolved, encoding="utf-8-sig", sep=",")
    except (OSError, UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        raise ImportDataError(f"No se pudo leer {resolved.name}: {one_line(error)}") from error
    if frame.empty:
        raise ImportDataError(
            f"{resolved.name} tiene cabecera pero ninguna fila de datos; "
            "vuelve a exportarlo con el rango de fechas correcto."
        )
    return frame


def detect_granularity(dates: pd.Series) -> str:
    """Infer daily / weekly-mon / weekly-sun from the observed date cadence.

    Used by the feeds that do not declare granularity in a column. A cadence that is neither
    a day nor a whole week anchored on one weekday is an error, never a guess.
    """
    unique = pd.Series(pd.to_datetime(dates).unique()).sort_values()
    if len(unique) < 2:
        raise ImportDataError(
            "Hacen falta al menos dos fechas distintas para deducir la granularidad; "
            "vuelve a exportar un rango mas largo."
        )
    steps = unique.diff().dropna().dt.days.unique().tolist()
    if steps == [1]:
        return "daily"
    if steps == [7]:
        weekdays = set(unique.dt.weekday.unique().tolist())
        if weekdays == {0}:
            return "weekly-mon"
        if weekdays == {6}:
            return "weekly-sun"
        raise ImportDataError(
            "Las semanas del export no empiezan todas en lunes ni todas en domingo; "
            "vuelve a pedir el export con un unico ancla semanal."
        )
    raise ImportDataError(
        f"Cadencia de fechas no reconocida (saltos de {sorted(steps)} dias); "
        "vuelve a pedir el export con una sola granularidad, diaria o semanal."
    )


# --- writing ----------------------------------------------------------------------------


def write_canonical(
    df: pd.DataFrame,
    out_prefix: Path,
    currency: str,
    granularity: str,
    timezone: str,
    source_platform: str,
) -> None:
    """Write `<prefix>.csv` in canonical column order plus its `<prefix>.meta.json` sidecar."""
    prefix = Path(out_prefix)
    missing = [column for column in CANONICAL_COLUMNS if column not in df.columns]
    if missing:
        raise ImportDataError(f"Faltan columnas canonicas en la salida: {missing}.")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    df.loc[:, list(CANONICAL_COLUMNS)].to_csv(prefix.with_suffix(".csv"), index=False)
    meta = {
        "schema_version": "1.0",
        "currency": currency,
        "granularity": granularity,
        "timezone": timezone,
        "source_platform": source_platform,
    }
    Path(f"{prefix}.meta.json").write_text(json.dumps(meta, indent=2))


@contextlib.contextmanager
def canonical_output(out_prefix: Path | None):
    """Yield `(prefix, dry_run)`: without `--out` the table is written to a temporary prefix.

    A dry run still maps every row and still runs the validator, so `import.py <export>.csv`
    answers "would this export produce a valid canonical table?" with the same exit code as a
    real run, without leaving anything on disk.
    """
    if out_prefix is not None:
        yield Path(out_prefix), False
        return
    with tempfile.TemporaryDirectory() as workdir:
        yield Path(workdir) / "canonical", True


def write_mapping_report(report: dict, out_path: Path | None) -> None:
    """Write the full mapping report as JSON, or print a readable summary when no path."""
    if out_path is None:
        print(
            f"mapped {len(report.get('column_mapping', {}))} columns, "
            f"ignored {len(report.get('ignored_columns', []))}, "
            f"dropped {len(report.get('dropped_rows', []))} rows, "
            f"currency {report.get('currency_detected')}, "
            f"granularity {report.get('granularity_detected')}."
        )
        if report.get("dry_run"):
            print("dry run: sin --out no se ha escrito ninguna tabla ni sidecar.")
        return
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))


def _as_whole_numbers(values: pd.Series) -> pd.Series:
    """Keep counts looking like counts: cast to nullable int when nothing would be rounded."""
    numeric = pd.to_numeric(values, errors="coerce")
    present = numeric.dropna()
    if present.empty or (present % 1 == 0).all():
        return numeric.astype("Int64")
    return numeric


def _incomplete_reason(row: pd.Series) -> str:
    """Say why one week of one series was dropped, in the terms of what is actually there."""
    days, rows = int(row["days"]), int(row["rows"])
    if rows > days:
        return f"{rows} filas para {days} dias: hay fechas duplicadas en la semana"
    if days < DAYS_PER_WEEK:
        return f"solo {days} de {DAYS_PER_WEEK} dias presentes"
    return f"solo {int(row['spend_days'])} de {DAYS_PER_WEEK} dias con spend legible"


def resample_to_weekly(df: pd.DataFrame, week_start: str = "MON") -> pd.DataFrame:
    """Sum a daily canonical table into whole weeks anchored on `week_start`.

    A week survives only when its `(geo, channel)` series has all seven days present with a
    readable `spend`. That is stricter than trimming the two ends of the file on purpose: a
    platform that simply omits the rows of a day with no activity would otherwise produce a
    weekly total silently short by those days. Anything incomplete is dropped, never imputed,
    and lands in `frame.attrs["dropped_partial_weeks"]` for the mapping report.

    `impressions` and `clicks` are optional, so a week keeps them only when every one of its
    days reports them; a week with some days blank gets an empty total rather than the sum of
    the days that happened to be there.
    """
    anchor = {"MON": 0, "SUN": 6}[week_start.upper()]
    frame = df.copy()
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any():
        raise ImportDataError(
            "Hay fechas ilegibles en la tabla canonica; no se puede re-muestrear a semanal."
        )
    frame["_week"] = dates - pd.to_timedelta((dates.dt.weekday - anchor) % 7, unit="D")
    frame["_date"] = dates
    for column in ("spend", "impressions", "clicks"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    grouped = frame.groupby(["_week", "geo", "channel"], dropna=False)
    weeks = pd.DataFrame(
        {
            "rows": grouped.size(),
            "days": grouped["_date"].nunique(),
            "spend": grouped["spend"].sum(min_count=1),
            "spend_days": grouped["spend"].count(),
            "impressions": grouped["impressions"].sum(min_count=1),
            "impressions_days": grouped["impressions"].count(),
            "clicks": grouped["clicks"].sum(min_count=1),
            "clicks_days": grouped["clicks"].count(),
        }
    ).reset_index()

    full = weeks["days"].eq(DAYS_PER_WEEK)
    unique = weeks["rows"].eq(weeks["days"])
    complete = full & unique & weeks["spend_days"].eq(DAYS_PER_WEEK)
    dropped = [
        {
            "week": row["_week"].strftime("%Y-%m-%d"),
            "geo": row["geo"],
            "channel": row["channel"],
            "days_present": int(row["days"]),
            "reason": _incomplete_reason(row),
        }
        for _, row in weeks[~complete].iterrows()
    ]

    kept = weeks[complete].copy()
    for column in ("impressions", "clicks"):
        kept.loc[kept[f"{column}_days"].ne(DAYS_PER_WEEK), column] = pd.NA
        kept[column] = _as_whole_numbers(kept[column])
    kept["date"] = kept["_week"].dt.strftime("%Y-%m-%d")
    result = kept.loc[:, list(CANONICAL_COLUMNS)].sort_values(["date", "geo", "channel"])
    result = result.reset_index(drop=True)
    result.attrs["dropped_partial_weeks"] = dropped
    return result


def run_schema_validator(csv_path: Path, allow_tracked: bool) -> int:
    """Run the FEAT-001 validator in media-only mode and return its exit code untouched."""
    command = [sys.executable, str(VALIDATOR), "--input", str(csv_path), "--media-only"]
    if allow_tracked:
        command.append("--allow-tracked")
    return subprocess.run(command, check=False).returncode
