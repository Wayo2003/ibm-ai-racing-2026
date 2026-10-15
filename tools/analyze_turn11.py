"""Detailed analysis of Turn 11 (3200-3300m) braking profile in V3.4 vs V3.3."""
import csv, math

def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def flt(r, k): return float(r[k])

rows34 = load('telemetry/torcs_v3_physics_20261015-111942/ticks.csv')
rows33 = load('telemetry/torcs_v3_physics_20261015-110003/ticks.csv')

# Extract Turn 11 entry zone (3080-3300m) for both runs
def segment(rows, d_start, d_end):
    return [(flt(r,'distFromStart'), flt(r,'speedX'), flt(r,'brake'), flt(r,'accel'),
             flt(r,'track9'), flt(r,'trackPos'), flt(r,'curLapTime'))
            for r in rows if d_start <= flt(r,'distFromStart') <= d_end and flt(r,'curLapTime') >= 0]

t11_34 = segment(rows34, 3080, 3310)
t11_33 = segment(rows33, 3080, 3310)

print('=== TURN 11 ENTRY (3080-3310m): braking point comparison ===')
print(f'{"dist":>7}  {"V3.3 spd":>9}  {"V3.4 spd":>9}  {"V3.3 brk":>9}  {"V3.4 brk":>9}  {"V3.3 t9":>8}  {"V3.4 t9":>8}')

# Align by distance: sample every ~10m
dist_points = range(3080, 3310, 10)
def nearest(seg, d):
    if not seg: return None
    return min(seg, key=lambda x: abs(x[0]-d))

for d in dist_points:
    r33 = nearest(t11_33, d)
    r34 = nearest(t11_34, d)
    if r33 and r34:
        print(f'{d:7d}  {r33[1]:9.1f}  {r34[1]:9.1f}  {r33[2]:9.2f}  {r34[2]:9.2f}  {r33[4]:8.1f}  {r34[4]:8.1f}')

# Find apex speed (minimum in 3270-3295m)
apex34 = min(t11_34, key=lambda x: x[1] if 3270 <= x[0] <= 3300 else 9999)
apex33 = min(t11_33, key=lambda x: x[1] if 3270 <= x[0] <= 3300 else 9999)
print(f'\nV3.3 apex speed: {apex33[1]:.1f} km/h at dist {apex33[0]:.0f}m (lapTime {apex33[6]:.2f}s)')
print(f'V3.4 apex speed: {apex34[1]:.1f} km/h at dist {apex34[0]:.0f}m (lapTime {apex34[6]:.2f}s)')

# When does brake first activate on T11 approach?
def first_brake(seg, d_start):
    for r in seg:
        if r[0] >= d_start and r[2] > 0.05:
            return r
    return None

bp33 = first_brake(t11_33, 3080)
bp34 = first_brake(t11_34, 3080)
if bp33: print(f'V3.3 braking starts: dist={bp33[0]:.0f}m  speed={bp33[1]:.1f}km/h  t9={bp33[4]:.1f}m')
if bp34: print(f'V3.4 braking starts: dist={bp34[0]:.0f}m  speed={bp34[1]:.1f}km/h  t9={bp34[4]:.1f}m')

# Compute brake_decel-implied stopping distance at apex speed
for label, spd in [('V3.3', apex33[1]), ('V3.4', apex34[1])]:
    vmax_ms = 230/3.6
    vcorner_ms = 55/3.6  # V_CORNER_MIN (no bonus since T11 side rays are short)
    brake_decel = 7.0
    d_stop = (vmax_ms**2 - vcorner_ms**2) / (2 * brake_decel)
    print(f'{label}: theoretical stop from 230km/h to 55km/h at 7m/s²: {d_stop:.0f}m')

# Analyze sector 3000-3200 time difference more carefully (big gain bucket)
s3000_34 = segment(rows34, 3000, 3200)
s3000_33 = segment(rows33, 3000, 3200)
print(f'\n=== SECTOR 3000-3200m ===')
print(f'V3.3: {len(s3000_33)} ticks, time = {len(s3000_33)*0.02:.2f}s, mean speed = {sum(r[1] for r in s3000_33)/len(s3000_33):.1f} km/h')
print(f'V3.4: {len(s3000_34)} ticks, time = {len(s3000_34)*0.02:.2f}s, mean speed = {sum(r[1] for r in s3000_34)/len(s3000_34):.1f} km/h')
print(f'Time saved: {(len(s3000_33)-len(s3000_34))*0.02:.2f}s')

