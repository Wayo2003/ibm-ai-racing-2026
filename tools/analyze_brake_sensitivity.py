"""Quantify the Turn 11 (3265-3290m) understeer loss and BRAKE_DECEL sensitivity."""
import csv, math

with open('telemetry/torcs_v3_physics_20261015-111942/ticks.csv') as f:
    rows = list(csv.DictReader(f))

def flt(r, k): return float(r[k])

# How long does the car spend below 70 km/h in Turn 11 vs the hairpin?
t11_slow = [r for r in rows if 3265 <= flt(r,'distFromStart') <= 3300 and flt(r,'curLapTime')>=0]
hp_slow  = [r for r in rows if 2455 <= flt(r,'distFromStart') <= 2480 and flt(r,'curLapTime')>=0]

print(f'Turn 11 (3265-3300m): {len(t11_slow)} ticks = {len(t11_slow)*0.02:.2f}s at mean {sum(flt(r,"speedX") for r in t11_slow)/len(t11_slow):.1f} km/h')
print(f'Hairpin  (2455-2480m): {len(hp_slow)} ticks = {len(hp_slow)*0.02:.2f}s at mean {sum(flt(r,"speedX") for r in hp_slow)/len(hp_slow):.1f} km/h')

# Track9 at Turn 11 entry (where braking starts)
t11_entry = [r for r in rows if 3080 <= flt(r,'distFromStart') <= 3200 and flt(r,'curLapTime')>=0]
max_t9_entry = max(flt(r,'track9') for r in t11_entry)
print(f'\nMax track9 in 3080-3200m: {max_t9_entry:.1f}m')

# What speed is the car doing when track9 first drops below 100m on T11 approach?
approaching = sorted([r for r in rows if 3080 <= flt(r,'distFromStart') <= 3200], key=lambda r: flt(r,'distFromStart'))
for r in approaching:
    if flt(r,'track9') < 100:
        print(f'track9 first < 100m at T11: dist={flt(r,"distFromStart"):.0f}m  spd={flt(r,"speedX"):.1f}km/h  brk={flt(r,"brake"):.2f}')
        break

# Simulate what braking distance would be needed for different V_CORNER_MIN
# at approach speed 168 km/h (V3.4 braking start speed)
approach_spd_kmh = 168.9
approach_spd_ms = approach_spd_kmh / 3.6

print('\n=== BRAKING DISTANCE SENSITIVITY (approach 168.9 km/h) ===')
for vcorner in [55, 60, 65, 70]:
    vc_ms = vcorner / 3.6
    for bd in [7.0, 8.0, 9.0]:
        d_needed = (approach_spd_ms**2 - vc_ms**2) / (2 * bd)
        print(f'  V_CORNER_MIN={vcorner}km/h  BRAKE_DECEL={bd}m/s²  => braking dist needed: {d_needed:.0f}m')

# Rolling-minimum effect on braking point
# The rolling minimum over 5 ticks means the sensor reading lags reality by ~0.1s
# At 168.9 km/h = 46.9 m/s, 0.1s = 4.7m additional distance
print(f'\nAt 168.9km/h, 5-tick lag (0.1s) = {168.9/3.6 * 0.10:.1f}m of extra braking distance')
print(f'At 130km/h,   5-tick lag (0.1s) = {130/3.6 * 0.10:.1f}m of extra braking distance')

# If BRAKE_DECEL increased to 8.5 m/s^2 (10% more optimistic), how does it change braking point?
# The model computes: v_target = sqrt(V_CORNER^2 + 2*BRAKE_DECEL*d)
# For d = 126.5m (T11 braking point), V_CORNER = 55:
d_entry_t11 = 126.5  # m, track9 at T11 braking start in V3.4
for bd in [7.0, 8.0, 8.5, 9.0]:
    vc_ms = 55/3.6
    v_target_ms = math.sqrt(vc_ms**2 + 2*bd*d_entry_t11)
    v_target_kmh = v_target_ms * 3.6
    print(f'  BRAKE_DECEL={bd}m/s²  @ d=126.5m, V_CORNER=55: v_target={v_target_kmh:.1f}km/h  (car doing 168.9km/h -> brake={max(0,(168.9-v_target_kmh)/15):.2f})')

print('\n=== WHAT IF BRAKE_DECEL = 8.5 at T11 entry? ===')
# At d=126.5m, BRAKE_DECEL=8.5:
bd = 8.5
vc_ms = 55/3.6
d = 126.5
v_target_ms = math.sqrt(vc_ms**2 + 2*bd*d)
v_target_kmh = v_target_ms * 3.6
print(f'  v_target = {v_target_kmh:.1f} km/h (vs 168.9 actual) -> brake = {max(0,(168.9-v_target_kmh)/15):.2f}')
print(f'  -> braking starts LATER -> car enters faster -> RISK of overspeed at apex')

# Forward: check where free distance = 200m (braking model cap)
# If BRAKE_DECEL=8.5: v_target at d=200m = sqrt(55^2 + 2*8.5*200*3.6^2 ... wait, need m/s
d200 = 200.0
for bd in [7.0, 8.5]:
    vc_ms = 55/3.6
    vt_ms = math.sqrt(vc_ms**2 + 2*bd*d200)
    vt_kmh = vt_ms * 3.6
    print(f'  BRAKE_DECEL={bd}: v_target @ d=200m = {vt_kmh:.1f}km/h (V_MAX cap={230})')

# Key: with BRAKE_DECEL=8.5, top speed target = sqrt(55^2 + 2*8.5*200) in m/s *3.6
# but d is in m and V is in m/s so:
print('\n=== V_MAX CALCULATION AT d=200m ===')
for bd in [7.0, 8.5]:
    vc_ms = 55/3.6
    vt_ms = math.sqrt(vc_ms**2 + 2*bd*200)
    print(f'  BRAKE_DECEL={bd}m/s²: v_target @ d=200m = {vt_ms*3.6:.1f}km/h')
