import math
from snakeoil3_gym import Client

MIN_SPEED = 70
MAX_SPEED = 120
LOOKAHEAD_NEAR = 30
LOOKAHEAD_FAR = 100
STEER_GAIN = 35
CENTERING_GAIN = 0.40
BRAKE_CURVE_FACTOR = 0.8
EMERGENCY_BRAKE_DIST = 25
GEAR_UP = [0, 5500, 6000, 6500, 7000, 7500]
GEAR_DOWN = [0, 2500, 3000, 3500, 4000, 4500]
ENABLE_TRACTION_CONTROL = True
ENABLE_RECOVERY = True

def get_forward_distance(S):
    return max(0.0, min(200.0, S['track'][9]))

def target_speed_dynamic(S):
    fwd = get_forward_distance(S)
    if fwd >= LOOKAHEAD_FAR:
        return MAX_SPEED
    if fwd <= LOOKAHEAD_NEAR:
        return MIN_SPEED
    ratio = (fwd - LOOKAHEAD_NEAR) / (LOOKAHEAD_FAR - LOOKAHEAD_NEAR)
    return MIN_SPEED + ratio * (MAX_SPEED - MIN_SPEED)

def calculate_steering(S):
    angle = S['angle']
    trackPos = S['trackPos']
    steer = (angle * STEER_GAIN / math.pi) - (trackPos * CENTERING_GAIN)
    return max(-1, min(1, steer))

def calculate_throttle_and_brake(S):
    target = target_speed_dynamic(S)
    speed = S['speedX']
    fwd = get_forward_distance(S)
    if fwd < EMERGENCY_BRAKE_DIST and speed > MIN_SPEED:
        return 0.0, 1.0
    diff = target - speed
    if diff > 5:
        accel, brake = 1.0, 0.0
    elif diff > 0:
        accel, brake = 0.6, 0.0
    elif diff > -5:
        accel, brake = 0.1, 0.0
    else:
        accel = 0.0
        brake = min(0.8, (-diff / 20.0) * BRAKE_CURVE_FACTOR + 0.2)
    if speed < 5:
        accel, brake = 1.0, 0.0
    return accel, brake

def shift_gears(S, current_gear):
    rpm = S['rpm']
    gear = max(1, min(5, current_gear if current_gear else 1))
    if gear < 6 and rpm > GEAR_UP[gear]:
        gear += 1
    elif gear > 1 and rpm < GEAR_DOWN[gear]:
        gear -= 1
    return max(1, min(6, gear))

def traction_control(S, accel):
    if not ENABLE_TRACTION_CONTROL:
        return accel
    rear = S['wheelSpinVel'][2] + S['wheelSpinVel'][3]
    front = S['wheelSpinVel'][0] + S['wheelSpinVel'][1]
    if (rear - front) > 2:
        accel -= 0.15
    return max(0.0, accel)

def recovery_maneuver(S):
    if not ENABLE_RECOVERY:
        return None
    trackPos = S['trackPos']
    angle = S['angle']
    if abs(trackPos) > 1.0:
        if S['speedX'] < 5 and abs(angle) > math.pi / 2:
            return (0.3, 0.0, -angle * 0.5)
        steer = -trackPos * 0.5 + angle * 0.5
        return (0.3, 0.0, max(-1, min(1, steer)))
    return None

def drive_v2(c):
    S, R = c.S.d, c.R.d
    rec = recovery_maneuver(S)
    if rec is not None:
        accel, brake, steer = rec
        R['accel'] = accel
        R['brake'] = brake
        R['steer'] = steer
        R['gear'] = shift_gears(S, R.get('gear', 1))
        return
    R['steer'] = calculate_steering(S)
    accel, brake = calculate_throttle_and_brake(S)
    R['accel'] = traction_control(S, accel)
    R['brake'] = brake
    R['gear'] = shift_gears(S, R.get('gear', 1))

if __name__ == "__main__":
    print("=" * 60)
    print("IBM Global AI Racing League - Agente V2 LOOKAHEAD")
    print("=" * 60)
    print(f"  MIN_SPEED          = {MIN_SPEED} km/h")
    print(f"  MAX_SPEED          = {MAX_SPEED} km/h")
    print(f"  LOOKAHEAD_NEAR/FAR = {LOOKAHEAD_NEAR}/{LOOKAHEAD_FAR} m")
    print(f"  STEER_GAIN         = {STEER_GAIN}")
    print(f"  CENTERING_GAIN     = {CENTERING_GAIN}")
    print("=" * 60)
    C = Client(p=3001)
    for step in range(C.maxSteps, 0, -1):
        C.get_servers_input()
        drive_v2(C)
        C.respond_to_server()
    C.shutdown()
