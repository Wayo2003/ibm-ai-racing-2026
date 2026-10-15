"""TORCS V3 Physics-Based Driver.

Enhancements over V2:
1. Physics-based target speed using kinematic braking distance: v = sqrt(v_c^2 + 2 * a * d).
2. Racing line steering aiming at longest sensor ray (open road) with edge margin protection.
3. ABS wheel slip control, proportional traction control, smooth throttle curve, and RPM shifting with hold time.
"""
import math
import sys as _sys

# Defer the TORCS client import so the module can be imported/tested without a
# live server connection (e.g. python src/torcs_v3_physics.py --selftest).
if "--selftest" not in _sys.argv:
    from snakeoil3_gym import Client

# ==============================================================================
# TUNABLE PARAMETERS
# ==============================================================================
PARAMS = {
    # --- Enhancement 1: Target Speed & Braking Model ---
    "V_MAX": 230.0,  # Max target speed on long straights (km/h)
    "V_CORNER_SHARP": 70.0,  # Corner entry speed for 90-deg sharp corners (km/h)
    "V_CORNER_FAST": 140.0,  # Corner entry speed for shallow/fast bends (km/h)
    "BRAKE_DECEL": 9.0,  # Estimated braking deceleration capacity (m/s^2)
    "STRAIGHT_DIST": 100.0,  # Lookahead distance threshold to classify road as straight (m)
    # --- Enhancement 2: Steering & Racing Line ---
    "STEER_AIM": 1.0,  # Weight factor for aiming toward the longest sensor ray
    "CENTERING_GAIN": 0.40,  # Base gain to center vehicle within track bounds
    "TRACK_MARGIN": 0.70,  # |trackPos| threshold beyond which extra centering applies
    "EXTRA_CENTERING_GAIN": 1.20,  # Additional centering gain when exceeding TRACK_MARGIN
    "STRAIGHT_STEER_AIM": 0.25,  # Reduced steer aim gain on straights to prevent weaving
    "STEER_LOCK": 0.366,  # Maximum steering lock angle in radians (TORCS car standard)
    # --- Enhancement 3: ABS, Traction Control, Throttle & Shifting ---
    "ABS_SLIP": 10.0,  # Slip threshold (km/h) where wheel speed < speedX before ABS intervenes
    "TC_SLIP": 2.0,  # Differential spin threshold (rad/s) between rear and front wheels
    "TC_GAIN": 0.08,  # Proportional cut per unit of excessive wheel spin diff
    "GEAR_UP_RPM": 7200,  # Engine RPM threshold to upshift (gears 1-5 -> 2-6)
    "GEAR_DOWN_RPM": 3200,  # Engine RPM threshold to downshift (gears 2-6 -> 1-5)
    "GEAR_HOLD_TICKS": 15,  # Minimum simulation steps (~0.3s) between gear shifts
    "WHEEL_RADIUS": 0.3179,  # Wheel radius in meters (for wheel speed computation)
}

# Sensor angle definitions (19 rays across 180-degree forward arc)
TRACK_ANGLES_DEG = [-90, -75, -60, -45, -30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 30, 45, 60, 75, 90]
TRACK_ANGLES_RAD = [math.radians(deg) for deg in TRACK_ANGLES_DEG]

# Global state for gear shifting hold time
_last_shift_step = -100
_current_step = 0


def get_free_distance_ahead(S):
    """Returns free track distance directly ahead using rays 8 (-5 deg), 9 (0 deg), 10 (+5 deg)."""
    track = S.get("track", [0.0] * 19)
    if not track or len(track) < 19:
        return 0.0
    return max(0.0, max(track[8], track[9], track[10]))


def get_longest_ray_info(S):
    """Finds the track sensor ray with maximum distance (the open-road direction).

    Returns (max_dist, aim_angle_rad, aim_angle_deg).
    """
    track = S.get("track", [0.0] * 19)
    if not track or len(track) < 19:
        return 0.0, 0.0, 0.0

    max_idx = 9  # default center
    max_val = -1.0
    for idx in range(19):
        val = track[idx]
        if val > max_val:
            max_val = val
            max_idx = idx

    return max_val, TRACK_ANGLES_RAD[max_idx], TRACK_ANGLES_DEG[max_idx]


