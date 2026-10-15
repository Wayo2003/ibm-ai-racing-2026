import csv, math

with open('telemetry/torcs_v3_physics_20261015-111942/ticks.csv') as f:
    rows = list(csv.DictReader(f))

def flt(r, k): return float(r[k])

speeds = [flt(r,'speedX') for r in rows]
dists  = [flt(r,'distFromStart') for r in rows]
laps   = [flt(r,'curLapTime') for r in rows]
brakes = [flt(r,'brake') for r in rows]
accels = [flt(r,'accel') for r in rows]
tpos   = [flt(r,'trackPos') for r in rows]
track9 = [flt(r,'track9') for r in rows]
damage = [flt(r,'damage') for r in rows]
steers = [flt(r,'steer') for r in rows]

print('=== BASIC STATS ===')
print(f'Total ticks: {len(rows)}')
max_s_idx = speeds.index(max(speeds))
min_s_idx = speeds.index(min(speeds))
print(f'Max speed: {max(speeds):.1f} km/h at dist {dists[max_s_idx]:.1f} m')
print(f'Min speed (on track): {min(speeds):.1f} km/h at dist {dists[min_s_idx]:.1f} m')
print(f'Max damage: {max(damage):.1f}')
print(f'Final damage: {flt(rows[-1],"damage"):.1f}')

# Braking events
brake_events = [(flt(r,'speedX'), flt(r,'distFromStart'), flt(r,'brake'), flt(r,'track9'), flt(r,'trackPos'))
                for r in rows if flt(r,'brake')>0.5 and flt(r,'speedX')>80]
brake_events.sort(key=lambda x:-x[0])
print('\n=== TOP BRAKING EVENTS (speed>80, brake>0.5) ===')
for spd, dist, brk, t9, tp in brake_events[:12]:
    print(f'  dist={dist:.0f}m  speed={spd:.1f}km/h  brake={brk:.2f}  track9={t9:.1f}m  trackPos={tp:.3f}')

# Low speed points
low_speed = [(flt(r,'speedX'), flt(r,'distFromStart'), flt(r,'trackPos'), flt(r,'track9'), flt(r,'curLapTime'))
             for r in rows if flt(r,'speedX')<80]
low_speed.sort(key=lambda x:x[0])
print('\n=== LOWEST SPEED POINTS ===')
for spd, dist, tp, t9, lt in low_speed[:15]:
    print(f'  dist={dist:.0f}m  speed={spd:.1f}km/h  trackPos={tp:.3f}  track9={t9:.1f}m  lapTime={lt:.3f}s')

# High |trackPos|
high_tp = [(abs(flt(r,'trackPos')), flt(r,'distFromStart'), flt(r,'speedX'), flt(r,'track9'), flt(r,'steer'))
           for r in rows if abs(flt(r,'trackPos'))>0.6]
high_tp.sort(key=lambda x:-x[0])
print('\n=== HIGH |trackPos| > 0.6 ===')
for tp, dist, spd, t9, st in high_tp[:15]:
    print(f'  dist={dist:.0f}m  |trackPos|={tp:.3f}  speed={spd:.1f}km/h  track9={t9:.1f}m  steer={st:.3f}')

# Segment analysis: divide track into 200m bins, compute mean speed and time spent
print('\n=== SEGMENT ANALYSIS (200m bins, mean speed, ticks) ===')
bin_size = 200
max_dist = max(dists)
bins = {}
for i, r in enumerate(rows):
    if flt(r,'curLapTime') < 0:
        continue
    d = flt(r,'distFromStart')
    b = int(d / bin_size) * bin_size
    if b not in bins:
        bins[b] = []
    bins[b].append(flt(r,'speedX'))

for b in sorted(bins.keys()):
    speeds_bin = bins[b]
    mean_spd = sum(speeds_bin)/len(speeds_bin)
    ticks_n = len(speeds_bin)
    time_s = ticks_n * 0.02  # 50Hz = 0.02s per tick
    print(f'  {b:4d}-{b+bin_size:4d}m  mean={mean_spd:5.1f}km/h  ticks={ticks_n:4d}  time={time_s:.2f}s')

# Steer saturation events
steer_sat = [(abs(flt(r,'steer')), flt(r,'distFromStart'), flt(r,'speedX'), flt(r,'trackPos'))
             for r in rows if abs(flt(r,'steer'))>0.95]
