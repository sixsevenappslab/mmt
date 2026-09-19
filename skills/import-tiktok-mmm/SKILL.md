---
name: import-tiktok-mmm
description: Convert a TikTok MMM export into canonical MMM-ready media data — blocked until a real header is supplied.
---

# Import a TikTok MMM export

**Status: no contract.** This importer always exits with code 2 and the message "sin cabecera
confirmada". TikTok publishes no column list for its MMM data. The help articles state only
that the export carries impressions and spend at campaign and DMA level, US only, daily, for
up to four years of paid data (earned data from 2023-07-01). That is not enough to map a
single column, and this repository does not invent column names from third-party blog posts.

Checked on **2026-09-07**:

- <https://ads.tiktok.com/help/article/how-to-pull-media-mix-modeling-mmm-data-in-tiktok-ads-manager>
- <https://ads.tiktok.com/help/article/about-media-mix-modeling-in-tiktok-ads-manager>

## Unblocking it

You need one real export. Nothing else.

1. In TikTok Ads Manager, request the Media Mix Modeling data for your advertiser and
   download it as CSV.
2. Open it and copy **the header row only** — no data rows, no account or campaign
   identifiers.
3. Paste those names into the `columns` array of
   `skills/import-tiktok-mmm/expected_headers.json`, set `"confirmed": true`, and update
   `verified_at` to the date you checked it.
4. Write the mapping in `import.py`: which column is the date, the geography, the channel, the
   spend, the impressions. Follow `skills/import-google-mmm/import.py`, which does the same job
   against a confirmed contract.
5. Add a fixture and an `expected_canonical.csv`, as the Google and Meta importers have.

Please do not paste real spend figures, account identifiers or campaign names anywhere in this
repository. The header row is all that is needed.

## Running it today

```bash
python3 skills/import-tiktok-mmm/import.py <export>.csv
```

It guards the path, reads the file — UTF-8 with or without BOM, comma separated, XLSX
rejected — and then stops at the header contract. `--allow-tracked` works as in every other
importer.

## Fixture

`fixtures/generate_fixture.py` writes a CSV with an **illustrative, unverified** header
(`campaign_id, dma, date, impressions, spend`) built from synthetic data. Its only job is to
show that the importer rejects any header while the contract is unconfirmed. Those names are
deliberately not in `expected_headers.json`.

## Exit codes

`2` always, today: either the input could not be read or the contract is unconfirmed.
