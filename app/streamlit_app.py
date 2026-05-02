"""svansökning dashboard — read-only view of data/listings.parquet."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from svansokning import config, constants, filters, storage  # noqa: E402

st.set_page_config(page_title="svansökning", layout="wide")
st.title("svansökning")
st.caption("Personal Oxford rental search — daily digest, editable filters.")


@st.cache_data(ttl=300)
def load() -> pd.DataFrame:
    return storage.read_listings()


def _load_state() -> dict:
    return {**constants.DEFAULT_CRITERIA, **storage.read_json(config.UI_STATE, {})}


def _save_state(state: dict) -> None:
    storage.write_json(config.UI_STATE, state)


df = load()
saved = _load_state()

with st.sidebar:
    st.header("Criteria")
    anchor_postcode = st.text_input("Anchor postcode", value=saved["anchor_postcode"])
    max_radius_km = st.slider("Max radius (km)", 0.5, 10.0, float(saved["max_radius_km"]), 0.5)
    bed_range = st.slider(
        "Bedrooms", 0, 6,
        (int(saved["min_bedrooms"]), int(saved["max_bedrooms"])),
    )
    max_rent_gbp = st.number_input(
        "Max monthly rent (£)", min_value=0, max_value=10000,
        value=int(saved["max_rent_gbp"]), step=50,
    )
    available_sources = sorted(df["source"].dropna().unique().tolist()) if not df.empty else []
    sources_enabled = st.multiselect(
        "Sources", options=available_sources or saved["sources_enabled"],
        default=[s for s in saved["sources_enabled"] if not available_sources or s in available_sources],
    )
    if st.button("Save criteria"):
        _save_state({
            "anchor_postcode": anchor_postcode,
            "max_radius_km": max_radius_km,
            "min_bedrooms": bed_range[0],
            "max_bedrooms": bed_range[1],
            "max_rent_gbp": max_rent_gbp,
            "sources_enabled": sources_enabled,
        })
        st.success("Saved.")

criteria = {
    "anchor_postcode": anchor_postcode,
    "max_radius_km": max_radius_km,
    "min_bedrooms": bed_range[0],
    "max_bedrooms": bed_range[1],
    "max_rent_gbp": max_rent_gbp,
    "sources_enabled": sources_enabled,
}

if df.empty:
    st.info("No listings yet. The daily cron will populate `data/listings.parquet`.")
    st.stop()

# NB: anchor changes don't recompute distances at view time — they are computed
# at scrape time against the saved anchor. Changing anchor_postcode here only
# takes effect on the next cron run (when daily_scrape.py reads the saved state).
view = filters.apply_criteria(df, criteria).sort_values("dist_anchor_km")

st.metric("Matching listings", len(view))

display_cols = [
    "title", "monthly_rent_gbp", "bedrooms",
    "dist_anchor_km", "dist_station_km", "dist_andrew_wiles_km",
    "postcode", "source", "first_seen_at", "url",
]
display_cols = [c for c in display_cols if c in view.columns]

st.dataframe(
    view[display_cols],
    column_config={
        "url": st.column_config.LinkColumn("Link", display_text="open"),
        "monthly_rent_gbp": st.column_config.NumberColumn("Rent £/mo", format="£%d"),
        "dist_anchor_km": st.column_config.NumberColumn("From anchor (km)", format="%.2f"),
        "dist_station_km": st.column_config.NumberColumn("From station (km)", format="%.2f"),
        "dist_andrew_wiles_km": st.column_config.NumberColumn("From AWB (km)", format="%.2f"),
        "first_seen_at": st.column_config.DatetimeColumn("First seen"),
    },
    hide_index=True,
    use_container_width=True,
)
