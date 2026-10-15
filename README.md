# AI Racing League – Go Full Speed with IBM Bob · Corkscrew 1:42.868, zero damage

**Solo entry — Alvaro Cunado**

---

## Problem Statement

The challenge is to write a Python AI driver for TORCS that sets the fastest possible lap on the Corkscrew
track using only the 19 forward-arc distance sensors and vehicle-state telemetry provided by the SCR
server — no image input, no map, no pre-recorded racing line.  The first baseline lap recorded in my earlier project with the reference driver
(`src/torcs_jm_par_ORIGINAL.py` family), 3:04.55, demonstrates the gap between a rule-of-thumb heuristic
controller and what physics-informed control can achieve.  The goal is to close that gap while keeping
damage at zero and remaining fully on track.

---

## Headline Results

| Driver | Version | Lap time | Damage | Off-track | Notes |
|--------|---------|----------|--------|-----------|-------|
| `torcs_jm_par_ORIGINAL.py` | Baseline | **3:04.55** | 0 | — | recorded in earlier project |
| `torcs_jm_par_V2_LOOKAHEAD.py` | V2 | **2:33.244** | 0 | 0 | standing start, measured today (`telemetry/torcs_jm_par_V2_LOOKAHEAD_20261015-102451/`) |
| `torcs_v3_FINAL.py` | **V3.12** | **1:42.868** | 0 | 0 | standing start, max 202.7 km/h, recorded on video |

> 📹 **Video demonstration:** https://youtu.be/crttMt2ngMw

The final driver is **81 seconds (44 %)** faster than the baseline and **50 seconds (33 %)** faster than
the previous V2 driver, with zero damage and zero off-track excursions.

---

## The Three Enhancements

### Enhancement 1 — Physics-based braking-distance target speed

**What it does.** On every control tick the driver reads the maximum of the three forward distance sensors
(`track[8]`, `track[9]`, `track[10]`) as the free distance `d` ahead and the openness of both ±30° side
rays to estimate how sharp the upcoming corner is.  It then computes:

```
v_target = min(V_MAX, sqrt(V_CORNER² + 2 · BRAKE_DECEL · d))
```

where `V_CORNER` is a floor speed (55 km/h) plus a bonus (up to 45 km/h) when both side rays are long —
a wide open bend.  Brake pressure is proportional to the speed excess over this target.

**Why it matters.** The V2 driver used a fixed speed cap and braked conservatively on every bend.  The
kinematic model lets the car carry full speed on open sections and only brakes where physics dictate it
must slow down to reach the apex at the target speed.  The result is dramatically higher straight-line
speed (203 km/h vs 113 km/h for V2) and precise corner entry.

### Enhancement 2 — Racing-line steering with smooth aim

**What it does.** Instead of tracking the centreline, the driver aims toward the corner exit: it computes
a distance-weighted average of the three longest track-sensor rays and steers toward that direction.  The
aim contribution is blended in linearly as the car approaches a corner (active only when `d < 100 m`) and
fades to zero on open straights.  A small dead-band suppresses micro-corrections.  A low-pass filter
(`steer = 0.5·prev + 0.5·raw`) prevents single noisy sensor ticks from reversing the steering command.

**Why it matters.** Two early crashes and a later repeatability failure were all caused by bang-bang steering
oscillation: the unfiltered single-longest-ray selector jumped between adjacent sensors every few ticks and
saturated the steering output.  The smooth, blended aim greatly reduces the oscillation (steering sign changes fell from roughly 430 to 161 per lap in V3.12) while still enabling the
car to rotate toward the corner exit.

### Enhancement 3 — ABS, traction control and speed-based gear selection

**What it does.**
- **ABS:** if wheel speed falls more than `ABS_SLIP` km/h below vehicle speed under braking, brake pressure
  is reduced proportionally (no lockup).
- **Traction control:** if rear wheels spin faster than the fronts by more than `TC_SLIP`, throttle is cut
  proportionally.
- **Speed-based gear selection:** on each eligible tick the driver selects the lowest gear in [2..6] whose
  engine rpm at the current road speed is ≤ `SHIFT_HIGH_RPM` (9 000 rpm), keeping the engine high in its
  power band.  A gear-1 launch rule fires while `speedX < 10 km/h`.

**Why it matters.** RPM-threshold shifting failed badly in two independent ways: the V3.2 invented gear
table caused 2–4 gear drops under any light braking (gear 6 → 2 at 100 km/h), and the V3.10 highest-gear
rule short-shifted the engine to 5 500 rpm on every corner exit, costing acceleration.  Speed-based
selection with a measured gear table (from telemetry) solves both problems.

