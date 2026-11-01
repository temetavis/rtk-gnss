"""End-to-end RTK simulation: shows float -> fixed convergence.

Run: python3 -m exercises.rtk_solver.simulate
"""

from .observations import simulate_observations
from .satellites import geodetic_to_ecef
from .solver import solve


def main():
    base = geodetic_to_ecef(60.1699, 24.9384, 50.0)   # Helsinki-ish
    true_rover = geodetic_to_ecef(60.1799, 24.9484, 55.0)
    true_baseline = tuple(r - b for r, b in zip(true_rover, base))
    print(f"true baseline (ECEF, m): "
          f"{true_baseline[0]:.3f} {true_baseline[1]:.3f} "
          f"{true_baseline[2]:.3f}")

    for n_epoch in (3, 5, 10, 20):
        obs = simulate_observations(true_rover, base, n_epoch=n_epoch,
                                    phase_noise_cycles=0.01)
        result = solve(obs, base, base)
        bl = result["baseline"]
        err = sum((bl[k] - true_baseline[k]) ** 2 for k in range(3)) ** 0.5
        print(f"epochs={n_epoch:3d}  status={result['status']:5s}  "
              f"ratio={result['ratio']:8.2f}  3D error={err * 100:6.1f} cm  "
              f"true amb={obs['ambiguities'][:3]}...")

    obs = simulate_observations(true_rover, base, n_epoch=20,
                                phase_noise_cycles=0.01)
    result = solve(obs, base, base)
    if result["status"] == "fixed":
        print(f"fixed ambiguities match truth: "
              f"{result['ambiguities'] == obs['ambiguities']}")


if __name__ == "__main__":
    main()
