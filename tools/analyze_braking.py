"""
Measure SUSTAINED / EFFECTIVE deceleration over multi-tick windows at the
V3.5 hairpin and T11 braking zones.

The per-tick values are noisy (ABS cycling, gear changes).
We instead measure:
  - entry speed  (first tick in zone with any brake)
  - exit speed   (last tick with any brake, before accel resumes)
  - distance covered
  - effective_decel = (v_entry^2 - v_exit^2) / (2 * distance)

Also reports the instantaneous window (every 5-tick rolling window)
at brake >= 0.2 to get a cleaner picture.
"""
import csv
import math

TICKS_CSV = "telemetry/torcs_v3_physics_20261015-112700/ticks.csv"

rows = []
with open(TICKS_CSV, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append({k: float(v) if v not in (None, "") else 0.0 for k, v in row.items()})

def effective_decel(rows, d_start, d_end, brake_entry_thresh=0.05, label="zone"):
    """Measure effective deceleration over the entire braking ramp."""
    zone = [r for r in rows if d_start <= r["distFromStart"] <= d_end and r["brake"] >= brake_entry_thresh]
    if len(zone) < 2:
        print(f"  {label}: not enough ticks")
        return

    v_entry = zone[0]["speedX"]  # km/h
    v_exit  = zone[-1]["speedX"]  # km/h
    d_entry = zone[0]["distFromStart"]
    d_exit  = zone[-1]["distFromStart"]
    dist    = d_exit - d_entry

    if dist <= 0:
        print(f"  {label}: zero distance")
        return

    # kinematics: v_exit^2 = v_entry^2 - 2*a*d  => a = (v_entry^2 - v_exit^2)/(2d)
    v_e = v_entry / 3.6
    v_x = v_exit  / 3.6
    eff_decel = (v_e**2 - v_x**2) / (2 * dist)

    max_brake = max(r["brake"] for r in zone)
    min_brake = min(r["brake"] for r in zone)
    mean_brake = sum(r["brake"] for r in zone) / len(zone)
    n_heavy = sum(1 for r in zone if r["brake"] >= 0.5)

    print(f"  {label}:")
    print(f"    entry  d={d_entry:.1f} m,  speedX={v_entry:.2f} km/h")
    print(f"    exit   d={d_exit:.1f} m,  speedX={v_exit:.2f} km/h")
    print(f"    dist={dist:.1f} m,  brake: mean={mean_brake:.3f}  max={max_brake:.3f}  min={min_brake:.3f}  n_heavy(>=0.5)={n_heavy}")
    print(f"    >>> EFFECTIVE DECEL = {eff_decel:.3f} m/s^2")
    return eff_decel

def rolling_window_decel(rows, d_start, d_end, window=5, brake_thresh=0.15):
    """Sliding window of N ticks to estimate instantaneous decel during braking."""
    zone = [(r["distFromStart"], r["speedX"], r["brake"])
            for r in rows if d_start <= r["distFromStart"] <= d_end and r["brake"] >= brake_thresh]
    if len(zone) < window:
        return []
    results = []
    for i in range(len(zone) - window + 1):
        seg = zone[i:i+window]
        d0, v0, _ = seg[0]
        d1, v1, _ = seg[-1]
        if d1 - d0 <= 0:
            continue
        mean_brake = sum(s[2] for s in seg) / window
        v0_ms = v0 / 3.6
        v1_ms = v1 / 3.6
        dist = d1 - d0
        dec = (v0_ms**2 - v1_ms**2) / (2 * dist)
        results.append((d0, v0, mean_brake, dec))
    return results

print("=" * 60)
print("V3.5 BRAKING ANALYSIS — effective / sustained decel")
print("=" * 60)

print()
print("--- HAIRPIN (~2468 m) — Phase 1: heavy pre-braking (2229-2241 m) ---")
hp1 = effective_decel(rows, 2229, 2241, brake_entry_thresh=0.5, label="Hairpin Phase-1 (brake>=0.5)")

print()
print("--- HAIRPIN (~2468 m) — Phase 2: full ramp to apex (2229-2450 m) ---")
hp2 = effective_decel(rows, 2229, 2450, brake_entry_thresh=0.05, label="Hairpin full-ramp")

print()
print("--- TURN 11 (~3287 m) — full ramp (3140-3260 m) ---")
t11 = effective_decel(rows, 3140, 3260, brake_entry_thresh=0.02, label="T11 full ramp")

print()
print("--- TURN 11 — rolling 5-tick windows (brake >= 0.15) ---")
t11_roll = rolling_window_decel(rows, 3140, 3260, window=5, brake_thresh=0.15)
if t11_roll:
    t11_roll_sorted = sorted(t11_roll, key=lambda x: x[3], reverse=True)
    print("  Top 5 windows (highest decel):")
    for d, v, b, dec in t11_roll_sorted[:5]:
        print(f"    d={d:.1f}  speedX={v:.2f} km/h  mean_brake={b:.3f}  decel={dec:.3f} m/s^2")
    print("  Full window profile (sorted by distance):")
    for d, v, b, dec in sorted(t11_roll, key=lambda x: x[0]):
        if dec > 3.0:  # only show significant decel
            print(f"    d={d:.1f}  speedX={v:.2f} km/h  mean_brake={b:.3f}  decel={dec:.3f} m/s^2")

print()
print("--- HAIRPIN — rolling 5-tick windows (brake >= 0.2) ---")
hp_roll = rolling_window_decel(rows, 2229, 2250, window=5, brake_thresh=0.2)
if hp_roll:
    hp_roll_sorted = sorted(hp_roll, key=lambda x: x[3], reverse=True)
    print("  Top 5 windows (highest decel):")
    for d, v, b, dec in hp_roll_sorted[:5]:
        print(f"    d={d:.1f}  speedX={v:.2f} km/h  mean_brake={b:.3f}  decel={dec:.3f} m/s^2")

print()
print("=" * 60)
print("SAFETY EVALUATION: BRAKE_DECEL 9.5 m/s^2")
print("=" * 60)

# Key numbers from the analysis
# Use measured effective decel from the ramp (the model number that matters)
print()
print("Key question: does the car ever actually achieve >= 9.5 m/s^2 sustained?")
print("If the measured peak sustained decel is < 9.5, then 9.5 overstates grip.")
print()

# Summarize
if hp1 is not None:
    print(f"  Hairpin Phase-1 (2 heavy ticks, brake 1.0/0.97): {hp1:.3f} m/s^2 effective")
if hp2 is not None:
    print(f"  Hairpin full ramp (brake 0.05-1.0):              {hp2:.3f} m/s^2 effective")
if t11 is not None:
    print(f"  T11 full ramp (brake 0.02-0.24):                 {t11:.3f} m/s^2 effective")

print()
print("  BRAKE_DECEL = 8.5 m/s^2 is the model parameter.  The car's own")
print("  target-speed formula uses this to time the braking point.  The")
print("  ACTUAL decel achieved measures what the physics engine delivers.")