---

## How IBM Bob Was Used

### The iterative loop

```
Bob prompt (read files + hypothesis) → Bob proposes code change
   → human code review → apply to src/torcs_v3_physics.py
   → race on TORCS Corkscrew → read telemetry/*/laps.csv + ticks.csv
   → Bob reads new telemetry → next prompt
```

Every version was proposed by Bob after reading the actual telemetry from the previous run.  Bob never
ran the simulator; the human ran each race and fed the resulting CSV files back to Bob.

### Version history (from CHANGELOG.md)

| Version | Change | Result | Keep / Revert |
|---------|--------|--------|---------------|
| V3.0 | Initial physics driver (braking model, racing-line steer, ABS/TC, RPM gear shift) | not run | — |
| V3.1 | **Steering sign fix (human review):** aim term was *added* instead of *subtracted*, inverting direction | not run | — |
| V3.2 | Smooth aim (weighted avg of 3 rays), low-pass filter, rolling-min free-distance, BRAKE_DECEL 9→7, braking downshift | not run | — |
| V3.3 | Remove STRAIGHT_DIST bypass from target-speed; V_CORNER = V_CORNER_MIN + bonus; proportional brake | **1:52.336**, 0 damage | KEEP |
| V3.4 | `V_CORNER_BONUS` 35 → 45 km/h | **1:47.106**, 0 damage | KEEP |
| V3.5 | `BRAKE_DECEL` 7.0 → 8.5 m/s² | **1:42.592**, 0 damage | KEEP |
| V3.6 | `V_CORNER_MIN` 55 → 50 km/h | **1:45.684**, 0 damage | **REVERT** (3.1 s slower) |
| V3.7 | Revert V3.6; `STEER_SMOOTH` 0.5 → 0.3 | **1:43.842**, 0 damage | **REVERT** (1.25 s slower) |
| V3.8 | `BRAKE_DECEL` 8.5 → 9.5 m/s² | **1:42.064**, 0 damage, **1 off-track** | **REVERT** (off-track event) |
| V3.9 | Fix gear table (measured from telemetry); braking downshift 1 gear, brake > 0.5 only | **1:57.840**, 0 damage | REVERT basis for V3.10 |
| V3.10 | Speed-based gear selection; fix standing-start launch bug | not run independently | — |
| V3.11 | Lowest eligible gear rule (keep engine high in power band) | **1:44.878**, 0 damage; **CRASH** on repeat | → V3.12 |
| V3.12 | Distance-blended aim gain; steering dead-band; reduces weave (~430 -> 161 sign flips/lap) | **1:42.868**, 0 damage, 0 off-track | **KEEP — FINAL** |

### Where the human corrected Bob

**1. Steering sign bug (V3.1 — human code review before first race).**
In `calculate_steering()`, Bob generated `steer = (angle + aim_gain · aim_angle_rad − centering) / STEER_LOCK`.
In TORCS/SCR a positive track sensor angle means the road opens to the *right*, while a positive steer
value turns *left*.  Adding the aim term therefore steered the car away from every corner exit.  The human
identified the sign error from the baseline driver's convention (`src/snakeoil3_gym_BASELINE.py`) before
any race was run and prompted Bob to subtract the term.  Without this fix the car would have hit the outer
wall on the first competitive lap.

**2. Invented gear table (V3.9 diagnosis — human hypothesis).**
The V3.2 braking-downshift rule used a `_GEAR_SPEED_KMH_PER_1000RPM` table with values up to 44 km/h per
1 000 rpm.  The human observed 6th gear at ~161 km/h showing ~9 300 rpm in telemetry — implying ~17 km/h
per 1 000 rpm — and raised this as a hypothesis.  Bob confirmed it with telemetry analysis: the measured
median was 15.89 km/h per 1 000 rpm in 6th (old table: 44 — a **2.8× error**), causing 2–4 gear drops on
every light braking event and explaining the gear-hunting instability.

**3. Short-shifting rule (V3.11 — human code review).**
Bob's V3.10 gear rule selected the *highest* gear whose rpm was ≥ `SHIFT_LOW_RPM` (5 500), meaning the
engine ran near the bottom of its power band after every corner exit.  The human identified this as
short-shifting and prompted the V3.11 correction: select the *lowest* gear whose rpm is ≤ `SHIFT_HIGH_RPM`
(9 000), keeping the engine high in the power band for maximum acceleration.

### Where Bob corrected the human's hypotheses

