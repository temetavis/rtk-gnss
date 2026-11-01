# GNSS Basics

## The core idea

A GNSS receiver computes its position by measuring **how long a signal took to
travel from a satellite**. Distance = speed of light × travel time:

```
ρ = c · (t_receive − t_transmit)
```

This measured distance is called a **pseudorange** — "pseudo" because the
receiver clock is not synchronized with the satellite clocks, so the range is
biased. With signals from at least 4 satellites, the receiver solves for
3 position unknowns + 1 clock bias.

## Constellations

| System | Owner | Frequencies (L-band) |
|---|---|---|
| GPS | USA | L1 (1575.42 MHz), L2, L5 |
| GLONASS | Russia | FDMA: ~1602 MHz + channel, also CDMA L3 |
| Galileo | EU | E1, E5a, E5b, E6 |
| BeiDou | China | B1, B2, B3 |

A multi-constellation receiver tracks all of these — this is why RTK
specifications mention "constellations" and "frequencies" prominently.

## Error sources (why plain GNSS is only ~3–10 m accurate)

| Source | Magnitude | Mitigated by |
|---|---|---|
| Satellite clock/orbit errors | 1–3 m | precise ephemerides, corrections |
| Ionospheric delay | up to 30 m | dual-frequency (iono-free combo), corrections |
| Tropospheric delay | 2–20 m | models, corrections |
| Multipath (signal reflections) | 0.5–5 m | receiver design, antenna siting |
| Receiver noise | 0.1–1 m | carrier smoothing |

All error sources except multipath/receiver noise are **spatially and
temporally correlated**: two receivers close together experience nearly the
same satellite clock error, ionosphere, and troposphere. This is the entire
basis of **differential GNSS** — a reference station at a known point measures
the combined error and transmits it to nearby users.

## Pseudorange vs carrier phase

Every GNSS signal has two measurable parts:

1. **Code** (PRN ranging code): coarse, noise ~1 m, unambiguous.
2. **Carrier** (the sinusoid itself): precise, noise ~1 mm, but **ambiguous** —
   the receiver only measures the fractional phase; it does not know how many
   whole cycles the signal has travelled since leaving the satellite.

The integer cycle unknowns are called **ambiguities** (N). Resolving them is
the whole game of high-accuracy positioning (RTK, PPP-RTK). The phase
observation equation:

```
λ · Φ = ρ + c·(dt_r − dt_s) + T − I + λ·N + ε
```

where λ is wavelength, Φ is cycles, T troposphere, I ionosphere, N the
integer ambiguity, ε noise.

## Dilution of precision (DOP)

Position accuracy also depends on satellite *geometry*. If all visible
satellites cluster in one corner of the sky, errors amplify. GDOP/PDOP/HDOP/VDOP
are geometry factors multiplying the ranging error. Sky plots and mask angles
(e.g. 10–15°) are everyday tools for a positioning network specialist.

## Exercise pointers

- `exercises/rtk_solver/satellites.py` — simulate satellite positions from
  simple circular orbits and build a geometry matrix.
- `exercises/rtk_solver/solver.py` — see the real observation equations in code.
