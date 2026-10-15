# Changelog

All notable changes to the IBM AI Racing 2026 driver are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
