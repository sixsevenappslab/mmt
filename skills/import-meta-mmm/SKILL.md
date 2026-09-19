---
name: import-meta-mmm
description: Convert a Meta MMM data export into canonical MMM-ready media data — header contract not confirmed yet.
---

# Import a Meta MMM data export

**Status: unconfirmed.** This importer refuses to run by default and exits with code 2. Meta
documents the columns of the Marketing API's `marketing-mix-modeling` breakdown, but nothing
public describes what the Ads Reporting UI export actually writes — it may use readable labels
such as `Amount spent (EUR)` instead of `spend`. Until somebody pastes a real header into
`expected_headers.json` and sets `confirmed: true`, running this on a real export would be
guessing.

Candidate columns verified on **2026-09-07** against
<https://developers.facebook.com/docs/marketing-api/insights/marketing-mix-modeling/>.

## Closing the contract

1. Pull the export you actually use (see below) and open it.
2. Copy its header row — the column names only, no data — into the `columns` array of
   `skills/import-meta-mmm/expected_headers.json`.
3. Set `"confirmed": true`, update `verified_at`, and re-run. If the real names differ from
   the candidates, the mapping table in `import.py` needs updating in the same change.

## Getting the export

Two routes, and only the first is documented at column level:

- **Marketing API.** Request the `marketing-mix-modeling` Insights breakdown with
  `time_increment=1` for daily rows. It returns the fourteen columns this contract lists.
- **Ads Reporting UI.** Ads Manager › Reporting exports the MMM dataset for up to 37 months.
  Choose CSV; XLSX is rejected with exit code 2. The header of this route is what is not
  confirmed.

## Running it

```bash
python3 skills/import-meta-mmm/import.py <export>.csv \
  --out /path/outside/the/repo/meta_canonical \
  --report /path/outside/the/repo/meta_report.json \
  --trust-unconfirmed
```

`--trust-unconfirmed` runs the mapping against the candidate contract anyway. It exists for
the fixture test; do not reach for it on a real export and then treat the result as verified.
Other options: `--channel-by <column>`, `--currency` (default `EUR`), `--timezone` (default
`Europe/Madrid`), `--allow-tracked`.

Leave `--out` off for a dry run: same mapping, same validation, same exit code, nothing
written to disk.

## What it maps

| Meta column | Canonical |
| --- | --- |
| `date_start` | `date` |
| `dma`, else `region`, else `country` | `geo` |
| *(none)* | `channel`, fixed to `meta` |
| `spend` | `spend` |
| `impressions` | `impressions` |

`date_stop` is read only to reject a row covering more than one period; re-export with
`time_increment=1` if that happens.

## Assumptions and limits

- **No channel column.** The documented breakdown has no campaign-level channel, so every row
  becomes the single channel `meta`. `--channel-by <column>` overrides that with a column of
  your export — a known limit, not a mapping.
- **No clicks.** The documented columns carry impressions and spend only, so `clicks` is
  empty in the output.
- **No currency column.** `--currency` declares it; the importer never converts.
- **Granularity** is inferred from the date cadence, and a cadence that is neither daily nor a
  single weekly anchor is an error.
- **No business KPI.** Media only, like every importer here.

## Fixture

```bash
python3 skills/import-meta-mmm/fixtures/generate_fixture.py --out /tmp/meta_fixture.csv
```

Synthetic throughout, derived from `generators/synthetic_mmm.py`; the identifiers are
placeholders and impressions come from a stated CPM/CTR assumption. `test_import.py` checks
both that `--trust-unconfirmed` reproduces `fixtures/expected_canonical.csv` and that the
default run stops with "sin cabecera confirmada".

## Exit codes

`0` valid canonical output, `1` the output failed schema validation, `2` the contract is not
confirmed, the input could not be read, or the header does not match.
