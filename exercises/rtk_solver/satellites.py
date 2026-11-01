"""Synthetic GNSS satellite constellation and geometry for simulations.

Satellites orbit a spherical Earth in circular orbits; positions are
analytic and deterministic so all exercises are reproducible.
"""

import math

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3
C = 299792458.0  # m/s

RE = WGS84_A
ORBIT_R = 26560e3  # GPS-like semi-major axis


class Satellite:
    def __init__(self, prn, inclination_deg, raan_deg, phase0, angular_rate):
        self.prn = prn
        self.inc = math.radians(inclination_deg)
        self.raan = math.radians(raan_deg)
        self.phase0 = phase0
        self.rate = angular_rate  # rad/s

    def position(self, t):
        """ECEF position at time t (seconds)."""
        u = self.phase0 + self.rate * t
        r = ORBIT_R
        x_orb = r * math.cos(u)
        y_orb = r * math.sin(u)
        cos_i, sin_i = math.cos(self.inc), math.sin(self.inc)
        cos_o, sin_o = math.cos(self.raan), math.sin(self.raan)
        x = x_orb * cos_o - y_orb * cos_i * sin_o
        y = x_orb * sin_o + y_orb * cos_i * cos_o
        z = y_orb * sin_i
        return (x, y, z)


def make_constellation(n=8, seed_phase=0.0):
    """Deterministic multi-plane constellation of n satellites."""
    sats = []
    for i in range(n):
        plane = i % 3
        sats.append(Satellite(
            prn=i + 1,
            inclination_deg=55.0,
            raan_deg=plane * 120.0,
            phase0=seed_phase + i * (2 * math.pi / n),
            angular_rate=2 * math.pi / (11 * 3600 + 58 * 60),  # ~12h period
        ))
    return sats


def unit_vector(a, b):
    dx, dy, dz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    return (dx / norm, dy / norm, dz / norm), norm


def geometry_matrix(sat_positions, approx_position):
    """Rows of unit line-of-sight vectors (sign per observation equation)."""
    rows = []
    for pos in sat_positions:
        los, _ = unit_vector(approx_position, pos)
        rows.append([-los[0], -los[1], -los[2]])
    return rows


def geodetic_to_ecef(lat_deg, lon_deg, h):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * sin_lat * sin_lat)
    x = (n + h) * cos_lat * cos_lon
    y = (n + h) * cos_lat * sin_lon
    z = (n * (1 - WGS84_E2) + h) * sin_lat
    return (x, y, z)
