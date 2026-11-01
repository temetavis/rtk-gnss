"""ETRS89 / EUREF-FIN specific helpers.

EUREF-FIN is the Finnish national realization of ETRS89, which is fixed to
the stable Eurasian plate. WGS84/ITRF coordinates move relative to it by
plate motion (~2.5 cm/yr in Finland). This module provides a simplified
parametric transform for learning; real production work uses the official
NKG / National Land Survey transformation grids.
"""

from datetime import date


def years_since_1989(d=None):
    """Years elapsed since the ETRS89 epoch (1989.0)."""
    d = d or date.today()
    return d.year - 1989.0 + d.timetuple().tm_yday / 365.25


def itrf_to_etrs89_approx(x, y, z, epoch_year):
    """Very approximate ITRF->ETRS89 shift for the Nordic region.

    Applies a fixed local displacement rate typical for Finland
    (~2.5 cm/yr relative motion since epoch 1989.0).
    For real work use the NKG/NLS transformation grids.
    """
    years = epoch_year - 1989.0
    dx = -0.015 * years
    dy = -0.020 * years
    dz = -0.008 * years
    return (x + dx, y + dy, z + dz)


def etrs89_to_itrf_approx(x, y, z, epoch_year):
    """Inverse of itrf_to_etrs89_approx."""
    ex, ey, ez = itrf_to_etrs89_approx(0.0, 0.0, 0.0, epoch_year)
    return (x - ex, y - ey, z - ez)
