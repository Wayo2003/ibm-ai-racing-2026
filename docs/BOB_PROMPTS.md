# IBM Bob prompts used in this project (in order)

## 1 — Build the V3 driver (Agent mode)

```
Read src/torcs_jm_par_V2_LOOKAHEAD.py (my current best driver: 2:27.28 on Corkscrew, zero damage),
tools/race.py (the runner that calls drive_v3(c) and logs telemetry) and the SnakeOil sensor list in
src/snakeoil3_gym_BASELINE.py. Do NOT modify the V2 file, the baseline or tools/race.py.

Create src/torcs_v3_physics.py with a function drive_v3(c) and three enhancements over V2. The car
model, its physics and the livery must not change: only the Python control logic.

ENHANCEMENT 1 — Physics-based target speed (braking-distance model)
- The 19 track range sensors are at angles [-90,-75,-60,-45,-30,-20,-15,-10,-5,0,5,10,15,20,30,45,60,75,90]
  degrees (track[9] is straight ahead, values up to 200 m, -1 when off track).
- Free distance ahead d = max(track[8], track[9], track[10]).
- Estimate the corner sharpness from the direction of the longest ray (see enhancement 2): the
  bigger its angle, the sharper the corner, the lower the corner speed V_CORNER (interpolate between
  V_CORNER_SHARP and V_CORNER_FAST).
- Target speed = min(V_MAX, sqrt(V_CORNER^2 + 2 * BRAKE_DECEL * d)) with speeds converted to m/s, so
  the car only brakes when it really needs to in order to reach the corner at V_CORNER.
- If d >= STRAIGHT_DIST treat it as a straight: target = V_MAX.

ENHANCEMENT 2 — Racing line steering (aim at the corner exit)
- Find the sensor with the maximum distance; its angle is the "open road" direction.
- steer = (STEER_AIM * aim_angle_rad + angle - CENTERING_GAIN * trackPos) / STEER_LOCK, with
  STEER_LOCK = 0.366 rad, clipped to [-1, 1]. On long straights (d >= STRAIGHT_DIST) reduce STEER_AIM
  to avoid weaving. Keep the car inside |trackPos| < TRACK_MARGIN by adding extra centering when it
  gets close to the edge.

ENHANCEMENT 3 — ABS + traction control + smoother throttle (protects zero damage)
- ABS: if braking and the wheel speed (mean of wheelSpinVel * wheel radius 0.3179 m, converted to
  km/h) is more than ABS_SLIP km/h below speedX, reduce brake proportionally (never below 0).
- Traction control: if rear wheels spin faster than front by more than TC_SLIP, cut throttle
  proportionally instead of a fixed -0.15.
- Throttle: full throttle when below target by > 10 km/h, proportional otherwise; no throttle while
  braking. Lift throttle when |steer| is large at high speed.
- Gears: rpm-based up/down shifting for gears 1..6 with GEAR_UP_RPM / GEAR_DOWN_RPM, plus a minimum
  hold time between shifts to avoid oscillation.

Keep the V2 recovery manoeuvre for |trackPos| > 1.
Put EVERY tunable value (V_MAX, V_CORNER_SHARP, V_CORNER_FAST, BRAKE_DECEL, STRAIGHT_DIST, STEER_AIM,
CENTERING_GAIN, TRACK_MARGIN, ABS_SLIP, TC_SLIP, GEAR_UP_RPM, GEAR_DOWN_RPM) in one PARAMS dict at the
top, with conservative starting values (V_MAX 230 km/h, BRAKE_DECEL 9 m/s^2) and a comment on each.
Add a __main__ block like V2's so it can also run standalone.
Explain the logic in plain English, then run `python -c "import ast; ast.parse(open('src/torcs_v3_physics.py').read())"`
to check syntax. Do not run the race and do not invent lap times.
```

## 2 — Data-driven tuning loop (Agent mode, repeated after every lap)

```
I ran src/torcs_v3_physics.py on Corkscrew. The telemetry is in telemetry/<run folder>/ (laps.csv
and ticks.csv). Read them. Report the lap time and damage, and find the ONE section of the track
(distFromStart range) that costs the most time or comes closest to damage (low speed vs. long
free distance, |trackPos| near 1, heavy braking, damage increase). Distinguish observations from
hypotheses. Propose ONE parameter change in PARAMS with its expected effect and risk, apply only
that change, append the run to CHANGELOG.md (version, change, lap time, damage, keep/revert), and
show the diff. Do not invent measurements.
```
