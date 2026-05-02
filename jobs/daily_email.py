"""Daily email: read listings, find new + price-drop rows, send digest.

`new` = first_seen_at is today (UTC).
`price drops` = id present yesterday with higher monthly_rent_gbp.

For v1 we only flag `new` rigorously; price-drop detection is left as an
empty placeholder until we keep a per-day snapshot. Email goes out only
if there's something to report.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from svansokning import constants, filters, notify, storage  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("daily_email")


def main() -> int:
    df = storage.read_listings()
    if df.empty:
        log.info("no listings yet — nothing to email")
        return 0

    today = datetime.now(timezone.utc).date()
    df = df.copy()
    df["first_seen_date"] = pd.to_datetime(df["first_seen_at"]).dt.date
    new_today = df[df["first_seen_date"] == today]

    new_today = filters.apply_criteria(new_today, constants.DEFAULT_CRITERIA)
    drops = pd.DataFrame()  # placeholder — see module docstring

    if new_today.empty and drops.empty:
        log.info("nothing to send today")
        return 0
    notify.send_digest(new_today, drops)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
