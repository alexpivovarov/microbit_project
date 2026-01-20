"""
Wearable / Node (MicroPython, micro:bit v2)
- Detects falls (impact + stillness with post-impact window)
- Sends fall alerts, battery reports, and heartbeats to the hub
- Relays hub-bound messages with a hop limit
"""

from microbit import *
import radio
import math
import random
import music

# ============== CONFIGURATION ==============
DEVICE_ID = 1              # Set unique ID per node
HUB_ID = 0                 # Hub destination ID
RADIO_GROUP = 42
RADIO_POWER = 7
RADIO_LENGTH = 120         # bytes; keep below 251

IMPACT_THRESHOLD = 3200    # mg
STILLNESS_THRESHOLD = 150  # mg
STILLNESS_DURATION_MS = 2000
POST_IMPACT_WINDOW_MS = 4000
SAMPLE_RATE_MS = 50

HEARTBEAT_INTERVAL_MS = 5000
MAX_MISSED_HEARTBEATS = 3
MAX_HOPS = 3

BATTERY_REPORT_INTERVAL_MS = 30000
SIMULATED_BATTERY_DRAIN = 0.01
BASE_LAT = 53.8008
BASE_LON = -1.5491
ALERT_VOLUME = 200

# ============== STATE ==============
class State:
    def __init__(self):
        self.battery_level = 100.0
        self.last_battery_report = 0
        self.last_heartbeat_sent = 0
        self.last_hub_ack = 0
        self.hub_responsive = True

        self.impact_detected = False
        self.impact_time = 0
        self.monitoring_stillness = False
        self.still_start_time = 0

state = State()

# ============== RADIO HELPERS ==============
def setup_radio():
    radio.on()
    radio.config(group=RADIO_GROUP, power=RADIO_POWER, length=RADIO_LENGTH)

def setup_audio():
    # Prefer the built-in speaker on v2; safely ignore on v1.
    try:
        music.set_built_in_speaker_enabled(True)
    except AttributeError:
        pass
    try:
        volume = max(0, min(255, ALERT_VOLUME))
        music.set_volume(volume)
    except AttributeError:
        pass

def create_message(msg_type, target_id, data, hops=0):
    return "{}|{}|{}|{}|{}".format(msg_type, DEVICE_ID, target_id, data, hops)

def parse_message(msg):
    parts = msg.split("|")
    if len(parts) >= 5:
        try:
            return {
                'type': parts[0],
                'sender': int(parts[1]),
                'target': int(parts[2]),
                'data': "|".join(parts[3:-1]),
                'hops': int(parts[-1]),
                'raw': msg,
            }
        except ValueError:
            return None
    return None

def reserialize(msg_dict, new_hops=None):
    hops = msg_dict['hops'] if new_hops is None else new_hops
    return "{}|{}|{}|{}|{}".format(
        msg_dict['type'], msg_dict['sender'], msg_dict['target'], msg_dict['data'], hops
    )

# ============== FALL DETECTION ==============
def get_accel_mag():
    x = accelerometer.get_x()
    y = accelerometer.get_y()
    z = accelerometer.get_z()
    return math.sqrt(x * x + y * y + z * z)

def analyze_movement():
    current_time = running_time()
    magnitude = get_accel_mag()

    if not state.monitoring_stillness:
        if magnitude > IMPACT_THRESHOLD:
            state.impact_detected = True
            state.impact_time = current_time
            state.monitoring_stillness = True
            state.still_start_time = 0
            display.show("!")
            return None
    else:
        deviation = abs(magnitude - 1000)
        if deviation < STILLNESS_THRESHOLD:
            if state.still_start_time == 0:
                state.still_start_time = current_time
            if current_time - state.still_start_time >= STILLNESS_DURATION_MS:
                state.monitoring_stillness = False
                state.impact_detected = False
                return True
        else:
            state.still_start_time = 0

        if current_time - state.impact_time > POST_IMPACT_WINDOW_MS:
            state.monitoring_stillness = False
            state.impact_detected = False
            display.show(Image.HAPPY)

    return False

# ============== SIMULATION HELPERS ==============
def get_simulated_gps():
    lat = BASE_LAT + random.uniform(-0.001, 0.001)
    lon = BASE_LON + random.uniform(-0.001, 0.001)
    return (round(lat, 6), round(lon, 6))

def get_battery_level():
    state.battery_level = max(0, state.battery_level - SIMULATED_BATTERY_DRAIN)
    return round(state.battery_level, 1)
# ============================== AUDIO HELPERS ==============
def play_fall_sound():
    # Short chirp pattern to signal a detected fall without blocking the loop.
    # melody = ['E5:2', 'C5:2', 'E5:2']
    # music.play(melody, wait=False)   
    pass