def calculate_target_speed(S):
    """ENHANCEMENT 1: Physics-based target speed (braking-distance model).

    Estimates corner sharpness from the angle of the longest ray, interpolates
    corner speed V_CORNER between V_CORNER_SHARP and V_CORNER_FAST, and computes:
        v_target = min(V_MAX, sqrt(V_CORNER^2 + 2 * BRAKE_DECEL * d))
    If free distance d >= STRAIGHT_DIST, treats road as a straight: target = V_MAX.
    """
    d = get_free_distance_ahead(S)

    # Long straightaway ahead
    if d >= PARAMS["STRAIGHT_DIST"]:
        return PARAMS["V_MAX"]

    # Corner sharpness: 0.0 (straight ahead) to 1.0 (90 deg perpendicular)
    _, _, aim_angle_deg = get_longest_ray_info(S)
    sharpness = min(1.0, abs(aim_angle_deg) / 90.0)

    # Interpolate corner speed based on estimated turn sharpness
    v_corner_kmh = PARAMS["V_CORNER_FAST"] - sharpness * (
        PARAMS["V_CORNER_FAST"] - PARAMS["V_CORNER_SHARP"]
    )

    # Convert to m/s for kinematic braking calculation: v^2 = v_0^2 + 2 * a * d
    v_corner_ms = v_corner_kmh / 3.6
    v_target_ms = math.sqrt(v_corner_ms**2 + 2.0 * PARAMS["BRAKE_DECEL"] * d)
    v_target_kmh = v_target_ms * 3.6

    return min(PARAMS["V_MAX"], v_target_kmh)


def calculate_steering(S):
    """ENHANCEMENT 2: Racing line steering (aim at the corner exit).

    TORCS/SCR sign convention (confirmed from snakeoil3_gym_BASELINE.py::drive_example):
      - track sensor angles: negative = left of car, positive = right of car
      - steer output:        positive = turn LEFT,   negative = turn RIGHT
      - angle:               positive = car nose points LEFT of track axis
      - trackPos:            positive = car displaced to the LEFT of centre

    To aim toward the open road, the aim term must be *subtracted* so that a
    positive aim_angle_rad (open road on the right) produces a negative (right)
    steer contribution:
        steer = (angle - STEER_AIM * aim_angle_rad - CENTERING_GAIN * trackPos) / STEER_LOCK

    Reduces STEER_AIM on straights to prevent weaving and adds progressive
    centering when |trackPos| exceeds TRACK_MARGIN.
    """
    d = get_free_distance_ahead(S)
    _, aim_angle_rad, _ = get_longest_ray_info(S)

    # Reduce aim gain on straights to prevent high-speed oscillation
    aim_gain = (
        PARAMS["STRAIGHT_STEER_AIM"] if d >= PARAMS["STRAIGHT_DIST"] else PARAMS["STEER_AIM"]
    )

    trackPos = S.get("trackPos", 0.0)
    angle = S.get("angle", 0.0)

    # Base track centering
    centering = PARAMS["CENTERING_GAIN"] * trackPos

    # Edge protection: extra centering if car approaches track boundaries
    if abs(trackPos) > PARAMS["TRACK_MARGIN"]:
        margin_excess = abs(trackPos) - PARAMS["TRACK_MARGIN"]
        centering += math.copysign(margin_excess * PARAMS["EXTRA_CENTERING_GAIN"], trackPos)

    steer = (angle - aim_gain * aim_angle_rad - centering) / PARAMS["STEER_LOCK"]
    return max(-1.0, min(1.0, steer))


