REFERENCE_POINTS = {
    "oxford_station": {"postcode": "OX1 1HS", "label": "Oxford station"},
    "andrew_wiles": {"postcode": "OX2 6GG", "label": "Andrew Wiles Building"},
}

DEFAULT_ANCHOR = {"postcode": "OX2 6BS", "label": "Jericho centre"}

DEFAULT_CRITERIA = {
    "anchor_postcode": DEFAULT_ANCHOR["postcode"],
    "min_bedrooms": 1,
    "max_bedrooms": 3,
    "max_rent_gbp": 2200,
    "max_radius_km": 3.0,
    "sources_enabled": ["openrent", "zoopla"],
}
