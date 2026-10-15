"""Race runner with lap telemetry.

Runs any driver module (one that defines `drive_v2(c)` or `drive(c)`) against TORCS
and records telemetry so every attempt is measured the same way.

Usage (TORCS open in Race -> Practice -> New Race, waiting for scr_server):
    C:\\torcs-env\\Scripts\\python.exe tools\\race.py src\\torcs_jm_par_V2_LOOKAHEAD.py --laps 2

Outputs (in telemetry/<driver>_<timestamp>/):
    ticks.csv  every simulation step (speed, trackPos, damage, ...)
    laps.csv   one row per completed lap
"""
import argparse
import csv
import importlib.util
import os
import sys
import time

sys.path.insert(0, r"C:\torcs\gym_torcs")
from snakeoil3_gym import Client  # noqa: E402


def load_driver(path):
    spec = importlib.util.spec_from_file_location("driver", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in ("drive_v3", "drive_v2", "drive_modular", "drive_example", "drive"):
        if hasattr(mod, name):
            return getattr(mod, name), name
    raise SystemExit(f"{path} has no drive_v3/drive_v2/drive_modular/drive function")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("driver")
    ap.add_argument("--laps", type=int, default=2, help="stop after N completed laps")
    ap.add_argument("--port", type=int, default=3001)
    args = ap.parse_args()

    drive, fname = load_driver(args.driver)
    tag = os.path.splitext(os.path.basename(args.driver))[0]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "telemetry", f"{tag}_{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out, exist_ok=True)

    print(f"Driver: {tag} ({fname})  ->  {out}")
    sys.argv = [sys.argv[0]]  # snakeoil parses argv itself
    C = Client(p=args.port)

    tick_f = open(os.path.join(out, "ticks.csv"), "w", newline="")
    ticks = csv.writer(tick_f)
    ticks.writerow(["step", "lap", "curLapTime", "distFromStart", "speedX", "trackPos", "angle",
                    "damage", "gear", "rpm", "steer", "accel", "brake", "track9"])
    laps = []
    lap, prev_last, lap_max_speed, lap_offtrack, lap_start_damage = 1, 0.0, 0.0, 0, 0.0
    offtrack_now = False

    try:
        for step in range(C.maxSteps):
            C.get_servers_input()
            S, R = C.S.d, C.R.d
            drive(C)
            C.respond_to_server()

            spd = S.get("speedX", 0.0)
            lap_max_speed = max(lap_max_speed, spd)
            off = abs(S.get("trackPos", 0.0)) > 1.0
            if off and not offtrack_now:
                lap_offtrack += 1
            offtrack_now = off
            ticks.writerow([step, lap, S.get("curLapTime"), S.get("distFromStart"), round(spd, 2),
                            round(S.get("trackPos", 0.0), 3), round(S.get("angle", 0.0), 4),
                            S.get("damage"), R.get("gear"), round(S.get("rpm", 0.0)),
                            round(R.get("steer", 0.0), 3), round(R.get("accel", 0.0), 2),
                            round(R.get("brake", 0.0), 2), round(S["track"][9], 1)])
            if step % 50 == 0:
                tick_f.flush()  # keep data if the run is stopped by hand

            last = S.get("lastLapTime", 0.0) or 0.0
            if last > 0 and abs(last - prev_last) > 1e-6:
                dmg = S.get("damage", 0.0)
                row = {"lap": lap, "lap_time_s": round(last, 3),
                       "lap_time": f"{int(last // 60)}:{last % 60:06.3f}",
                       "damage_this_lap": round(dmg - lap_start_damage, 1), "damage_total": dmg,
                       "max_speed_kmh": round(lap_max_speed, 1), "offtrack_events": lap_offtrack}
                laps.append(row)
                print(f"LAP {lap}: {row['lap_time']}  damage+{row['damage_this_lap']}  "
                      f"max {row['max_speed_kmh']} km/h  offtrack {lap_offtrack}")
                prev_last, lap_max_speed, lap_offtrack, lap_start_damage = last, 0.0, 0, dmg
                lap += 1
                if len(laps) >= args.laps:
                    break
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        tick_f.close()
        if laps:
            with open(os.path.join(out, "laps.csv"), "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(laps[0].keys()))
                w.writeheader()
                w.writerows(laps)
            best = min(laps, key=lambda r: r["lap_time_s"])
            print(f"\nBEST LAP: {best['lap_time']} (lap {best['lap']}), total damage {laps[-1]['damage_total']}")
        try:
            C.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
