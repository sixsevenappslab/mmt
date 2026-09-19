---
name: import-google-mmm
description: Convert a Google MMM Data Platform export (Google Ads or DV360) into canonical MMM-ready media data.
---

# Import a Google MMM Data Platform export

Google's MMM Data Platform delivers two feeds: one for Google Ads campaigns and one for DV360
insertion orders, YouTube included. This importer reads either one and writes the canonical
media table of `mmm-ready-schema` — `date,geo,channel,spend,impressions,clicks` — plus its
`.meta.json` sidecar, then hands the result to `mmm-data-validate --media-only` and exits with
that validator's code.

Format verified on **2026-09-07** against
<https://developers.google.com/meridian/docs/pre-modeling/using-mmm-data-platform>.

## Getting the export

1. Ask your Google account team to enable the MMM Data Platform for the advertiser.
2. Request the feed with the reporting window you need (up to five years) and one time
   granularity: `Daily`, `Weekly-Monday` or `Weekly-Sunday`.
3. Download the delivered file and, if it does not arrive as CSV, re-export it as
   comma-separated UTF-8. XLSX is rejected on purpose (exit code 2).

## Running it

```bash
python3 skills/import-google-mmm/import.py <export>.csv \
  --out /path/outside/the/repo/google_canonical \
  --report /path/outside/the/repo/google_report.json
```

Options: `--currency` (default `EUR`, see below), `--timezone` (default `Europe/Madrid`),
`--allow-tracked` to accept a path inside this repository that git does not ignore.

Leave `--out` off for a dry run: the export is mapped and validated in full and you get the
same exit code, but nothing is written to disk. Useful for answering "does this export match
the contract, and would it produce a valid table?" before choosing where to put it.

```bash
python3 skills/import-google-mmm/import.py <export>.csv
```

## What it maps

| Google Ads column | DV360 column | Canonical |
| --- | --- | --- |
| `ReportDate` | `ReportDate` | `date` |
| `RegionName`, else `CountryName` | `RegionName` | `geo` |
| `Product` | `LineItemType` | `channel` |
| `Cost` | `MediaCost` | `spend` |
| `Impressions` | `Impressions` | `impressions` |
| `Clicks` | `Clicks` | `clicks` |

`channel` comes from a fixed table (`Search` → `search`, `Display` → `display`,
`Video`/`YouTube` → `video`, `Demand Gen` → `demand_gen`, and so on; DV360 `Audio` → `audio`,
`TrueView` → `video`). A value outside the table stops the import — the importer never guesses
a channel by similarity. Every column the mapping does not use is listed in the report under
`ignored_columns`.

## Assumptions and limits

- **Currency.** DV360 carries `CurrencyCode` and the importer reads it. The Google Ads feed
  does not, so the currency comes from `--currency`, defaulting to EUR. `CostUsd` is ignored:
  this importer never converts currency. Two different `CurrencyCode` values in one file stop
  the import.
- **Granularity.** Taken from `TimeGranularity` for Google Ads and inferred from the date
  cadence for DV360. A file mixing granularities stops the import rather than being resampled.
- **No aggregation.** Rows are written one for one. If your export has several dimension
  values per day, channel and geography (device, targeting, creative), several rows collapse
  onto the same `(date, geo, channel)` key and the validator rejects the table. Request the
  export at the dimensionality you want to model, or aggregate it yourself before importing.
- **No business KPI.** The output is media only, as no platform export carries the outcome.

## Fixture

`fixtures/generate_fixture.py` writes a synthetic export with the exact documented header,
derived from `generators/synthetic_mmm.py`. It is not a trimmed real export, and impressions
and clicks come from a stated CPM/CTR assumption, not from any platform's data.

```bash
python3 skills/import-google-mmm/fixtures/generate_fixture.py --out /tmp/google_fixture.csv
```

`--feed dv360`, `--granularity daily|weekly-mon|weekly-sun` and `--expected-out` cover the
other shapes. `fixtures/expected_canonical.csv` is the table the importer must reproduce
byte for byte from the default fixture; `test_import.py` checks exactly that.

## Exit codes

`0` valid canonical output, `1` the output failed schema validation, `2` the input could not
be read or its header does not match the contract in `expected_headers.json`.
