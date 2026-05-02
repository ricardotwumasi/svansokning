from svansokning.distance import haversine_km


def test_zero_distance():
    assert haversine_km(51.75, -1.27, 51.75, -1.27) == 0.0


def test_oxford_station_to_andrew_wiles_under_2km():
    # OX1 1HS ~ (51.7534, -1.2701), OX2 6GG ~ (51.7609, -1.2638). Real walking is ~1km;
    # haversine will be ~0.9km — well under 2.
    d = haversine_km(51.7534, -1.2701, 51.7609, -1.2638)
    assert 0.5 < d < 2.0


def test_symmetry():
    a = haversine_km(51.5, -0.1, 52.0, -0.5)
    b = haversine_km(52.0, -0.5, 51.5, -0.1)
    assert abs(a - b) < 1e-9
