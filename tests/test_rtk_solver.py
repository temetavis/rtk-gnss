import pytest

from exercises.rtk_solver.observations import simulate_observations
from exercises.rtk_solver.satellites import geodetic_to_ecef, make_constellation
from exercises.rtk_solver.solver import (
    fixed_baseline, float_solution, integer_search, ratio_test, solve,
)

BASE = geodetic_to_ecef(60.1699, 24.9384, 50.0)
ROVER = geodetic_to_ecef(60.1799, 24.9484, 55.0)


def test_constellation_deterministic():
    a = make_constellation()
    b = make_constellation()
    assert a[0].position(0.0) == b[0].position(0.0)


def test_satellite_positions_change_with_time():
    sat = make_constellation()[0]
    assert sat.position(0.0) != sat.position(600.0)


def test_observations_contain_true_ambiguities():
    obs = simulate_observations(ROVER, BASE, n_epoch=5)
    assert len(obs["ambiguities"]) == obs["n_sats"] - 1
    assert all(isinstance(a, int) for a in obs["ambiguities"])
    assert len(obs["epochs"]) == 5


def test_float_solution_close_with_known_ambiguities():
    obs = simulate_observations(ROVER, BASE, n_epoch=10,
                                phase_noise_cycles=0.01)
    dx, amb = float_solution(obs, BASE, BASE)
    true_bl = tuple(r - b for r, b in zip(ROVER, BASE))
    err = sum((dx[k] - true_bl[k]) ** 2 for k in range(3)) ** 0.5
    # float solution with dm-level phase noise: sub-meter expected
    assert err < 1.0


def test_integer_search_neighborhood():
    cands = integer_search([1.4, -2.6], search_width=1)
    assert [1, -3] in cands
    assert len(cands) == 9


def test_rtk_end_to_end_fixed():
    obs = simulate_observations(ROVER, BASE, n_epoch=20,
                                phase_noise_cycles=0.005)
    result = solve(obs, BASE, BASE)
    true_bl = tuple(r - b for r, b in zip(ROVER, BASE))
    assert result["status"] == "fixed"
    assert result["ratio"] >= 3.0
    assert result["ambiguities"] == obs["ambiguities"]
    err = sum((result["baseline"][k] - true_bl[k]) ** 2
              for k in range(3)) ** 0.5
    assert err < 0.10, f"fixed baseline error {err:.3f} m too large"


def test_fixed_baseline_from_true_ambiguities_is_accurate():
    obs = simulate_observations(ROVER, BASE, n_epoch=10,
                                phase_noise_cycles=0.001)
    bl = fixed_baseline(obs, BASE, obs["ambiguities"])
    true_bl = tuple(r - b for r, b in zip(ROVER, BASE))
    err = sum((bl[k] - true_bl[k]) ** 2 for k in range(3)) ** 0.5
    assert err < 0.05