**Crash at distFromStart 2468 m (V3.2 → V3.3 analysis).**
The human hypothesised that the `STRAIGHT_DIST` bypass (`target = V_MAX` when `d ≥ 100 m`) was the root
cause of the second crash because stopping from 230 km/h at 7 m/s² requires ~275 m.  Bob confirmed the
bypass was a latent hazard but refuted it as the cause of *this* crash: in steps 3 145–3 315 the forward
sensor `track9` never exceeded 94.3 m, so the bypass was almost certainly not active.  The actual cause
was that `V_CORNER` was derived from the aim angle and came out ~100 km/h — close to the actual speed —
so the brake term stayed near zero while the car ran straight into the wall.

**Steering oscillation diagnosis (V3.9 telemetry).**
The human attributed the 13 s gap between two supposedly identical runs to the gear-hunting bug.  Bob's
analysis showed the gear bug was present in *both* runs (both had ~57 downshifts and 28–37 multi-gear
drops in the first 2 000 m) and therefore could not explain the 13 s difference.  The real cause was a
steering limit-cycle oscillation in the second run (184 vs 5 steering sign flips, 30 km/h lower mean speed
after 2 000 m) that could run independently of gear changes.  This focused V3.10–V3.12 on the steering
stability problem.

---

## Setup and Run Commands

### Prerequisites

- TORCS with the SCR patch installed and configured for Practice mode on track **corkscrew**.
- A Python virtual environment at `C:\torcs-env\` with `snakeoil3_gym` dependencies installed.

### Start TORCS

Open TORCS → Race → Practice → select track **Corkscrew** → add `scr_server` as the robot → Start.

### Run the final driver (one lap)

```powershell
C:\torcs-env\Scripts\python.exe tools\race.py src\torcs_v3_FINAL.py --laps 1
```

Telemetry is written to `telemetry/<timestamp>/laps.csv` and `ticks.csv` automatically.

### Replay self-tests (no TORCS required)

```powershell
C:\torcs-env\Scripts\python.exe src\torcs_v3_physics.py --selftest
```

All 11 cases should print `PASS`.

---

## Repository Structure

```
ibm-ai-racing-2026/
├── src/
│   ├── torcs_v3_FINAL.py          # Final submitted driver (V3.12)
│   ├── torcs_v3_physics.py        # Development driver (V3.12, identical to FINAL)
│   ├── torcs_jm_par_V2_LOOKAHEAD.py  # Previous best V2 driver
│   ├── torcs_jm_par_ORIGINAL.py   # Original baseline driver
│   └── snakeoil3_gym_BASELINE.py  # SCR sensor reference (read-only)
├── tools/
│   ├── race.py                    # Race runner and telemetry logger
│   └── analyze_*.py               # Offline telemetry analysis scripts
├── telemetry/                     # One directory per race run (laps.csv + ticks.csv)
├── evidence/
│   ├── final_lap_laps.csv         # Official final lap: 1:42.868, 0 damage, 0 off-track
│   └── final_lap_ticks.csv        # Per-tick data for the official lap
├── docs/
│   ├── bob-sessions/              # 14 Bob prompt + log pairs (01 – 14)
│   └── BOB_PROMPTS.md
├── livery/
│   └── car1-trb1.rgb              # Custom livery (car physics unchanged)
├── CHANGELOG.md                   # Full version history with telemetry references
├── README.md                      # This file
└── SUBMISSION.md                  # Organiser submission template
```

---

## Livery Note

A custom livery is provided at [`livery/car1-trb1.rgb`](livery/car1-trb1.rgb).  No car physics, mass,
tyre model or engine parameters were modified; only the Python control logic changes between versions.

---

## Limitations and Next Steps

**Limitations**
- The braking model uses a single scalar deceleration parameter (`BRAKE_DECEL = 8.5 m/s²`); lateral load
  transfer and combined-slip tyre behaviour are not modelled.
- The racing line is emergent from the sensor-aim heuristic, not a pre-computed optimal line.
- `V_CORNER_BONUS` uses only the ±30° side rays; narrower chicanes that appear open at ±30° but tight at
  ±15° are not handled.
- Repeatability is not perfect: the same code produced 1:42.592 and 1:55.606 in two consecutive runs
  before V3.9 fixed the gear table; environmental non-determinism in TORCS cannot be fully excluded.
- Only Corkscrew has been tested; parameter values are not validated on other tracks.

**Next steps**
- Add a lap-time predictor that uses segment splits to identify the next highest-gain corner automatically.
- Replace the scalar `BRAKE_DECEL` with a speed-dependent grip curve derived from measured deceleration data.
- Extend `V_CORNER_BONUS` to use a wider set of side rays for narrower-corridor detection.
- Validate on at least one other track before generalising parameters.
