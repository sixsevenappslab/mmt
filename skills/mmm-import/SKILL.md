---
name: mmm-import
description: Import a folder of platform MMM exports into one canonical MMM-ready media table.
---

# Import a folder of platform exports

"Here is the folder I downloaded my exports into — give me one table I can model." That is
what this does. It recognises each file by its header, hands it to the importer that owns that
platform, and concatenates the results into a single canonical media table with one metadata
sidecar.

```bash
python3 skills/mmm-import/detect_and_import.py /path/to/exports \
  --out /path/outside/the/repo/all_media \
  --report /path/outside/the/repo/import_report.json
```

## What happens to each file

| Situation | Result |
| --- | --- |
| Header matches a confirmed contract | Imported by that platform's skill |
| Not a `.csv` | Skipped, reason in the report |
| Empty, header-only, not UTF-8, not comma separated | Skipped, reason in the report |
| Header matches no confirmed contract | Skipped, with the contracts tried |
| Importer ran and failed | Skipped, with its exit code and message |

The batch never aborts on one bad file. It exits `0` when at least one file was imported and
`2` when none was — and in both cases the report lists every file with its verdict.

Only Google has a confirmed contract today. Meta, TikTok and Amazon files will therefore land
in the skipped list; see their `SKILL.md` for how to close their contracts.

## Alignment, and what it refuses to do

- **Currency.** Every file must declare the same one. Two currencies stop the run with exit 2
  and an explanation. Nothing is ever converted.
- **Granularity.** Daily tables are summed into whole weeks when the folder also holds weekly
  data, using the anchor that is already there. Partial weeks at either end are dropped, not
  imputed, and the report says which. Weekly data is never broken down into days.
- **Week anchors.** A folder holding both Monday-anchored and Sunday-anchored weeks stops with
  exit 2. Shifting one to the other would move somebody's data by a day; re-export instead.
- **Duplicates.** Rows are concatenated as they come. If two files describe the same
  `(date, geo, channel)`, the FEAT-001 validator rejects the union — deliberately, because
  silently summing or dropping one of them would be a modelling decision this tool does not
  get to make.

## Output

`<prefix>.csv` in canonical column order, `<prefix>.meta.json` with the agreed currency,
granularity and timezone, and a report with the per-file verdicts, the merged column mapping,
the ignored columns and every resampling applied. The final table is validated with
`mmm-data-validate --media-only`, and this skill exits with that validator's code.

`--allow-tracked` is needed for any path inside this repository that git does not ignore, and
it is passed through to each importer.

The report is written even when the run refuses to align — mixed currencies, mixed week
anchors — with the per-file currency and granularity that caused it and an `aborted_because`
line. Being able to see which file brought which anchor is the whole point of reading it.

## Exit codes

`0` at least one file imported and the union validated, `1` the union failed schema
validation, `2` nothing could be imported or the folder mixes currencies or week anchors.