# ============== HARDWARE HELPERS ==============
def safe_pin0_write(value):
    try:
        pin0.write_digital(value)
    except Exception:
        # If pin0 is busy (e.g., speaker routing), ignore the indicator pulse.
        pass

# ============== SENDING ==============
def send_with_optional_relay(message):
    radio.send(message)
    if not state.hub_responsive:
        relay_wrapper = create_message("RELAY", HUB_ID, message, 1)
        radio.send(relay_wrapper)

def send_fall_alert():
    play_fall_sound()
    lat, lon = get_simulated_gps()
    accel = int(get_accel_mag())
    data = "GPS:{},{};ACC:{}".format(lat, lon, accel)
    msg = create_message("FALL", HUB_ID, data, 0)
    for _ in range(2):
        send_with_optional_relay(msg)
        sleep(120)
    display.show(Image.SAD)
    for _ in range(3):
        safe_pin0_write(1)
        sleep(200)
        safe_pin0_write(0)
        sleep(200)

def send_battery_status():
    level = get_battery_level()
    msg = create_message("BATT", HUB_ID, str(level), 0)
    send_with_optional_relay(msg)

def send_heartbeat():
    now = running_time()
    if now - state.last_heartbeat_sent >= HEARTBEAT_INTERVAL_MS:
        state.last_heartbeat_sent = now
        msg = create_message("HBEAT", HUB_ID, str(now), 0)
        send_with_optional_relay(msg)

# ============== RELAYING AND PROCESSING ==============
def forward_to_hub(msg_dict):
    if msg_dict['hops'] >= MAX_HOPS:
        return
    forwarded = reserialize(msg_dict, msg_dict['hops'] + 1)
    radio.send(forwarded)

def handle_message(msg_dict, via_relay=False):
    # Forward hub-bound messages if we are not the hub
    if msg_dict['target'] == HUB_ID and msg_dict['sender'] != DEVICE_ID:
        forward_to_hub(msg_dict)

    if msg_dict['target'] not in (DEVICE_ID, HUB_ID):
        return

    if msg_dict['type'] == 'ACK' and msg_dict['target'] == DEVICE_ID:
        state.last_hub_ack = running_time()
        state.hub_responsive = True
    elif msg_dict['type'] == 'HBEAT' and msg_dict['target'] == DEVICE_ID:
        state.hub_responsive = True
    elif msg_dict['type'] == 'CLR' and msg_dict['target'] == DEVICE_ID:
        reset_alert_state()

def process_incoming():
    msg = radio.receive()
    if not msg:
        return
    parsed = parse_message(msg)
    if not parsed:
        return

    if parsed['type'] == 'RELAY':
        inner = parse_message(parsed['data'])
        if not inner:
            return
        if inner['hops'] >= MAX_HOPS:
            return
        inner['hops'] += 1
        handle_message(inner, via_relay=True)
        return

    handle_message(parsed, via_relay=False)

# ============== STATUS HELPERS ==============
def check_hub_connectivity():
    now = running_time()
    if now - state.last_hub_ack > HEARTBEAT_INTERVAL_MS * MAX_MISSED_HEARTBEATS:
        state.hub_responsive = False

def reset_alert_state():
    # Clear any local alert indicators when hub marks alert complete.
    state.monitoring_stillness = False
    state.impact_detected = False
    state.still_start_time = 0
    state.impact_time = 0
    display.show(Image.HAPPY)
    safe_pin0_write(0)

def show_status_icon():
    if state.monitoring_stillness:
        display.show("!")
    elif state.hub_responsive:
        display.show(Image.HEART_SMALL)
    else:
        display.show(Image.CONFUSED)

# ============== TEST MODE ==============
def run_test_mode():
    display.scroll("TEST")
    while True:
        if button_a.was_pressed():
            display.scroll("FALL")
            send_fall_alert()
        if button_b.was_pressed():
            display.scroll(str(int(get_accel_mag())))
        if button_a.is_pressed() and button_b.is_pressed():
            break
        sleep(100)

# ============== MAIN LOOP ==============
def main():
    setup_radio()
    setup_audio()
    display.show(str(DEVICE_ID))
    sleep(800)

    if button_a.is_pressed():
        run_test_mode()

    state.last_hub_ack = running_time()

    while True:
        result = analyze_movement()
        if result is True:
            send_fall_alert()

        process_incoming()
        send_heartbeat()
        check_hub_connectivity()

        now = running_time()
        if now - state.last_battery_report >= BATTERY_REPORT_INTERVAL_MS:
            state.last_battery_report = now
            send_battery_status()

        show_status_icon()
        sleep(SAMPLE_RATE_MS)

# Run
main()
