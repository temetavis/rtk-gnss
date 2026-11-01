# RTK and Network RTK

## From DGPS to RTK

**DGPS**: reference station transmits pseudorange corrections; user accuracy
improves to ~1 m. Still limited by code-measurement noise.

**RTK (Real-Time Kinematic)**: use *carrier phase* instead of code, and resolve
the integer ambiguities. Once ambiguities are fixed to their correct integers,
the range error drops to millimetre level → centimetre accuracy in real time.

## How ambiguity resolution works (single baseline)

1. **Double differencing**: form between-receiver and between-satellite
   differences. This cancels satellite and receiver clocks and largely
   cancels atmosphere for short baselines. What remains: geometry (ρ),
   residual atmosphere, and the **integer ambiguities**.
2. **Float solution**: solve the least-squares problem treating ambiguities
   as reals. Accuracy ~dm.
3. **Integer search** (LAMBDA and friends): search integer candidates near the
   float solution, using the ambiguity covariance matrix. Validate with a
   ratio test (best candidate must beat second-best decisively).
4. **Fixed solution**: correct the float estimate with the chosen integers →
   cm accuracy.

`exercises/rtk_solver/solver.py` implements exactly this pipeline:
float LSQ → integer search with Z-transformation → ratio test → fixed solution.
The simulation (`simulate.py`) shows the float-to-fixed convergence.

## Requirements for RTK in practice

- Dual-frequency receiver (to eliminate ionosphere and to widen the ambiguity
  search space cleanly)
- At least 5 satellites, good geometry, low multipath
- Data link: **NTRIP over cellular** is the industry standard
- Baseline length matters: single-baseline RTK degrades beyond ~10–20 km as
  atmospheric correlation breaks down → enter **network RTK**.

## Network RTK

Instead of one reference station, a **network of continuously operating
reference stations (CORS)** covers a region. A central service models the
spatial behavior of the atmosphere and satellite errors across the whole
network and generates a correction tailored to *each user's approximate
position*. This extends cm-accuracy to baselines of 30–70 km from the nearest
station.

Three main generation approaches:

### 1. VRS (Virtual Reference Station)
User sends its approximate position (via **NMEA GGA** in the NTRIP request);
the service computes a synthetic "virtual" reference station near the user and
streams corrections **as if** that station were real. Most common approach for
consumer/professional RTK services. Watch for: the rover must send GGA, and
corrections are position-dependent — a stale GGA means degraded corrections.

### 2. MAC (Master-Auxiliary Concept)
Transmits full corrections for one *master* station plus *interpolated*
residuals of the surrounding auxiliary stations. The rover reconstructs
corrections for its own location. More bandwidth-efficient; RTCM message types
1021–1029 / 1030–1039 relate to this.

### 3. FKP (Flächenkorrekturparameter, "area correction parameters")
Transmits gradient coefficients of a linear atmospheric model; the rover
applies the model itself. Older approach, declining use.

## RTCM corrections in practice

The chosen representation is streamed as **RTCM 3.x** messages over NTRIP
(see `docs/03-ntrip.md` and `docs/04-rtcm-messages.md`). Typical message sets
for network RTK: MSM4/MSM6/7 (observations), 1005/1006 (station coordinates,
antenna height), 1019/1042 etc. (ephemerides), 1030–1037 (network residuals).

## Reliability / operations

A commercial correction service is fundamentally an operations business:

- Reference station uptime and monitoring (cycle slips, noise, multipath)
- Latency budget (corrections older than a few seconds degrade the fix)
- Redundancy: overlapping networks (some providers use national CORS data,
  e.g. geodetic agency networks of ~90 stations)
- Compatibility: open RTCM formats so any rover brand works
- Account/credential management at the NTRIP caster (mountpoint = product)

## Exercise pointers

- `exercises/ntrip/` — a complete mock caster handling GGA and mountpoints,
  the operations-facing side of the service.
- `exercises/rtk_solver/solver.py` — float/fixed ambiguity resolution.
- `exercises/rtcm/` — parsing station coordinates (msg 1005) from a stream.