print(f'\n=== STEER SATURATION (|steer|>0.95): {len(steer_sat)} ticks ===')
# Group into contiguous runs
if steer_sat:
    prev_dist = -9999
    run_start = None
    run_cnt = 0
    runs = []
    for tp, dist, spd, tpos_v in sorted(steer_sat, key=lambda x:x[1]):
        if dist - prev_dist > 30:
            if run_start is not None:
                runs.append((run_start, prev_dist, run_cnt))
            run_start = dist
            run_cnt = 1
        else:
            run_cnt += 1
        prev_dist = dist
    if run_start is not None:
        runs.append((run_start, prev_dist, run_cnt))
    for rs, re, cnt in runs:
        print(f'  dist={rs:.0f}-{re:.0f}m  ticks={cnt}')

# High brake events near hairpin (dist 2400-2550) 
print('\n=== HAIRPIN ZONE 2400-2600m DETAIL ===')
hp_rows = [(flt(r,'distFromStart'), flt(r,'speedX'), flt(r,'brake'), flt(r,'accel'),
            flt(r,'trackPos'), flt(r,'track9'), flt(r,'steer'), flt(r,'curLapTime'))
           for r in rows if 2400 <= flt(r,'distFromStart') <= 2600]
for d, spd, brk, acc, tp, t9, st, lt in hp_rows[::3]:
    print(f'  dist={d:.0f}m  spd={spd:.1f}  brk={brk:.2f}  acc={acc:.2f}  tp={tp:.3f}  t9={t9:.1f}m  lt={lt:.2f}s')

# Turn 11 zone (3200-3400m)
print('\n=== TURN 11 ZONE 3200-3400m DETAIL ===')
t11_rows = [(flt(r,'distFromStart'), flt(r,'speedX'), flt(r,'brake'), flt(r,'accel'),
             flt(r,'trackPos'), flt(r,'track9'), flt(r,'steer'), flt(r,'curLapTime'))
            for r in rows if 3200 <= flt(r,'distFromStart') <= 3400]
for d, spd, brk, acc, tp, t9, st, lt in t11_rows[::3]:
    print(f'  dist={d:.0f}m  spd={spd:.1f}  brk={brk:.2f}  acc={acc:.2f}  tp={tp:.3f}  t9={t9:.1f}m  lt={lt:.2f}s')

# Compare V3.3 vs V3.4: load V3.3 ticks if available
import os
v33_path = 'telemetry/torcs_v3_physics_20261015-110003/ticks.csv'
if os.path.exists(v33_path):
    with open(v33_path) as f:
        rows33 = list(csv.DictReader(f))
    speeds33 = [flt(r,'speedX') for r in rows33]
    dists33  = [flt(r,'distFromStart') for r in rows33]

    print('\n=== V3.3 vs V3.4 SEGMENT COMPARISON (200m bins) ===')
    bins33 = {}
    for r in rows33:
        if flt(r,'curLapTime') < 0:
            continue
        d = flt(r,'distFromStart')
        b = int(d / bin_size) * bin_size
        if b not in bins33:
            bins33[b] = []
        bins33[b].append(flt(r,'speedX'))

    bins34 = {}
    for r in rows:
        if flt(r,'curLapTime') < 0:
            continue
        d = flt(r,'distFromStart')
        b = int(d / bin_size) * bin_size
        if b not in bins34:
            bins34[b] = []
        bins34[b].append(flt(r,'speedX'))

    all_bins = sorted(set(list(bins33.keys()) + list(bins34.keys())))
    print(f'  {"Bin":12s}  {"V3.3 spd":>9s}  {"V3.4 spd":>9s}  {"delta":>8s}  {"V3.3 tks":>9s}  {"V3.4 tks":>9s}  {"time saved":>10s}')
    total_saved = 0.0
    for b in all_bins:
        s33 = bins33.get(b, [])
        s34 = bins34.get(b, [])
        if not s33 or not s34:
            continue
        m33 = sum(s33)/len(s33)
        m34 = sum(s34)/len(s34)
        # time in segment: ticks * 0.02
        t33 = len(s33)*0.02
        t34 = len(s34)*0.02
        saved = t33 - t34
        total_saved += saved
        marker = ' <-- GAIN' if saved > 0.5 else (' <-- LOSS' if saved < -0.3 else '')
        print(f'  {b:4d}-{b+bin_size:4d}m  {m33:9.1f}  {m34:9.1f}  {m34-m33:+8.1f}  {len(s33):9d}  {len(s34):9d}  {saved:+10.2f}s{marker}')
    print(f'  Total accounted time saved: {total_saved:+.2f}s')
else:
    print('V3.3 ticks not found at expected path.')
