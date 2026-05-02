"""Daily scrape: run all enabled scrapers, enrich, write Parquet.

Idempotent: re-running on the same day updates last_seen_at for re-seen listings
without duplicating them.
"""

import logging
import sys
from pathlib import Path

# allow running as `python jobs/daily_scrape.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from svansokning import enrich, storage  # noqa: E402
from svansokning.scrape.openrent import OpenRentScraper  # noqa: E402
from svansokning.scrape.zoopla import ZooplaScraper  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("daily_scrape")


def main() -> int:
    scrapers = [OpenRentScraper(), ZooplaScraper()]
    all_listings = []
    for s in scrapers:
        try:
            results = s.fetch()
            log.info("%s: %d listings", s.name, len(results))
            all_listings.extend(results)
        except Exception:
            log.exception("%s: scraper failed", s.name)

    df = enrich.enrich(all_listings)
    storage.write_listings(df)
    log.info("wrote %d total rows to %s", len(df), storage.config.LISTINGS_PARQUET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
