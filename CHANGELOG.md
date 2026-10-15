# Changelog

All notable changes to the IBM AI Racing 2026 driver are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [V3.2] — Crash-prevention: smooth steering, robust braking, braking downshift

### Crash evidence (Corkscrew, lap 1)
- **Step 3265**, distFromStart **2467.9 m**, lapTime 66.582 s
- Speed at impact: **68 km/h** (down from 222 km/h peak), damage = **123**
- Root causes confirmed in telemetry `torcs_v3_physics_20261015-104305/ticks.csv`:
  - **Bang-bang steering** (steps 3053–3145): steer flipped between −1.0 and +1.0
    every 2–8 ticks because the single-longest-ray index jumped across the centre
    line; with `STEER_AIM=1.0 / STEER_LOCK=0.366` the aim term alone = 2.73 →
    always saturated.
  - **Free-distance spike cancelling brakes**: step 3077 read 121.0 m (→ no brake),
    step 3078 read 17.1 m — a 100 m drop in one tick.  At step 3205 the car was
    still at **125.6 km/h** with only **17.6 m** of free distance ahead.

### Fixed
- **Smooth aim** (`get_aim_angle_rad`): replaced single-longest-ray pick with a
  distance-weighted average of the `STEER_AIM_TOP_N` (default 3) longest rays.
  The weighted angle changes smoothly even when the dominant index alternates.
- **STEER_AIM 1.0 → 0.35**: with the averaged angle the contribution stays well
  below ±1.0 (at 45° aim: `0.35 × π/4 / 0.366 ≈ 0.94`), leaving room for the
  centering term to act.
- **Steering low-pass filter** (`STEER_SMOOTH = 0.5`):
  `steer = 0.5 × prev + 0.5 × raw` — a single noisy tick cannot flip the sign.
- **Robust free distance** (`FREE_DIST_MEMORY = 5`): `get_free_distance_ahead`
  now returns the *rolling minimum* of the last 5 ticks; a single long spike
  cannot release braking.
- **Safer braking** — `BRAKE_DECEL 9.0 → 7.0`, `V_CORNER_SHARP 70 → 60 km/h`:
  braking distance is conservatively underestimated so the car begins slowing
  earlier.  Full brake (1.0) is applied whenever the speed excess over the target
  exceeds `BRAKE_DECEL × 0.5 m/s`.
- **Braking downshift** (`shift_gears(braking=True)`): when `brake > 0`, the
  gear is dropped to match current speed using the `_GEAR_SPEED_KMH_PER_1000RPM`
  table, ensuring the engine is in the correct range for corner-exit acceleration.

### Added (PARAMS)
- `STEER_AIM_TOP_N = 3` — number of rays used in weighted-average aim direction.
- `STEER_SMOOTH = 0.5` — low-pass coefficient for the steering output.
- `FREE_DIST_MEMORY = 5` — rolling-minimum window (ticks) for forward distance.

### Added (self-test)
- **Case 5**: primes the steering filter for 15 ticks with a right-corner cluster
  (indices 11–13, +10°..+20°, 150 m), letting `_prev_steer` converge to ≈ −0.250.
  Then feeds one noisy tick with only index 7 (−10°) spiking to 25 m.
  Asserts `s_noisy < 0.5` — the low-pass filter must attenuate the glitch so the
  output cannot saturate to ±1.0 (the V3.1 bang-bang symptom).

---

## [V3.1] — Steering sign fix (pre-race code review)

### Fixed
- **`calculate_steering()` in `src/torcs_v3_physics.py`**: the aim term was
  *added* instead of *subtracted*, inverting the steering direction relative to
  the open-road sensor.

  In TORCS/SCR (confirmed from `snakeoil3_gym_BASELINE.py::drive_example`):
  - Track sensor angle **positive** → road opens to the **right** of the car.
  - Steer value **positive** → car turns **left**.

  Therefore a positive `aim_angle_rad` (open road on the right) must *reduce*
  the steer value, not increase it.

  **Before (buggy):**
  ```
  steer = (angle + aim_gain * aim_angle_rad - centering) / STEER_LOCK
  ```
  **After (correct):**
  ```
  steer = (angle - aim_gain * aim_angle_rad - centering) / STEER_LOCK
  ```

  Without this fix the car would steer away from every corner exit, hitting the
  outer wall and accumulating damage on the first competitive lap.

### Added
- Self-test runnable with `python src/torcs_v3_physics.py --selftest`.
  Four synthetic sensor scenarios (open road right, open road left, car on left
  edge, car on right edge) assert that the steering sign is correct in each
  case. No TORCS server connection is required.

- Updated `calculate_steering()` docstring to document the TORCS/SCR
  sign convention explicitly, referencing the baseline driver as the
  authoritative source.

---

## [V3.0] — Initial physics driver

### Added
- Physics-based target speed using kinematic braking-distance model:
  `v_target = sqrt(V_corner² + 2 · a_brake · d)`.
- Racing-line steering that aims toward the longest track sensor ray (corner
  exit), with straight-line aim-gain reduction to prevent weaving.
- Progressive edge-centering when `|trackPos|` exceeds `TRACK_MARGIN`.
- ABS wheel-slip control and proportional traction-control system.
- Smooth throttle curve and RPM-based gear shifting with minimum hold time
  to prevent gear hunting.