def calculate_throttle_and_brake(S, steer, target_speed):
    """ENHANCEMENT 3: ABS, traction control, and smooth throttle control.

    - Full throttle when below target by > 10 km/h, proportional otherwise.
    - Zero throttle during braking.
    - Throttle lift when steering at high speed to protect stability.
    - ABS: reduces brake pressure proportionally if wheel speed locks below speedX by > ABS_SLIP.
    - Traction Control: cuts throttle proportionally if rear wheels spin faster than front by > TC_SLIP.
    """
    speed = S.get("speedX", 0.0)
    diff = target_speed - speed

    # 1. Base Throttle & Brake
    if diff > 10.0:
        accel, brake = 1.0, 0.0
    elif diff > 0.0:
        accel, brake = diff / 10.0, 0.0
    else:
        accel = 0.0
        brake = min(1.0, max(0.0, (-diff / 25.0) + 0.1))

    # Low speed launch guarantee
    if speed < 5.0:
        accel, brake = 1.0, 0.0

    # Ensure no simultaneous throttle and brake
    if brake > 0.0:
        accel = 0.0

    # High speed cornering throttle lift
    if speed > 50.0 and abs(steer) > 0.1:
        lift = max(0.0, 1.0 - abs(steer) * (speed / PARAMS["V_MAX"]))
        accel *= lift

    # 2. Anti-lock Braking System (ABS)
    if brake > 0.0 and speed > 10.0:
        spins = S.get("wheelSpinVel", [0.0, 0.0, 0.0, 0.0])
        avg_wheel_rad_s = sum(spins) / 4.0
        wheel_speed_kmh = avg_wheel_rad_s * PARAMS["WHEEL_RADIUS"] * 3.6
        slip = speed - wheel_speed_kmh
        if slip > PARAMS["ABS_SLIP"]:
            excess_slip = slip - PARAMS["ABS_SLIP"]
            reduction = max(0.0, 1.0 - (excess_slip / 20.0))
            brake = max(0.0, brake * reduction)

    # 3. Traction Control System (TCS)
    if accel > 0.0:
        spins = S.get("wheelSpinVel", [0.0, 0.0, 0.0, 0.0])
        front_spin = (spins[0] + spins[1]) / 2.0
        rear_spin = (spins[2] + spins[3]) / 2.0
        tc_diff = rear_spin - front_spin
        if tc_diff > PARAMS["TC_SLIP"]:
            excess_tc = tc_diff - PARAMS["TC_SLIP"]
            accel = max(0.0, accel - excess_tc * PARAMS["TC_GAIN"])

    return accel, brake


def shift_gears(S, current_gear):
    """RPM-based transmission shifting with minimum hold time between shifts."""
    global _last_shift_step, _current_step
    _current_step += 1

    rpm = S.get("rpm", 0.0)
    gear = current_gear if current_gear and current_gear > 0 else 1

    # Hold time to avoid rapid gear hunting/oscillation
    if (_current_step - _last_shift_step) < PARAMS["GEAR_HOLD_TICKS"]:
        return max(1, min(6, gear))

    if gear < 6 and rpm > PARAMS["GEAR_UP_RPM"]:
        gear += 1
        _last_shift_step = _current_step
    elif gear > 1 and rpm < PARAMS["GEAR_DOWN_RPM"]:
        gear -= 1
        _last_shift_step = _current_step

    return max(1, min(6, gear))


def recovery_maneuver(S):
    """V2 Recovery maneuver for when the vehicle is outside track boundaries (|trackPos| > 1.0)."""
    trackPos = S.get("trackPos", 0.0)
    angle = S.get("angle", 0.0)
    if abs(trackPos) > 1.0:
        if S.get("speedX", 0.0) < 5.0 and abs(angle) > math.pi / 2.0:
            return (0.3, 0.0, -angle * 0.5)
        steer = -trackPos * 0.5 + angle * 0.5
        return (0.3, 0.0, max(-1.0, min(1.0, steer)))
    return None


def drive_v3(c):
    """Main driver function called by TORCS client loop or tools/race.py."""
    S, R = c.S.d, c.R.d

    # Priority 1: Track recovery if outside boundaries
    rec = recovery_maneuver(S)
    if rec is not None:
        accel, brake, steer = rec
        R["accel"] = accel
        R["brake"] = brake
        R["steer"] = steer
        R["gear"] = shift_gears(S, R.get("gear", 1))
        return

    # Priority 2: Physics-based control
    steer = calculate_steering(S)
    target_speed = calculate_target_speed(S)
    accel, brake = calculate_throttle_and_brake(S, steer, target_speed)

    R["steer"] = steer
    R["accel"] = accel
    R["brake"] = brake
    R["gear"] = shift_gears(S, R.get("gear", 1))


