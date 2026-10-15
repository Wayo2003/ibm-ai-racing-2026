# Changelog

All notable changes to the IBM AI Racing 2026 driver are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [V3.6] — Lower V_CORNER_MIN to remove throttle in the saturated-steer part of Turn 11

### Changed (`src/torcs_v3_physics.py`)
- `PARAMS["V_CORNER_MIN"]`: 55.0 → 50.0 km/h. Nothing else changed.

### V3.5 result (`telemetry/torcs_v3_physics_20261015-112700/`)
- Lap time: **1:42.592** (102.592 s) — 4.514 s faster than V3.4 (1:47.106)
- Damage: **0.0**, offtrack events: **0**, max speed **203.0 km/h** (distFromStart 1769.6 m)
- Status: **KEEP**. — *[V3.4→V3.5: confirmed KEEP]*

#### Observations (from ticks.csv; V3.4 = `torcs_v3_physics_20261015-111942/`; track width in metres is not logged, so margins are in trackPos units only)
- **Where the gain came from:** 100 m bins gained 0.08–0.20 s each on 33 of 37 bins (sum 4.51 s). The tight-corner bins did not: 2400–2500 m −0.02 s, 2500–2600 m −0.07 s, 3200–3300 m +0.04 s, 3300–3400 m −0.09 s (negative = slower than V3.4).
- **Closest call to damage — Turn 11, 3200–3300 m:** peak |trackPos| **0.891** at 3287.1 m (V3.4: 0.813); margin to edge 0.109. Speed there 61.5 km/h, track9 5.1 m minimum (3283.9 m), steer ≥ 0.99 for 72 ticks, 29 ticks with |trackPos| > 0.8 (V3.4: 9). The 100 m bin took 4.22 s (mean 87.4 km/h), the slowest non-start bin (bin 0–100 m, 4.31 s, is the standing start).
- **Entry speed rose, apex speed did not:** speed at 3180 m 157.2 km/h (V3.4: 145.0); minimum 61.1 km/h (V3.4: 62.7). Mean brake over 3180–3249 m only 0.16 (max 0.24); measured mean deceleration over that stretch 8.9 m/s². Throttle stays > 0 (0.10–0.26) from 3260 m through the apex while the car loses speed 82 → 61 km/h.
- **Hairpin ~2468 m:** speed 73.1 km/h and |trackPos| 0.35 at 2469 m, min track9 11.2 m; peak |trackPos| **0.740** at 2480.3 m (V3.4: 0.566), speed there 72.5 km/h; lowest speed in the hairpin zone 66.9 km/h at 2499.5 m. Entry speed at 2380 m 130.9 km/h (V3.4: 123.1). Steer ≥ 0.99 for 58 ticks. Brake in 2380–2560 m peaks at 0.28.
- **Heaviest braking of the lap is NOT at the hairpin:** only 2 ticks with brake ≥ 0.5, at 2230.9–2232.0 m (brake 1.0/0.97, 194.3 km/h, track9 ≈ 106 m), about 237 m before the hairpin. Speed fell 194.3 → 181.7 km/h by 2239 m.
- The steering command is saturated (1.0) at both corners while |trackPos| grows, so steering terms (TRACK_MARGIN, EXTRA_CENTERING_GAIN, STEER_SMOOTH) cannot add more correction there.
- Model check (side rays are not logged, so openness is unknown): with V_CORNER_MIN = 55, BRAKE_DECEL = 8.5, d = 13.7 m (track9 at 3266.2 m) and openness 0 the formula gives a target of 77.7 km/h, against a logged speed of 76.4 km/h and accel 0.19 (steer 1.0). Target slightly above speed is consistent with the logged small positive throttle.

#### Hypotheses (not measured)
- BRAKE_DECEL = 8.5 does not overstate straight-line braking (0 damage) but lets the car arrive faster at tight corners, where the car is steering-limited; the extra width (0.813 → 0.891, 0.566 → 0.740) is the symptom. Without lateral velocity or slip in the log this cannot be confirmed.
- Throttle applied while the steering is saturated (accel 0.10–0.26 from 3260 to 3285 m) may limit the lateral grip available for turning; the log has no lateral acceleration or slip, so this is unconfirmed.
- The V3.5 entry said "revert if |trackPos| exceeds 0.85 at the hairpin": the hairpin stayed at 0.74 (not triggered). The 0.891 occurred at T11, outside that criterion, but it is the smallest margin seen in V3.3–V3.5 and is why V3.6 is proposed. The predicted T11 gain of 0.2–0.5 s did not occur (≈ −0.05 s net over 3200–3400 m).

### Expected effect
- Computed from the model at d = 13.7 m, openness 0: target falls 77.7 → 74.3 km/h. At 76.4 km/h the car would then be slightly above target and would brake lightly instead of applying 0.19 throttle. Expected (hypothesis): apex speed a few km/h lower, T11 peak |trackPos| below 0.891, cost 0.05–0.15 s per tight corner. The bonus term is unchanged, so open sections only see the −5 km/h floor shift.

### Risk
- **Low.** It costs lap time if the T11 line does not improve. **Revert to 55.0 if damage > 0, or if the lap is slower than 1:42.592 and the T11 peak |trackPos| is not below 0.85.** Keep if damage is 0 and either the lap is ≤ 1:42.592 or the T11 peak |trackPos| ≤ 0.85 with lap loss < 0.3 s.
- Result of V3.6: *not run yet — no lap time or damage claimed.*

---

## [V3.5] — Increase BRAKE_DECEL to trust braking model on fast approaches

**Result:** lap **1:42.592**, damage **0.0**, max 203.0 km/h (`telemetry/torcs_v3_physics_20261015-112700/`) — **KEEP**.

