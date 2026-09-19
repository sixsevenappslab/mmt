---
name: import-amazon-mmm
description: Convert an Amazon Ads MMM data feed into canonical MMM-ready media data — blocked until a real header is supplied.
---

# Import an Amazon Ads MMM data feed

**Status: no contract.** This importer always exits with code 2 and the message "sin cabecera
confirmada". Amazon documents the feed as a product — free, delivered through a manager
account or Amazon S3, daily or weekly grain, available in fourteen countries, up to ten
business days to arrive — but not as a schema. The API page that should carry the column table
is a JavaScript application that served no content to the tools available on 2026-09-07, so
there is no published header to map against.

Checked on **2026-09-07**:

- <https://advertising.amazon.com/en-gb/measurement-analytics/marketing-mix-models>
- <https://advertising.amazon.com/resources/whats-new/marketing-mix-modeling-supports-daily-grain-metrics-requests>

## Unblocking it

1. Request the MMM data feed for your advertiser through your Amazon Ads manager account or
   the S3 delivery, choosing daily or weekly grain and CSV.
2. Open the delivered file and copy **the header row only** — no data rows, no account or
   campaign identifiers.
3. Paste those names into the `columns` array of
   `skills/import-amazon-mmm/expected_headers.json`, set `"confirmed": true`, and update
   `verified_at`.
4. Write the mapping in `import.py`, following `skills/import-google-mmm/import.py`, which
   does the same job against a confirmed contract.
5. Add a fixture and an `expected_canonical.csv`, as the Google and Meta importers have.

Please do not paste real spend figures, account identifiers or campaign names anywhere in this
repository. The header row is all that is needed.

## Running it today

```bash
python3 skills/import-amazon-mmm/import.py <export>.csv
```

It guards the path, reads the file — UTF-8 with or without BOM, comma separated, XLSX
rejected — and then stops at the header contract. `--allow-tracked` works as in every other
importer.

## Fixture

`fixtures/generate_fixture.py` writes a CSV with an **illustrative, unverified** header
(`date, country, spend, granularity`) built from synthetic data, purely to show that the
importer rejects any header while the contract is unconfirmed. Those names are deliberately
not in `expected_headers.json`.

## Exit codes

`2` always, today: either the input could not be read or the contract is unconfirmed.
