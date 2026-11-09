# RTK-GNSS Learning Sandbox

A hands-on sandbox for learning the technologies behind **GNSS positioning** and
**network RTK correction services** — the kind of stack used by commercial
RTK correction providers and national GNSS reference station networks.

## What is covered

| Area | Where | What you learn |
|---|---|---|
| GNSS fundamentals | `docs/01-gnss-basics.md` | Pseudoranges, trilateration, error sources, DOP |
| RTK & network RTK | `docs/02-rtk-and-network-rtk.md` | Carrier phase, ambiguities, VRS, MAC, FKP concepts |
| NTRIP | `docs/03-ntrip.md` + `exercises/ntrip/` | The protocol correction streams ride on; a mock caster you can run |
| RTCM messages | `docs/04-rtcm-messages.md` + `exercises/rtcm/` | RTCM 3.x framing and how to parse a 1005 station coordinate message |
| Coordinate systems | `docs/05-coordinate-systems.md` + `exercises/coords/` | WGS84, ETRS89, EUREF-FIN, ENU/local frames, UTM, heights |
| RTK solver | `exercises/rtk_solver/` | A simplified single-baseline RTK engine, end to end |
| Service health dashboard | `docs/06-service-health-dashboard.md` + `exercises/dashboard/` | What an RTK provider monitors; a mock mobile web dashboard |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run all exercise tests (each exercise is self-verifying)
pytest

# run the mock NTRIP caster on localhost and connect a client
python3 -m exercises.ntrip.caster          # terminal 1
python3 -m exercises.ntrip.client          # terminal 2

# watch the RTK solver converge from float to fixed ambiguities
python3 -m exercises.rtk_solver.simulate

# run the mock service health dashboard (mobile web UI + JSON API)
python3 -m exercises.dashboard.app    # http://127.0.0.1:8000/
```

## Suggested study order

1. Read `docs/01-gnss-basics.md`, then poke at `exercises/rtk_solver/satellites.py`.
2. Read `docs/03-ntrip.md`, run the mock caster, and read its source — it is
   a complete NTRIP implementation in one small file.
3. Read `docs/04-rtcm-messages.md` and do the RTCM framing exercises.
4. Read `docs/02-rtk-and-network-rtk.md`, then study
   `exercises/rtk_solver/solver.py` — it implements float/fixed ambiguity
   resolution with integer least squares (LAMBDA-style) in pure Python.
5. Finish with `docs/05-coordinate-systems.md` and the coordinate exercises.
6. Skim `docs/06-service-health-dashboard.md`, run the dashboard, and read
   `exercises/dashboard/service.py` — how a provider turns station telemetry
   into healthy / degraded / down statuses.

## Real-world resources

- [RTKLIB](http://www.rtklib.com/) — open-source GNSS positioning library
- [NTRIP spec (RFC 9100)](https://www.rfc-editor.org/rfc/rfc9100)
- [RTCM standards](https://www.rtcm.org/) (SC-104 messages)
- [IGS network](https://igs.org/) — global reference station network
- [EUREF-FIN & Finnish national network (FGI)](https://www.maanmittauslaitos.fi/en/maps-and-spatial-data/positioning-services)
- [EGNOS / ESA Navipedia](https://gssc.esa.int/navipedia/) — excellent GNSS textbook online
