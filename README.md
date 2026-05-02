# svansökning

Personal rental-search dashboard for Oxford, UK. Scrapes listings, filters by editable criteria, ranks by distance to Oxford station and the Andrew Wiles Building, and emails a daily digest.

See [CLAUDE.md](CLAUDE.md) for the architecture.

## Quick start

```bash
uv sync
uv run pytest
uv run streamlit run app/streamlit_app.py
```

## Daily pipeline (local)

```bash
uv run python jobs/daily_scrape.py
uv run python jobs/daily_email.py
```

In production this runs on GitHub Actions cron (`.github/workflows/daily.yml`). The scrape commits the updated Parquet to `main`; Streamlit Community Cloud auto-redeploys on push.
