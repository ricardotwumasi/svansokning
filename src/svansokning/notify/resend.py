import logging

import httpx
import pandas as pd

from .. import config

log = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"


def _row_html(row) -> str:
    rent = f"£{int(row['monthly_rent_gbp'])}" if pd.notna(row.get("monthly_rent_gbp")) else "?"
    beds = int(row["bedrooms"]) if pd.notna(row.get("bedrooms")) else "?"
    d_anchor = f"{row['dist_anchor_km']:.1f}km" if pd.notna(row.get("dist_anchor_km")) else "?"
    d_stn = f"{row['dist_station_km']:.1f}km" if pd.notna(row.get("dist_station_km")) else "?"
    d_aw = f"{row['dist_andrew_wiles_km']:.1f}km" if pd.notna(row.get("dist_andrew_wiles_km")) else "?"
    title = row.get("title") or row.get("address") or row.get("id")
    url = row.get("url") or "#"
    source = row.get("source") or ""
    return (
        f'<tr><td><a href="{url}">{title}</a></td>'
        f"<td>{rent}</td><td>{beds}</td>"
        f"<td>{d_anchor}</td><td>{d_stn}</td><td>{d_aw}</td>"
        f"<td>{source}</td></tr>"
    )


def _digest_html(new_df: pd.DataFrame, drops_df: pd.DataFrame) -> str:
    parts: list[str] = []
    parts.append("<h2>svansökning daily digest</h2>")
    if new_df.empty and drops_df.empty:
        parts.append("<p>No new listings or price drops today.</p>")
    table_head = (
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>Listing</th><th>Rent</th><th>Beds</th>"
        "<th>From anchor</th><th>From station</th><th>From AWB</th><th>Source</th></tr>"
    )
    if not new_df.empty:
        parts.append(f"<h3>New ({len(new_df)})</h3>{table_head}")
        parts.extend(_row_html(r) for _, r in new_df.iterrows())
        parts.append("</table>")
    if not drops_df.empty:
        parts.append(f"<h3>Price drops ({len(drops_df)})</h3>{table_head}")
        parts.extend(_row_html(r) for _, r in drops_df.iterrows())
        parts.append("</table>")
    return "".join(parts)


def send_digest(new_df: pd.DataFrame, drops_df: pd.DataFrame) -> bool:
    if new_df.empty and drops_df.empty:
        log.info("resend: nothing to send today")
        return False
    if not config.RESEND_API_KEY or not config.RESEND_TO_EMAIL:
        log.warning("resend: missing RESEND_API_KEY or RESEND_TO_EMAIL — skipping send")
        return False
    payload = {
        "from": config.RESEND_FROM_EMAIL,
        "to": [config.RESEND_TO_EMAIL],
        "subject": f"svansökning — {len(new_df)} new, {len(drops_df)} price drop(s)",
        "html": _digest_html(new_df, drops_df),
    }
    headers = {
        "Authorization": f"Bearer {config.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    r = httpx.post(API_URL, json=payload, headers=headers, timeout=15.0)
    if r.status_code >= 400:
        log.error("resend: %s %s", r.status_code, r.text[:300])
        return False
    log.info("resend: sent digest, id=%s", r.json().get("id", "?"))
    return True
