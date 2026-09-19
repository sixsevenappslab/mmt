---
name: mmm-data-validate
description: Validate a canonical MMM-ready CSV and report every schema issue before modelling.
---

# Validate MMM-ready data

Run this before a MMM conversion or model fit. The input CSV needs its adjacent
`<name>.meta.json` sidecar.

```bash
python3 skills/mmm-data-validate/validate.py --input /path/to/mmm-ready.csv --json
```

For a media-platform export that does not yet include business KPI or controls, use
`--media-only`. The JSON output has `ok`, `summary`, and row/column/cause `errors`. Exit code
`0` means valid, `1` means schema errors, and `2` means the input or metadata could not be read.

Files inside this repository that are not ignored by git require `--allow-tracked` explicitly.
