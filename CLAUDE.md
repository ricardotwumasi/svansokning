# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: svansökning

A personal rental-search dashboard for Oxford, UK. Aggregates rental listings from public UK property portals, filters them against editable criteria, ranks by distance to two fixed Oxford reference points, and emails a daily digest. A future "buy" section is planned but out of scope for v1.

This is a single-user tool. Optimise for clarity and operational simplicity over generality (no auth, no multi-tenancy, no scaling beyond one user's listings).

## Stack

- **Language/runtime:** Python 3.11+
- **UI:** Streamlit
- **Storage:** Parquet for the listings table, JSON for small config/state files. No relational database. Read/write through a single `storage.py` module so callers never touch file paths directly.
- **Geocoding:** [postcodes.io](https://postcodes.io) — free, UK-only, no API key. Cache geocode results to disk; postcodes don't move.
- **Distance:** Haversine straight-line distance from a listing's postcode centroid to each reference point. Don't add a routing API (Mapbox/Google) unless explicitly asked — straight-line is good enough for v1.
- **Email:** [Resend](https://resend.com) for the daily digest. API key in `RESEND_API_KEY`.
- **Hosting:** Streamlit Community Cloud for the dashboard. GitHub Actions cron for the daily scrape + email job. Parquet state lives in object storage (Cloudflare R2 free tier, or committed to a private data branch — decide when implementing). Avoid anything that requires a paid tier.

## Reference points (hard-coded constants)

These are domain constants, not config — put them in one module and import.

| Name | Postcode | Approx lat/lon |
|------|----------|----------------|
| Oxford station | OX1 1HS | 51.7536, -1.2701 |
| Andrew Wiles Building (Maths Inst.) | OX2 6GG | 51.7600, -1.2630 |
| Jericho centre (default search anchor) | — | ~51.7585, -1.2670 |

Resolve the lat/lon at startup via postcodes.io and cache; don't trust hand-typed coordinates as the source of truth.

## Default criteria (UI-editable)

All of these must be editable in the Streamlit sidebar; the values below are defaults, not constraints:

- Search anchor: Jericho centre
- Max radius from anchor: 3 km
- Bedrooms: 1–3 (inclusive range)
- Max monthly rent: £2200
- Plus the usual qualitative filters as they become relevant (furnished, available-from, let-agreed visibility, pets)

Persist the user's last-used criteria to a JSON file so the dashboard reopens with their settings, not the defaults.

## Listing sources

UK rental portals don't expose free public APIs. Expected sources are Rightmove, Zoopla, OnTheMarket, OpenRent, SpareRoom. Each scraper lives behind a common interface that returns a normalised listing record; the rest of the pipeline doesn't know which source a listing came from.

Operational rules for any scraper added here:
- Respect `robots.txt` and use conservative rate limits (sleep between requests; one full pass per day is plenty).
- Identify with a real `User-Agent` that includes a contact email.
- Cache raw HTML responses to disk so reruns during development don't re-hit the source.
- Never parallelise requests against the same host.

If a source becomes hostile (Cloudflare challenges, IP blocks), drop it rather than escalating to headless browsers or proxies — this is a personal tool, not a data product.

## Data model

One canonical listing record, written to Parquet. Required fields:

- `id` (stable per source — usually source + their listing id)
- `source`, `url`, `first_seen_at`, `last_seen_at`
- `postcode`, `lat`, `lon`
- `bedrooms`, `monthly_rent_gbp`
- `dist_station_km`, `dist_andrew_wiles_km`, `dist_anchor_km`
- `title`, `address`, `available_from`, `furnished`, `let_agreed`
- `raw` (JSON blob of source-specific fields, for debugging)

`first_seen_at` is what the daily digest filters on — "new since yesterday's run". Don't delete listings that disappear from a source; mark them via `last_seen_at` going stale so we keep history.

## Pipeline shape

Three stages, runnable independently:

1. **Scrape** — fetch listings from each source, write to a per-source raw Parquet.
2. **Enrich** — geocode postcodes, compute distances, normalise into the canonical schema, merge with prior state on `id` (preserving `first_seen_at`).
3. **Notify** — diff against yesterday's snapshot, send Resend email of new + meaningfully-changed listings (price drops).

The Streamlit app reads only the enriched Parquet — it doesn't trigger scrapes. Keep the dashboard read-only against state produced by the cron job.

## Secrets

- `RESEND_API_KEY` — Resend API
- Any per-source auth (none expected for v1)

Local: `.env` (gitignored). CI: GitHub Actions secrets. Never read from `os.environ` outside a single `config.py` module.

## Out of scope for v1 (don't build until asked)

- Buy/purchase listings (planned, separate section)
- Multi-user accounts / auth
- Map-based UI (start with a sortable table)
- Routing-API-based commute times
- Mobile app or push notifications beyond email

## Open decisions

These haven't been settled yet — flag them when you hit them rather than picking silently:

- Where exactly the Parquet state lives between cron runs (R2 vs. private repo branch vs. Streamlit Cloud's ephemeral disk + re-fetch). Trade-off is cost vs. complexity.
- Whether to commit the geocode cache to git (small, useful) or keep it ephemeral.
