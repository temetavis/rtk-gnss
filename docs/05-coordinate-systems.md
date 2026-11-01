# Coordinate Systems and Heights

A positioning network specialist lives between several coordinate systems and
must convert between them fluently.

## The stack of frames

| Frame | What it is |
|---|---|
| WGS84 | GPS native frame; geocentric ECEF (X,Y,Z) or geodetic (lat,lon,h) |
| ITRF | International Terrestrial Reference Frame — realization of WGS84 at cm level, epoch-dated |
| ETRS89 | Europe-fixed frame; tied to the stable part of the Eurasian plate (no plate motion inside Europe) |
| EUREF-FIN | Finnish national realization of ETRS89 |
| ECEF vs ENU | Earth-Centered-Earth-Fixed cartesian vs local East-North-Up topocentric |

**Why ETRS89 exists**: plate tectonics move Europe ~2.5 cm/yr relative to
WGS84/ITRF. Maps should not drift, so European countries freeze their
national frames to ETRS89 (epoch 1989.0). The difference between ITRF (current
epoch) and ETRS89 grows ~2.5 cm per year and must be handled when mixing
modern GNSS output with national coordinates.

## Common conversions

- ECEF ↔ geodetic (WGS84 ellipsoid: a=6378137.0, f=1/298.257223563)
  — closed formulas one way, iterative (Bowring) the other.
- ECEF → ENU: rotate by the local geodetic lat/lon. This is how baseline
  vectors become readable "east/north/up" components.
- ETRS89/EUREF-FIN → UTM projection (zone 34/35 in Finland) or the national
  grid (ETRS-TM35FIN, ETRS-GK25FIN).

## Heights: three different "heights" of the same point

1. **Ellipsoidal height (h)**: above the WGS84 ellipsoid. What GNSS gives you.
2. **Geoid height (N)**: offset between ellipsoid and geoid (mean sea level
   surface), from gravity models like **FIN2005N00** in Finland or the global
   EGM2008.
3. **Orthometric height (H = h − N)**: above mean sea level. What maps and
   construction use.

Getting a GNSS height right in practice = knowing your local geoid model.
This is why "RTK gives you cm horizontal but you must be careful with
heights" — a wrong or absent geoid model silently biases elevations.

## Antenna reference points (ARP) and eccentricities

Measured coordinates refer to an antenna reference point; the pole tip
(rod) or ground mark sits at known vertical offsets. Total station /
GNSS combo work (measure-and-mark, stakeout) requires tracking these
constants exactly.

## Exercise pointers

- `exercises/coords/transforms.py` — ECEF↔geodetic (Bowring), ECEF↔ENU,
  UTM via pyproj, ellipsoidal↔orthometric heights.
- `exercises/coords/finland.py` — ETRS89 / EUREF-FIN notes as code:
  WGS84↔ETRS89 plate-motion transform (parametrized), Finnish grid usage.
- `tests/test_coords.py` — checks known point conversions.

## Further reading

- [ESA Navipedia — reference frames](https://gssc.esa.int/navipedia/index.php/Reference_Frames)
- Finnish Geospatial Institute positioning services and FIN2005N00 geoid
- EPSG registry codes: EPSG:4326 (WGS84), EPSG:4937/4936 (ETRS89),
  EPSG:3067 (ETRS-TM35FIN)
