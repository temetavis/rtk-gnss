import math

import pytest

from exercises.coords.transforms import (
    ecef_to_enu,
    ecef_to_geodetic,
    ellipsoidal_to_orthometric,
    geodetic_to_ecef,
    to_utm,
)


def test_ecef_geodetic_roundtrip():
    lat, lon, h = 60.1699, 24.9384, 50.0
    x, y, z = geodetic_to_ecef(lat, lon, h)
    lat2, lon2, h2 = ecef_to_geodetic(x, y, z)
    assert lat2 == pytest.approx(lat, abs=1e-9)
    assert lon2 == pytest.approx(lon, abs=1e-9)
    assert h2 == pytest.approx(h, abs=1e-6)


def test_known_ecef_values():
    # Helsinki-ish point, sanity against standard formulas
    x, y, z = geodetic_to_ecef(0.0, 0.0, 0.0)
    assert z == pytest.approx(0.0)
    assert math.hypot(x, y) == pytest.approx(6378137.0)


def test_enu_of_same_point_is_zero():
    x, y, z = geodetic_to_ecef(60.0, 25.0, 100.0)
    e, n, u = ecef_to_enu(x, y, z, 60.0, 25.0, 100.0)
    assert e == pytest.approx(0.0, abs=1e-6)
    assert n == pytest.approx(0.0, abs=1e-6)
    assert u == pytest.approx(0.0, abs=1e-6)


def test_enu_axes_sanity():
    # moving east must increase the east component
    x1, y1, z1 = geodetic_to_ecef(60.0, 25.0, 0.0)
    x2, y2, z2 = geodetic_to_ecef(60.0, 25.01, 0.0)
    e, n, u = ecef_to_enu(x2, y2, z2, 60.0, 25.0, 0.0)
    assert e > 0
    assert abs(n) < e
    assert abs(u) < e


def test_tm35fin_projection():
    # ETRS89 lat/lon -> ETRS-TM35FIN easting/northing (EPSG:3067)
    east, north = to_utm(60.1699, 24.9384, epsg=3067)
    # Helsinki is west of the 27E central meridian -> ~385.6 km easting (false 500 km)
    assert east == pytest.approx(385611, abs=100)
    assert north == pytest.approx(6672118, abs=100)


def test_height_conversion():
    # ellipsoidal 50 m, geoid undulation 20 m -> orthometric 30 m
    assert ellipsoidal_to_orthometric(50.0, 20.0) == 30.0
