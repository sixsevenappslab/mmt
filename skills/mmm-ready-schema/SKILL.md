---
name: mmm-ready-schema
description: Convert canonical MMM-ready marketing data to Meridian or PyMC-Marketing wide tables.
---

# MMM-ready schema

Use this skill when a canonical long MMM CSV must be converted before modelling. Read
`SCHEMA.md` before mapping a source dataset.

```bash
python3 skills/mmm-ready-schema/convert.py \
  --input /path/to/mmm-ready.csv --to meridian --out /path/to/meridian.csv
```

The output is wide: `time`, `kpi`, `control_*`, one `spend_<channel>` per channel and, for
Meridian, `impressions_<channel>` when available. Use `--to pymc` only for a single-geo dataset. Multi-geo data is supported by the Meridian
conversion and rejected explicitly for PyMC-Marketing. Files inside this repository that are
not ignored by git require `--allow-tracked`; ordinary user files outside the repository do not.

The script uses only pandas and the Python standard library. It does not import Meridian,
PyMC-Marketing, TensorFlow, or PyMC.
