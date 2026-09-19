"""Import a whole folder of platform exports into one canonical media table.

Each file is matched against every *confirmed* header contract under `skills/import-*-mmm/`,
handed to the importer that owns it, and the results are concatenated. A file nobody claims —
wrong extension, unreadable, or a header no confirmed contract matches — is reported as
skipped and the batch carries on. Exit code 0 means at least one file made it; 2 means none
did, or the folder mixes currencies or week anchors that cannot be reconciled without
rewriting somebody's data.

Alignment is deliberately one-way: daily tables are summed up to a weekly anchor that is
already present in the folder, never the other way round, and two different weekly anchors
stop the run instead of being shifted.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[1]
sys.path.insert(0, str(SKILL_DIR.parent / "_lib"))

import mmm_import_common as common

IMPORTER_GLOB = "import-*-mmm"


def confirmed_contracts() -> list[tuple[Path, str, dict]]:
    """Every (importer directory, feed label, contract) that is marked confirmed."""
    found = []
    for skill_dir in sorted((REPO_ROOT / "skills").glob(IMPORTER_GLOB)):
        contract_path = skill_dir / "expected_headers.json"
        if not contract_path.exists():
            continue
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        feeds = contract.get("feeds")
        if feeds:
            for feed, expected in feeds.items():
                if expected.get("confirmed"):
                    found.append((skill_dir, f"{skill_dir.name}:{feed}", expected))
        elif contract.get("confirmed"):
            found.append((skill_dir, skill_dir.name, contract))
    return found


def match_contract(columns: list[str], contracts: list[tuple[Path, str, dict]]) -> tuple | None:
    for skill_dir, label, expected in contracts:
        missing, unknown = common.header_diff(columns, expected)
        if not missing and not unknown:
            return skill_dir, label
    return None


def delegate(
    skill_dir: Path, source: Path, out_prefix: Path, report_path: Path, allow_tracked: bool
) -> tuple[int, str]:
    command = [
        sys.executable,
        str(skill_dir / "import.py"),
        str(source),
        "--out",
        str(out_prefix),
        "--report",
        str(report_path),
    ]
    if allow_tracked:
        command.append("--allow-tracked")
    result = subprocess.run(command, text=True, capture_output=True, check=False, cwd=REPO_ROOT)
    return result.returncode, common.one_line(result.stdout + result.stderr)


def collect(directory: Path, workdir: Path, allow_tracked: bool) -> tuple[list[dict], list[dict]]:
    """Import what can be imported; return (per-file report entries, imported pieces)."""
    contracts = confirmed_contracts()
    tried = [label for _, label, _ in contracts]
    entries: list[dict] = []
    imported: list[dict] = []

    for index, path in enumerate(sorted(p for p in directory.iterdir() if p.is_file())):
        entry = {"path": str(path), "status": "skipped", "reason": None}
        if path.suffix.lower() != ".csv":
            entry["reason"] = f"extension {path.suffix or '(ninguna)'} no soportada; solo CSV."
            entries.append(entry)
            continue
        try:
            frame = common.read_export_csv(path)
        except common.ImportDataError as error:
            entry["reason"] = str(error)
            entries.append(entry)
            continue

        match = match_contract(list(frame.columns), contracts)
        if match is None:
            entry["reason"] = (
                f"ningun contrato confirmado coincide. Probados: {tried}. Revisa los "
                "contratos sin confirmar (Meta, TikTok, Amazon): puede que sea uno de ellos "
                "y haga falta pegar su cabecera real en expected_headers.json."
            )
            entries.append(entry)
            continue

        skill_dir, label = match
        out_prefix = workdir / f"piece_{index}"
        piece_report = workdir / f"piece_{index}.report.json"
        code, output = delegate(skill_dir, path, out_prefix, piece_report, allow_tracked)
        if code != 0:
            entry["reason"] = f"{label} termino con codigo {code}: {output}"
            entries.append(entry)
            continue

        piece = {
            "path": str(path),
            "importer": label,
            "frame": pd.read_csv(out_prefix.with_suffix(".csv")),
            "meta": json.loads(Path(f"{out_prefix}.meta.json").read_text()),
            "report": json.loads(piece_report.read_text()),
        }
        entry.update({"status": "imported", "importer": label, "reason": None})
        entry["currency"] = piece["meta"]["currency"]
        entry["granularity"] = piece["meta"]["granularity"]
        entry["report"] = piece["report"]
        entries.append(entry)
        imported.append(piece)
    return entries, imported


def align(imported: list[dict]) -> tuple[pd.DataFrame, str, list[dict]]:
    """Bring every piece to one granularity, or stop. Returns (table, granularity, notes)."""
    granularities = {piece["meta"]["granularity"] for piece in imported}
    weekly = sorted(g for g in granularities if g.startswith("weekly-"))
    if len(weekly) > 1:
        by_anchor = "; ".join(
            f"{piece['path']} -> {piece['meta']['granularity']}"
            for piece in imported
            if piece["meta"]["granularity"] in weekly
        )
        raise common.ImportDataError(
            f"La carpeta mezcla anclas semanales ({weekly}): {by_anchor}. Vuelve a pedir esos "
            "exports con una sola ancla (todo lunes o todo domingo). No se desplazan semanas "
            "por tu cuenta."
        )

    notes: list[dict] = []
    if not weekly:
        return pd.concat([piece["frame"] for piece in imported], ignore_index=True), "daily", notes

    target = weekly[0]
    week_start = common.WEEK_START_BY_GRANULARITY[target]
    pieces = []
    for piece in imported:
        if piece["meta"]["granularity"] == "daily":
            resampled = common.resample_to_weekly(piece["frame"], week_start)
            notes.append(
                {
                    "path": piece["path"],
                    "resampled_from": "daily",
                    "resampled_to": target,
                    "dropped_partial_weeks": resampled.attrs.get("dropped_partial_weeks", []),
                }
            )
            pieces.append(resampled)
        else:
            pieces.append(piece["frame"])
    return pd.concat(pieces, ignore_index=True), target, notes


def single_value(imported: list[dict], key: str, what: str, advice: str) -> str:
    values = sorted({piece["meta"][key] for piece in imported})
    if len(values) > 1:
        detail = "; ".join(f"{piece['path']} -> {piece['meta'][key]}" for piece in imported)
        raise common.ImportDataError(f"La carpeta mezcla {what} ({values}): {detail}. {advice}")
    return values[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="folder of platform export CSVs")
    parser.add_argument("--out", type=Path, required=True, help="output prefix for .csv/.meta.json")
    parser.add_argument("--report", type=Path, default=None, help="path of the JSON report")
    parser.add_argument("--allow-tracked", action="store_true")
    args = parser.parse_args()

    common.guard_untracked_path(args.directory, args.allow_tracked, "entrada")
    common.guard_untracked_path(args.out, args.allow_tracked, "salida")
    if args.report is not None:
        common.guard_untracked_path(args.report, args.allow_tracked, "informe")
    if not args.directory.is_dir():
        common.fail(f"{args.directory} no es un directorio.")

    with tempfile.TemporaryDirectory() as tmp:
        entries, imported = collect(args.directory, Path(tmp), args.allow_tracked)
        report = {
            "input_directory": str(args.directory),
            "files": entries,
            "imported_count": len(imported),
            "skipped_count": sum(1 for entry in entries if entry["status"] == "skipped"),
        }
        if not imported:
            report.update(
                {
                    "column_mapping": {},
                    "ignored_columns": [],
                    "dropped_rows": [],
                    "currency_detected": None,
                    "granularity_detected": None,
                    "resampling": [],
                }
            )
            common.write_mapping_report(report, args.report)
            print(
                "ERROR: ningun fichero de la carpeta pudo importarse; "
                "revisa el informe para el motivo de cada uno.",
                file=sys.stderr,
            )
            return common.EXIT_INPUT_ERROR

        try:
            currency = single_value(
                imported,
                "currency",
                "monedas",
                "Vuelve a pedir cada export en una sola moneda. Este importador nunca convierte "
                "divisas.",
            )
            timezone = single_value(
                imported,
                "timezone",
                "zonas horarias",
                "Vuelve a importar cada fichero con la misma.",
            )
            table, granularity, resampling = align(imported)
        except common.ImportDataError as error:
            # The report is the point of this skill: write it before refusing to align.
            report.update(
                {
                    "column_mapping": {},
                    "ignored_columns": [],
                    "dropped_rows": [],
                    "currency_detected": None,
                    "granularity_detected": None,
                    "resampling": [],
                    "aborted_because": common.one_line(error),
                }
            )
            common.write_mapping_report(report, args.report)
            common.fail(str(error))
        table = table.sort_values(["date", "geo", "channel"]).reset_index(drop=True)

        common.write_canonical(
            table,
            args.out,
            currency,
            granularity,
            timezone,
            ",".join(sorted({piece["meta"]["source_platform"] for piece in imported})),
        )
        merged_mapping: dict[str, str] = {}
        ignored: set[str] = set()
        dropped: list = []
        for piece in imported:
            merged_mapping.update(piece["report"].get("column_mapping", {}))
            ignored.update(piece["report"].get("ignored_columns", []))
            dropped.extend(piece["report"].get("dropped_rows", []))
        report.update(
            {
                "column_mapping": merged_mapping,
                "ignored_columns": sorted(ignored),
                "dropped_rows": dropped,
                "currency_detected": currency,
                "granularity_detected": granularity,
                "resampling": resampling,
                "rows_out": len(table),
            }
        )
        common.write_mapping_report(report, args.report)
        return common.run_schema_validator(
            Path(args.out).with_suffix(".csv"), args.allow_tracked
        )


if __name__ == "__main__":
    raise SystemExit(main())
