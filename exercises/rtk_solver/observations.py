"""Simulated GNSS carrier-phase observations for a reference-rover baseline.

Model: double-difference carrier phase in cycles,
  ∇∇Φ = (∇∇ρ)/λ + ∇∇N + noise
where atmospherics are assumed cancelled (short baseline).
"""

import math
import random

from .satellites import make_constellation

L1_WAVELENGTH = 0.19029367266  # meters (GPS L1)


def simulate_observations(rover_ecef, base_ecef, n_epoch=10, seed=42,
                          phase_noise_cycles=0.02, n_sats=8):
    """Generate per-epoch double-difference phase observations.

    Returns dict with:
      'epochs': list of per-epoch {'dd_phase': [...], 'dd_range': [...]}
      'ambiguities': true integer ambiguities per DD pair
      'sat_positions': per-epoch list of ECEF tuples (ref satellite first)
    """
    rng = random.Random(seed)
    sats = make_constellation(n_sats)
    true_amb = [rng.randint(-2000, 2000) for _ in range(n_sats - 1)]

    epochs = []
    for e in range(n_epoch):
        t = e * 30.0
        sat_pos = [s.position(t) for s in sats]
        ref_sat = sat_pos[0]

        ranges_rover = [math.dist(rover_ecef, p) for p in sat_pos]
        ranges_base = [math.dist(base_ecef, p) for p in sat_pos]

        # single differences rover-base, then double difference vs ref sat
        dd_range = []
        dd_phase = []
        for i in range(1, n_sats):
            sd = ranges_rover[i] - ranges_rover[0] \
                - (ranges_base[i] - ranges_base[0])
            dd_range.append(sd)
            noise = rng.gauss(0, phase_noise_cycles)
            dd_phase.append(sd / L1_WAVELENGTH + true_amb[i - 1] + noise)

        epochs.append({
            "dd_phase": dd_phase,
            "dd_range": dd_range,
            "sat_positions": sat_pos,
        })

    return {"epochs": epochs, "ambiguities": true_amb,
            "wavelength": L1_WAVELENGTH, "n_sats": n_sats}
