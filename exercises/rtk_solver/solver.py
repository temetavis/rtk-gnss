"""Simplified single-baseline RTK solver.

Pipeline: float least squares -> integer ambiguity search (LAMBDA-style
integer least squares over a rounded neighbourhood) -> ratio-test
validation -> fixed solution.

The geometry unknowns are per-epoch rover-baseline ENU (or ECEF) offsets;
ambiguities are common to all epochs (that's why they can be fixed).
"""

import itertools
import math


def float_solution(observations, base_ecef, approx_rover):
    """Least-squares float estimate of (dx, dy, dz) + ambiguities.

    Observation model per epoch i, DD pair j:
        λ·Φ_ij = -e_ij · dr + λ·N_j + residual
    where e_ij is the DD line-of-sight vector and dr the baseline correction.
    Solved with normal equations accumulated over all epochs.
    """
    lam = observations["wavelength"]
    epochs = observations["epochs"]
    n_sats = observations["n_sats"]
    n_amb = n_sats - 1
    n_epoch = len(epochs)

    n_unknowns = 3 + n_amb
    # accumulate normal equations A^T P A x = A^T P l with unit weights
    ata = [[0.0] * n_unknowns for _ in range(n_unknowns)]
    atl = [0.0] * n_unknowns

    for e_idx, epoch in enumerate(epochs):
        sat_pos = epoch["sat_positions"]
        ref_sat = sat_pos[0]
        for j, dd in enumerate(epoch["dd_phase"]):
            sat = sat_pos[j + 1]
            ux, uy, uz = dd_los(base_ecef, ref_sat, sat)
            row = [-ux, -uy, -uz]
            row += [0.0] * n_amb
            row[3 + j] = lam
            l = lam * dd  # measured phase in meters

            for a in range(n_unknowns):
                atl[a] += row[a] * l
                for b in range(n_unknowns):
                    ata[a][b] += row[a] * row[b]

    x = gauss_solve(ata, atl)
    dx = x[0:3]
    amb_float = x[3:]
    return dx, amb_float


def dd_los(base_ecef, ref_sat, sat):
    """Unit double-difference line-of-sight vector for geometry terms.

    Approximation: difference of unit vectors from the reference station to
    the two satellites; exact enough for short baselines.
    """
    def unit(a, b):
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        n = math.sqrt(dx * dx + dy * dy + dz * dz)
        return (dx / n, dy / n, dz / n)

    e_ref = unit(base_ecef, ref_sat)
    e_sat = unit(base_ecef, sat)
    return (e_sat[0] - e_ref[0], e_sat[1] - e_ref[1], e_sat[2] - e_ref[2])


def gauss_solve(a, b):
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("singular normal matrix")
        m[col], m[pivot] = m[pivot], m[col]
        pv = m[col][col]
        for r in range(n):
            if r == col:
                continue
            factor = m[r][col] / pv
            for c in range(col, n + 1):
                m[r][c] -= factor * m[col][c]
    return [m[i][n] / m[i][i] for i in range(n)]


def round_ambiguities(amb_float):
    return [int(round(a)) for a in amb_float]


def integer_search(amb_float, search_width=3):
    """Enumerate integer candidates near the float solution.

    A real solver decorrelates with a Z-transformation first (LAMBDA);
    here we brute-force a small box, which is fine for learning purposes.
    """
    n = len(amb_float)
    centers = [int(round(a)) for a in amb_float]
    ranges = [range(c - search_width, c + search_width + 1)
              for c in centers]
    return [list(cand) for cand in itertools.product(*ranges)]


def ratio_test(observations, base_ecef, approx_rover, candidates,
               ratio_threshold=3.0):
    """Score candidates by residual sum; return (best, second_ratio).

    Returns the fixed baseline of the best candidate and the
    best/second-best residual ratio. ratio > threshold => accepted fix.
    """
    lam = observations["wavelength"]
    scores = []
    for cand in candidates:
        res2 = 0.0
        for epoch in observations["epochs"]:
            sat_pos = epoch["sat_positions"]
            ref_sat = sat_pos[0]
            for j, dd in enumerate(epoch["dd_phase"]):
                pred = lam * (dd - cand[j])
                # residual after removing geometry contribution of the
                # best-fit baseline is approximated by DD range agreement
                obs_range = epoch["dd_range"][j]
                res = pred - obs_range
                res2 += res * res
        scores.append((res2, cand))
    scores.sort(key=lambda s: s[0])
    best_res, best_cand = scores[0]
    second_res = scores[1][0] if len(scores) > 1 else math.inf
    ratio = second_res / best_res if best_res > 0 else math.inf
    accepted = ratio >= ratio_threshold
    return best_cand, ratio, accepted


def fixed_baseline(observations, base_ecef, amb_int):
    """Baseline (dx, dy, dz) from fixed ambiguities: LSQ over geometry only."""
    lam = observations["wavelength"]
    ata = [[0.0] * 3 for _ in range(3)]
    atl = [0.0] * 3
    for epoch in observations["epochs"]:
        sat_pos = epoch["sat_positions"]
        ref_sat = sat_pos[0]
        for j, dd in enumerate(epoch["dd_phase"]):
            sat = sat_pos[j + 1]
            ux, uy, uz = dd_los(base_ecef, ref_sat, sat)
            row = [-ux, -uy, -uz]
            l = lam * (dd - amb_int[j])
            for a in range(3):
                atl[a] += row[a] * l
                for b in range(3):
                    ata[a][b] += row[a] * row[b]
    return gauss_solve(ata, atl)


def solve(observations, base_ecef, approx_rover, ratio_threshold=3.0):
    """Full RTK pipeline; returns a dict describing the solution."""
    dx_float, amb_float = float_solution(observations, base_ecef, approx_rover)
    candidates = integer_search(amb_float, search_width=2)
    best_cand, ratio, accepted = ratio_test(
        observations, base_ecef, approx_rover, candidates, ratio_threshold)
    if not accepted:
        return {"status": "float", "baseline": dx_float,
                "ambiguities": amb_float, "ratio": ratio}
    baseline = fixed_baseline(observations, base_ecef, best_cand)
    return {"status": "fixed", "baseline": baseline,
            "ambiguities": best_cand, "ratio": ratio}
