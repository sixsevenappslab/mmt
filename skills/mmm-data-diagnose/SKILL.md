---
name: mmm-data-diagnose
description: Diagnose time-series and media-quality risks in canonical MMM-ready data.
---

# Diagnose MMM-ready data

Use this after validation to identify data conditions that make a marketing-mix model weak or
misleading.

```bash
python3 skills/mmm-data-diagnose/diagnose.py --input /path/to/mmm-ready.csv --json
```

The diagnosis checks missing and duplicate periods, media metric mismatches, incomplete
impression coverage, scale jumps, low spend variation, and short histories. Findings never make
the command fail: a readable input returns exit code `0` with recommendations. Use
`--media-only` for a platform export that has no KPI or controls; the summary then reports
`mode`, `columns_used` and `checks_omitted` (empty today: no diagnostic depends on KPI). Exit code `2` is reserved for
an unreadable input or metadata sidecar.

Files inside this repository that are not ignored by git require `--allow-tracked` explicitly.
