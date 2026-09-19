"""Import an Amazon Ads MMM data feed into canonical form — no header contract exists yet.

Amazon delivers the feed through a manager account or S3, daily or weekly, across fourteen
countries, but the schema page is a JavaScript application that served no column list to the
tools available when this was written. There is nothing to map against, so this importer is a
deliberate stub: it reads and guards its input like every other importer and then stops with
exit code 2, rather than pretending to work on invented column names.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR.parent / "_lib"))

import mmm_import_common as common

PLATFORM = "Amazon Ads"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="export CSV exactly as Amazon delivers it")
    parser.add_argument("--out", type=Path, default=None, help="output prefix, once a contract exists")
    parser.add_argument("--report", type=Path, default=None, help="path of the JSON mapping report")
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
    common.check_header(list(frame.columns), contract, PLATFORM)
    # Unreachable while the contract is unconfirmed: check_header always exits 2 above.
    common.fail(f"Importador de {PLATFORM} sin logica de mapeo todavia.")


if __name__ == "__main__":
    raise SystemExit(main())