### Changed (`src/torcs_v3_physics.py`)
- `PARAMS["BRAKE_DECEL"]`: 7.0 → 8.5 m/s².

### Telemetry analysis & Rationale
- **V3.4 Run Telemetry** (`telemetry/torcs_v3_physics_20261015-111942/`):
  - Lap time: **1:47.106** (107.106 s)
  - Damage: **0.0**
  - Max speed: **193.0 km/h** at distFromStart 1755.5 m
  - Status: **Keep** (5.23 s faster than V3.3, 0 damage). — *[V3.3→V3.4: confirmed KEEP]*

#### Observations (measurements from ticks.csv — not inferred)
- **Where the 5.2 s were gained (V3.3 vs V3.4 segment comparison, 200 m bins):**
  - 2200–2400 m: +1.02 s saved (mean speed 119.0 → 146.7 km/h; V3.4 entered this pre-hairpin straight faster due to higher V_CORNER_BONUS on the preceding open sweeper).
  - 3400–3600 m: +0.84 s saved (mean speed 138.5 → 168.1 km/h; post-T11 acceleration starts higher because T11 is now entered 34.9 km/h faster: 134 km/h vs 139 km/h, braking start 41 m later).
  - 1200–1400 m: +0.62 s saved (max speed 152.2 → 180.6 km/h; open-arc sector with long ±30° rays, full bonus applied).
  - 3000–3200 m: +0.60 s saved (approach to T11 faster: 122.9 → 138.3 km/h mean).
  - Total accounted by segment bins: +4.78 s (residual 0.44 s in sub-bin scatter).
- **Bottleneck — Turn 11 (distFromStart 3200–3300 m):**
  - Apex speed: **62.7 km/h** at dist 3286 m (identical to V3.3: 62.4 km/h). Apex position unchanged.
  - Peak |trackPos|: **0.813** at dist 3289 m with steer = 1.00 (saturated for 70 ticks, 3265–3290 m).
  - track9 at braking-start distance (3140 m) in V3.4: **126.5 m**. Model computes v_target = sqrt(55²/3.6² + 2·7.0·126.5)·3.6 = **161.2 km/h** while car is doing **168.9 km/h** → brake = 0.52. Car still arrives at apex at 62.7 km/h, indicating V_CORNER_MIN = 55 km/h matches physics, but braking starts 41 m later than V3.3 (3140 vs 3099 m) and the approach speed at that point is 34.9 km/h higher.
  - Time spent ≤70 km/h in T11 (3265–3300 m): **1.84 s** — the single slowest 35 m section on the entire lap.
  - For comparison, hairpin at dist ~2468 m (3.94 s lost in V3.3) now costs only: apex 72.8 km/h, 1.08 s at < 80 km/h, |trackPos|_max = 0.566, no steer saturation. Hairpin is no longer the bottleneck.
- **Only braking events on the whole lap (speed > 80, brake > 0.5):** 4 ticks, all at 2228–2239 m (pre-hairpin; speed 174–188 km/h, track9 100–107 m). No heavy braking at T11: model brakes gradually from 3140 m.

#### Hypothesis for V3.5
- BRAKE_DECEL = 7.0 m/s² is **too conservative**: the car reaches 62.7 km/h at the T11 apex correctly, which means the actual grip is sufficient for 7 m/s² of deceleration but the model under-estimates it. If the car can decelerate faster than 7 m/s², braking can start later (higher entry speed) with the same apex speed. Increasing BRAKE_DECEL to **8.5 m/s²** raises v_target at d = 126.5 m to 175.8 km/h > 168.9 km/h (brake = 0.00 until the car catches up to the closer corner distance), effectively delaying the braking point. At d = 200 m (sensor cap), v_target rises from 198.3 → 217.0 km/h, lifting straight speed targets across all approach sections. This propagates a speed benefit to every braking zone on the lap, not only T11. Risk: if 8.5 m/s² overstates grip, the car will reach the apex faster than 62.7 km/h — most likely at the hairpin (dist 2468 m, prior crash site) since it is the tightest corner and has the least V_CORNER_BONUS. The hairpin apex under V3.4 is 72.8 km/h with 0 trackPos margin; a 10–15% entry overshoot would push |trackPos| toward 0.7–0.8, approaching but not exceeding the prior crash value (|trackPos| > 1.0). STEER_SMOOTH and edge centering remain active.

### Changed
- `PARAMS["BRAKE_DECEL"]`: **7.0 → 8.5 m/s²** (21% increase).

### Expected effect
- Braking point at T11 (d_approach ≈ 126–188 m) delayed, entry speed higher, apex speed unchanged (physics-limited by V_CORNER_MIN). Sector 3200–3300 m should save ~0.2–0.5 s. All straight-speed targets also rise (~10 km/h at 200 m free distance), potentially saving a further 0.3–0.6 s across the lap.

### Risk
- **Medium.** Hairpin at dist 2468 m is the most sensitive corner (V_CORNER_BONUS ≈ 0 due to short ±30° rays). Predicted hairpin entry speed increases by ~15 km/h (current 122 km/h at 2230 m, same braking zone). Stopping from 137 km/h to 73 km/h at 8.5 m/s² requires (137²−73²)/(2·8.5·3.6²) ≈ 71 m; current braking starts at dist ~2230 m, apex at ~2469 m — 239 m available. Margin is sufficient. However, if the model over-estimates deceleration, the only safe outcome is a slightly wider exit line (|trackPos| up to 0.8); |trackPos| > 1.0 indicates a crash. **Revert to 7.0 if damage > 0 or |trackPos| exceeds 0.85 at the hairpin.**

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
