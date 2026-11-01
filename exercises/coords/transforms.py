"""Core coordinate transforms: ECEF <-> geodetic, ENU, heights, UTM."""

import math

from pyproj import CRS, Transformer

WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
WGS84_E2 = 2 * WGS84_F - WGS84_F * WGS84_F


def geodetic_to_ecef(lat_deg, lon_deg, h):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * sin_lat * sin_lat)
    x = (n + h) * cos_lat * math.cos(lon)
    y = (n + h) * cos_lat * math.sin(lon)
    z = (n * (1 - WGS84_E2) + h) * sin_lat
    return (x, y, z)


def ecef_to_geodetic(x, y, z):
    """Bowring's iterative method."""
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - WGS84_E2))
    for _ in range(10):
        sin_lat = math.sin(lat)
        n = WGS84_A / math.sqrt(1 - WGS84_E2 * sin_lat * sin_lat)
        h = p / math.cos(lat) - n if abs(math.cos(lat)) > 1e-9 else z - n
        lat = math.atan2(z, p * (1 - WGS84_E2 * n / (n + h)))
    return (math.degrees(lat), math.degrees(lon), h)


def ecef_to_enu(x, y, z, lat_deg, lon_deg, h_ref=0.0):
    """Local East-North-Up components relative to a reference point."""
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    ref = geodetic_to_ecef(lat_deg, lon_deg, h_ref)
    dx, dy, dz = x - ref[0], y - ref[1], z - ref[2]
    east = -sin_lon * dx + cos_lon * dy
    north = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    up = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
    return (east, north, up)


_utm_transformers = {}


def to_utm(lat_deg, lon_deg, epsg=3067):
    """Project to a Transverse Mercator grid (default: ETRS-TM35FIN, EPSG:3067).

    Input must be in the frame matching the EPSG (ETRS89 for 3067).
    """
    if epsg not in _utm_transformers:
        _utm_transformers[epsg] = Transformer.from_crs(
            CRS.from_epsg(4937), CRS.from_epsg(epsg), always_xy=True)
    return _utm_transformers[epsg].transform(lon_deg, lat_deg)


def ellipsoidal_to_orthometric(h_ellipsoidal, geoid_undulation):
    """H = h - N (N positive where geoid is above the ellipsoid)."""
    return h_ellipsoidal - geoid_undulation