def _make_state(track, angle=0.0, trackPos=0.0, speedX=50.0):
    """Build a minimal sensor dict for self-tests."""
    return {
        "track": track,
        "angle": angle,
        "trackPos": trackPos,
        "speedX": speedX,
        "wheelSpinVel": [0.0, 0.0, 0.0, 0.0],
        "rpm": 5000.0,
    }


def _flat_track(dominant_idx, dominant_dist=150.0, other_dist=10.0):
    """19-sensor track array where one sensor reads dominant_dist, the rest other_dist."""
    t = [other_dist] * 19
    t[dominant_idx] = dominant_dist
    return t


def _run_selftest():
    """Steering sign self-tests.

    TORCS/SCR conventions that each case verifies:
      - track angle positive  → right of car → steer must be NEGATIVE (turn right)
      - track angle negative  → left of car  → steer must be POSITIVE  (turn left)
      - trackPos positive     → car left of centre → steer must be NEGATIVE (return right)
      - trackPos negative     → car right of centre → steer must be POSITIVE (return left)
    """
    PASS = "\033[32mPASS\033[0m"
    FAIL = "\033[31mFAIL\033[0m"
    failures = 0

    def check(label, condition, steer_val):
        nonlocal failures
        status = PASS if condition else FAIL
        print(f"  [{status}] {label}  (steer={steer_val:+.4f})")
        if not condition:
            failures += 1

    # --- Case 1: open road on the RIGHT (longest ray at index 15, +45 deg) ----
    # Expected: steer < 0 (turn right toward the opening)
    track = _flat_track(15, dominant_dist=150.0)
    S = _make_state(track, angle=0.0, trackPos=0.0)
    s = calculate_steering(S)
    check("Open road on the RIGHT  → steer < 0", s < 0.0, s)

    # --- Case 2: open road on the LEFT (longest ray at index 3, -45 deg) -----
    # Expected: steer > 0 (turn left toward the opening)
    track = _flat_track(3, dominant_dist=150.0)
    S = _make_state(track, angle=0.0, trackPos=0.0)
    s = calculate_steering(S)
    check("Open road on the LEFT   → steer > 0", s > 0.0, s)

    # --- Case 3: car on the LEFT edge (trackPos > TRACK_MARGIN) ---------------
    # trackPos = +0.85 means car is displaced left; must steer RIGHT (steer < 0)
    # Flat track straight ahead so aim term is ~zero (ray 9 is dominant)
    track = _flat_track(9, dominant_dist=150.0)
    S = _make_state(track, angle=0.0, trackPos=0.85)
    s = calculate_steering(S)
    check("Car on the LEFT edge    → steer < 0", s < 0.0, s)

    # --- Case 4: car on the RIGHT edge (trackPos < -TRACK_MARGIN) -------------
    # trackPos = -0.85 means car is displaced right; must steer LEFT (steer > 0)
    track = _flat_track(9, dominant_dist=150.0)
    S = _make_state(track, angle=0.0, trackPos=-0.85)
    s = calculate_steering(S)
    check("Car on the RIGHT edge   → steer > 0", s > 0.0, s)

    print()
    if failures == 0:
        print("All steering sign tests PASSED.")
    else:
        print(f"{failures} test(s) FAILED.")
        raise SystemExit(1)


if __name__ == "__main__":
    if "--selftest" in _sys.argv:
        print("=" * 60)
        print("V3 Physics Driver — Steering Sign Self-Test")
        print("=" * 60)
        _run_selftest()
    else:
        print("=" * 60)
        print("IBM Global AI Racing League - Agente V3 PHYSICS")
        print("=" * 60)
        for k, v in PARAMS.items():
            print(f"  {k:<22} = {v}")
        print("=" * 60)
        C = Client(p=3001)
        for step in range(C.maxSteps, 0, -1):
            C.get_servers_input()
            drive_v3(C)
            C.respond_to_server()
        C.shutdown()
