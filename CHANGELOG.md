# Changelog

All notable changes to the IBM AI Racing 2026 driver are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [V3.4] — Increase V_CORNER_BONUS for higher open-section speed with preserved hairpin safety margin

### Changed (`src/torcs_v3_physics.py`)
- `PARAMS["V_CORNER_BONUS"]`: 35.0 → 45.0 km/h.

### Telemetry analysis & Rationale
- **V3.3 Run Telemetry** (`telemetry/torcs_v3_physics_20261015-110003/`):
  - Lap time: **1:52.336** (112.336 s)
  - Damage: **0.0**
  - Max speed: **191.4 km/h**
  - Status: **Keep** (first clean baseline lap).
- **Track Bottleneck Identified**:
  - **Turn 11 (distFromStart 3200–3300 m)**: Apex at 3285.8 m had the lowest speed on track (62.4 km/h), highest `|trackPos|` on track (0.802 at 3288.2 m), lowest forward visibility `track9` (6.7 m at 3283.9 m), full steering saturation (steer = 1.00 for 67 ticks), and cost 3.94 s.
  - In contrast, the hairpin at dist 2468 m was negotiated cleanly with apex speed 72.5 km/h, max `|trackPos|` 0.524, and 0 damage.
- **Expected effect of V_CORNER_BONUS = 45.0**:
  - In tight hairpins (dist 2468 m and 3285 m), side rays at ±30° are short (~10–15 m), resulting in an openness factor `min(track[4], track[14]) / 200` of only ~0.05–0.08. An increase of +10 km/h in bonus raises hairpin corner target speed by only +0.5 to +0.8 km/h, preserving the critical safety margin in the hairpins.
  - In open straights and sweeping corners (openness 0.4–1.0), corner speed increases by +4 to +10 km/h, lifting top speed on straights (up to ~215 km/h theoretical target) and carrying more momentum across open sectors.
- **Risk**: Low. Fast sweeping corners with wide geometry will be taken faster; edge protection (`TRACK_MARGIN = 0.70`, `EXTRA_CENTERING_GAIN = 1.20`) remains active if track position widens.

---

## [V3.3] — Target-speed model without straight bypass, conservative V_CORNER, proportional brake

### Race telemetry (`telemetry/torcs_v3_physics_20261015-110003/`)
- **Lap time**: **1:52.336** (112.336 s)
- **Damage**: **0.0** (0 damage accumulated across the entire lap)
- **Max speed**: **191.4 km/h** (at step 2432, distFromStart 1782.5 m)
- **Result**: **Keep** (first fully clean lap on Corkscrew).

### Crash evidence (V3.2, race 2, same hairpin)
Telemetry `telemetry/torcs_v3_physics_20261015-105228/ticks.csv` (only `track9` is logged, not the other rays):
- First damage at **step 3315**, distFromStart **2468.2 m**, curLapTime **67.68 s**; speed **95.1 → 17.3 km/h** in one tick, damage **214**.
- Steps **3255–3303**: `brake` > 0 in only **1 of 49 ticks** (0.12 at step 3255), mean `accel` ≈ **0.18**, while `track9` fell
  **19.6 m → 0.3 m** and speed only fell **116.6 → 97.5 km/h**. Steering was saturated at 1.0 from step 3276, with `trackPos`
  going 0.46 → −1.0 and `angle` 0.11 → 0.46 rad: the car ran wide because it was too fast for the radius.
- Steering is no longer the problem (no bang-bang).

### Diagnosis review
- **(a) V_CORNER too high, so target > speed: CONFIRMED (mechanism), numbers differ.**
  Back-solving the V3.2 throttle (`accel = (target − speed)/10`, undoing the cornering lift) in steps 3256–3300 gives
  `target ≈ speed + 0…4 km/h` and an implied **V_CORNER ≈ 96–100 km/h** (not 120–125). That corresponds to an aim angle of
  about 45–50° at those ticks (inside the bend), not 15–20°. The aim angle at corner entry cannot be checked because the
  CSV has no side rays. Either way, `target` stayed just above `speed` all the way to the wall, so the brake was never released
  into the `diff <= 0` branch. With V_CORNER = 55 km/h the same ticks give target ≈ 81 km/h at d = 19.6 m (116 km/h → excess 35 km/h → brake 1.0).
- **(b) STRAIGHT_DIST bypass physically unsafe: CONFIRMED as physics, REFUTED as the cause of THIS crash.**
  Stopping 230 → 55 km/h at 7 m/s²: (63.9² − 15.3²)/(2·7) ≈ **275 m**, more than the 200 m sensor range. But in the final approach
  (steps 3145–3315) `track9` never exceeded **94.3 m** (the bypass uses max of rays 8–10, so this is indicative, not proof), so it was most likely not active; the car arrived at 128–144 km/h (peak of the
  segment 2900–3100: 160.7 km/h; lap peak 205.9 km/h at step 2443, dist 1792 m). The bypass is still a latent
  hazard on the faster approaches, so it was removed as requested.

### Changed (`src/torcs_v3_physics.py`)
1. **Target speed**: STRAIGHT_DIST bypass removed; always
   `v_target = min(V_MAX, sqrt(V_CORNER² + 2·BRAKE_DECEL·d))`. `STRAIGHT_DIST` now only selects the steering aim gain.
   The 200 m sensor range caps the top speed (≈ 198 km/h with V_CORNER = 55, ≈ 211 km/h with the full bonus).
2. **V_CORNER** = `V_CORNER_MIN` + `V_CORNER_BONUS · clip(min(track[4], track[14]) / 200, 0, 1)` (rays at −30° and +30°);
   independent of the aim angle. The bonus is continuous and only large when BOTH side rays are long. Removed `V_CORNER_SHARP`, `V_CORNER_FAST`.
3. **Brake** = `clip((speed − target) / BRAKE_RANGE, 0, 1)` (BRAKE_RANGE = 15 km/h); replaces the V3.2 `-diff/25 + 0.1`
   formula and the “full brake if excess > BRAKE_DECEL·0.5 m/s” rule. ABS unchanged.

### Added (PARAMS)
- `V_CORNER_MIN = 55.0` km/h, `V_CORNER_BONUS = 35.0` km/h, `BRAKE_RANGE = 15.0` km/h.

### Added (self-test)
- **Case 6**: wall 15 m ahead at 105 km/h (rolling wheels, so ABS does not cut it) → brake > 0 (result: target 77.7 km/h, brake 1.00).
- **Case 7**: 200 m free at 230 km/h → target < V_MAX (210.7 km/h in this case, with full bonus).
- `python src/torcs_v3_physics.py --selftest` → all 7 cases pass.

### Notes / risks (not verified in a race)
- No race was run for V3.3; no lap times are claimed.
- The 200 m cap and V_CORNER_MIN = 55 will likely lower straight speed and lap time; BRAKE_DECEL = 7 m/s² is an estimate, not measured.
- `shift_gears(braking=brake > 0)` will now trigger on any speed excess, so downshifts happen more often.

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