# Sector 3400-3600 time difference
s3400_34 = segment(rows34, 3400, 3598)
s3400_33 = segment(rows33, 3400, 3598)
print(f'\n=== SECTOR 3400-3600m ===')
print(f'V3.3: {len(s3400_33)} ticks, time = {len(s3400_33)*0.02:.2f}s, mean speed = {sum(r[1] for r in s3400_33)/len(s3400_33):.1f} km/h')
print(f'V3.4: {len(s3400_34)} ticks, time = {len(s3400_34)*0.02:.2f}s, mean speed = {sum(r[1] for r in s3400_34)/len(s3400_34):.1f} km/h')
print(f'Time saved: {(len(s3400_33)-len(s3400_34))*0.02:.2f}s')

# === POST-HAIRPIN (2500-2800m) acceleration quality
s2500_34 = segment(rows34, 2500, 2800)
s2500_33 = segment(rows33, 2500, 2800)
print(f'\n=== POST-HAIRPIN 2500-2800m ===')
print(f'V3.3: {len(s2500_33)} ticks, time = {len(s2500_33)*0.02:.2f}s, mean speed = {sum(r[1] for r in s2500_33)/len(s2500_33):.1f} km/h')
print(f'V3.4: {len(s2500_34)} ticks, time = {len(s2500_34)*0.02:.2f}s, mean speed = {sum(r[1] for r in s2500_34)/len(s2500_34):.1f} km/h')
print(f'Time saved: {(len(s2500_33)-len(s2500_34))*0.02:.2f}s')

# Where does the car reach 100 km/h after hairpin in each run?
def dist_reach_speed(rows, d_start, target_spd):
    for r in rows:
        if flt(r,'distFromStart') >= d_start and flt(r,'speedX') >= target_spd:
            return flt(r,'distFromStart'), flt(r,'curLapTime')
    return None, None

d33_100, lt33_100 = dist_reach_speed(rows33, 2470, 100)
d34_100, lt34_100 = dist_reach_speed(rows34, 2470, 100)
print(f'\nV3.3: reaches 100km/h after hairpin at dist={d33_100}m, lapTime={lt33_100:.2f}s')
print(f'V3.4: reaches 100km/h after hairpin at dist={d34_100}m, lapTime={lt34_100:.2f}s')

# Hairpin apex speed comparison
hp33 = min([r for r in rows33 if 2440 <= flt(r,'distFromStart') <= 2490 and flt(r,'curLapTime')>=0],
           key=lambda r: flt(r,'speedX'), default=None)
hp34 = min([r for r in rows34 if 2440 <= flt(r,'distFromStart') <= 2490 and flt(r,'curLapTime')>=0],
           key=lambda r: flt(r,'speedX'), default=None)
if hp33: print(f'V3.3 hairpin apex: speed={flt(hp33,"speedX"):.1f}km/h at dist={flt(hp33,"distFromStart"):.0f}m  tp={flt(hp33,"trackPos"):.3f}')
if hp34: print(f'V3.4 hairpin apex: speed={flt(hp34,"speedX"):.1f}km/h at dist={flt(hp34,"distFromStart"):.0f}m  tp={flt(hp34,"trackPos"):.3f}')

# Check 1200-1400m and 2200-2400m gains in V3.3 vs V3.4 context
for seg_start, seg_end in [(1200,1400), (2200,2400)]:
    s34 = segment(rows34, seg_start, seg_end)
    s33 = segment(rows33, seg_start, seg_end)
    print(f'\n=== SECTOR {seg_start}-{seg_end}m ===')
    max_s33 = max(r[1] for r in s33)
    max_s34 = max(r[1] for r in s34)
    print(f'V3.3: {len(s33)} ticks, time={len(s33)*0.02:.2f}s, mean={sum(r[1] for r in s33)/len(s33):.1f}, max={max_s33:.1f}km/h')
    print(f'V3.4: {len(s34)} ticks, time={len(s34)*0.02:.2f}s, mean={sum(r[1] for r in s34)/len(s34):.1f}, max={max_s34:.1f}km/h')
    print(f'Time saved: {(len(s33)-len(s34))*0.02:.2f}s')
