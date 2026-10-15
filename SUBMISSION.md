# IBM AI Racing League 2026 — Submission

---

## Participant Information

| Field | Value |
|-------|-------|
| **Name** | Alvaro Cunado |
| **Project Members** | Solo |
| **GitHub Link** | https://github.com/AlvaroCunado2003/ibm-ai-racing-2026 |
| **Video Demonstration** | VIDEO_URL |

---

## Project Description / Problem Statement

Write a Python autonomous racing agent for TORCS (The Open Racing Car Simulator) that achieves the fastest
possible lap on the Corkscrew circuit using only the 19 forward-arc distance sensors and vehicle-state
telemetry from the SCR server — no image input, no map, no pre-recorded racing line.  The first baseline lap recorded in my earlier project was 3:04.55; my previous
V2 driver ran 2:33.244 (standing start, measured today).  The final V3.12 driver achieves **1:42.868** with zero
damage and zero off-track events, a **44 % reduction** in lap time, built entirely through a systematic
iterative loop with IBM Bob and evidence from real telemetry.

---

## Enhancements

### Enhancement 1 — Physics-based braking-distance target speed

A kinematic braking model computes the maximum safe entry speed for every upcoming corner on every control
tick:

```
v_target = min(V_MAX, sqrt(V_CORNER² + 2 · BRAKE_DECEL · d))
```

where `d` is the free distance ahead (max of the three centre sensors), `V_CORNER` is a floor speed
(55 km/h) plus a bonus of up to 45 km/h when both ±30° side rays are long (wide-open bend), and
`BRAKE_DECEL = 8.5 m/s²` is calibrated against measured telemetry deceleration.  Brake pressure is
proportional to the speed excess.  This replaces the V2 fixed-speed cap and lets the car reach 203 km/h on
straights while braking precisely at each corner entry.

### Enhancement 2 — Racing-line steering with smooth aim

The driver aims toward the corner exit by computing a distance-weighted average of the three longest
track-sensor rays.  The aim contribution is blended in linearly as free distance falls below 100 m (zero
on open straights) and gated by a dead-band of 0.01 to suppress micro-corrections.  A low-pass filter
(`steer = 0.5 · prev_steer + 0.5 · raw_steer`) prevents any single noisy sensor reading from reversing
the steering sign.  This removed the bang-bang steering behind the two early crashes and cut the remaining weave from roughly 430 to 161 steering sign changes per lap.

### Enhancement 3 — ABS, traction control and speed-based gear selection

- **ABS:** reduces brake pressure proportionally if wheel speed falls more than `ABS_SLIP` km/h below
  vehicle speed (prevents lockup on hard braking).
- **Traction control:** cuts throttle proportionally if rear wheels spin faster than fronts by more than
  `TC_SLIP`.
- **Speed-based gear selection:** selects the lowest gear in [2..6] whose rpm at the current road speed is
  ≤ 9 000 rpm (`SHIFT_HIGH_RPM`), keeping the engine high in its power band for maximum corner-exit
  acceleration.  A gear-1 launch rule fires while `speedX < 10 km/h` to prevent the standing-start
  upshift bug (1 → 4 at 0 km/h).  Gear ratios are derived from median telemetry measurements
  (e.g. 6th gear = 15.89 km/h per 1 000 rpm), replacing an invented table that caused 2–4 gear drops on
  every light braking event.

---

## Use of IBM Bob and AI

IBM Bob (IBM's AI coding assistant) was the primary tool used throughout this project.  The workflow was:

1. **Human writes a structured prompt** containing the current code, recent telemetry CSVs and a diagnosis
   hypothesis.
2. **Bob reads the files**, confirms or refutes the hypothesis against the data, and proposes the smallest
   code change.
3. **Human reviews the diff** — catching sign errors and logical mistakes before any race is run.
4. **Human runs the race** in TORCS and reads back `laps.csv` and `ticks.csv`.
5. **Repeat** — the new telemetry feeds the next Bob prompt.

All 14 Bob sessions are preserved in `docs/bob-sessions/` (`.prompt.txt` + `.log` pairs).

**Cases where the human caught Bob's mistakes:**
- **Steering sign (V3.1):** Bob's initial code *added* the racing-line aim term, inverting the steering
  direction.  The human identified the TORCS sign convention (positive angle = road opens right; positive
  steer = turn left) from the baseline driver before the first race and prompted the correction.
- **Invented gear table (V3.9):** Bob's initial gear-ratio table had values up to 44 km/h per 1 000 rpm
  (2.8× the measured 15.89 km/h).  The human noticed the discrepancy in telemetry and directed Bob to
  measure the real ratios from the data.
- **Short-shifting rule (V3.11):** Bob's V3.10 rule selected the *highest* gear above `SHIFT_LOW_RPM`,
  keeping the engine at 5 500 rpm on corner exits.  The human recognised this as short-shifting and
  directed Bob to flip the logic.

**Cases where Bob corrected the human's hypotheses:**
- Bob's telemetry analysis refuted the hypothesis that the `STRAIGHT_DIST` bypass caused the second crash
  (the bypass was not active at that point; the real cause was an incorrect corner-speed estimate).
- Bob's quantitative analysis of two back-to-back runs showed the gear-hunting bug was present in both
  runs and could not explain a 13 s difference; the root cause was a steering limit-cycle, redirecting
  the V3.10–V3.12 development to fix steering stability.

The combination of Bob's analytical depth and the human's contextual knowledge of simulator physics
produced a driver that is 44 % faster than the baseline with zero damage.
