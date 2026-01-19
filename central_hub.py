"""
Central Hub (MicroPython, micro:bit v2)
- Receives fall alerts, battery reports, and heartbeats
- Sends ACKs and tracks device status
- Handles relayed messages with hop limits
"""

from microbit import *
import radio

# ============== CONFIGURATION ==============
HUB_ID = 0
RADIO_GROUP = 42
RADIO_POWER = 7
RADIO_LENGTH = 120  # bytes; keep below 251 for micro:bit

DEVICE_TIMEOUT_MS = 20000   # Device considered offline after this
ALERT_DISPLAY_MS = 10000    # How long to show alert icon
STATUS_PRINT_INTERVAL = 10000
MAX_HOPS = 3

# ============== STATE ==============
class DeviceInfo:
    def __init__(self, device_id):
        self.device_id = device_id
        self.battery_level = 100
        self.last_seen = 0
        self.last_location = (0, 0)
        self.has_active_alert = False
        self.alert_time = 0

class HubState:
    def __init__(self):
        self.devices = {}  # device_id -> DeviceInfo
        self.active_alerts = []
        self.alert_display_start = 0
        self.showing_alert = False
        self.last_status_print = 0
        self.current_alert_device = None
        self.alert_cycle_start = 0

state = HubState()

# ============== RADIO HELPERS ==============
def setup_radio():
    radio.on()
    radio.config(group=RADIO_GROUP, power=RADIO_POWER, length=RADIO_LENGTH)

def create_message(msg_type, target_id, data, hops=0):
    return "{}|{}|{}|{}|{}".format(msg_type, HUB_ID, target_id, data, hops)

def parse_message(msg):
    """Allow DATA to contain '|' by joining middle fields."""
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

def increment_hops(msg_dict):
    new_hops = msg_dict['hops'] + 1
    return "{}|{}|{}|{}|{}".format(
        msg_dict['type'], msg_dict['sender'], msg_dict['target'], msg_dict['data'], new_hops
    )

def send_ack(device_id):
    radio.send(create_message("ACK", device_id, "OK", 0))

# ============== DEVICE MANAGEMENT ==============
def get_or_create_device(device_id):
    if device_id not in state.devices:
        state.devices[device_id] = DeviceInfo(device_id)
    return state.devices[device_id]

def update_device_seen(device_id):
    device = get_or_create_device(device_id)
    device.last_seen = running_time()
    return device

def check_offline_devices():
    current_time = running_time()
    for device_id, device in state.devices.items():
        if current_time - device.last_seen > DEVICE_TIMEOUT_MS:
            print("WARNING: Device {} appears offline".format(device_id))

# ============== ALERT HANDLING ==============
def parse_fall_data(data):
    result = {'lat': 0, 'lon': 0, 'accel': 0}
    try:
        parts = data.split(";")
        for part in parts:
            if part.startswith("GPS:"):
                coords = part[4:].split(",")
                result['lat'] = float(coords[0])
                result['lon'] = float(coords[1])
            elif part.startswith("ACC:"):
                result['accel'] = int(part[4:])
    except Exception:
        pass
    return result

def handle_fall_alert(device_id, data, via_relay=False):
    device = update_device_seen(device_id)
    fall_data = parse_fall_data(data)
    device.has_active_alert = True
    device.alert_time = running_time()
    device.last_location = (fall_data['lat'], fall_data['lon'])

    state.active_alerts.append({
        'device_id': device_id,
        'time': running_time(),
        'location': device.last_location,
        'impact': fall_data['accel'],
        'via_relay': via_relay,
    })

    state.showing_alert = True
    state.alert_display_start = running_time()
    state.current_alert_device = device_id
    state.alert_cycle_start = running_time()

    print("=" * 50)
    print("!!! FALL ALERT !!!" + (" (relay)" if via_relay else ""))
    print("Device ID: {}".format(device_id))
    print("Location: {}, {}".format(fall_data['lat'], fall_data['lon']))
    print("Impact Force: {} mg".format(fall_data['accel']))
    print("Time: {} ms".format(running_time()))
    print("=" * 50)

    trigger_alarm()
    send_ack(device_id)

def handle_battery_update(device_id, level):
    device = update_device_seen(device_id)
    try:
        device.battery_level = float(level)
    except ValueError:
        device.battery_level = 0

    if device.battery_level < 20:
        print("WARNING: Device {} battery low: {}%".format(device_id, device.battery_level))
    print("Device {} battery: {}%".format(device_id, device.battery_level))
    send_ack(device_id)

def handle_heartbeat(device_id):
    update_device_seen(device_id)
    send_ack(device_id)

def trigger_alarm():
    for _ in range(3):
        display.show(Image.SKULL)
        pin0.write_digital(1)
        sleep(300)
        display.clear()
        pin0.write_digital(0)
        sleep(200)

# ============== DISPLAY AND STATUS ==============
def acknowledge_alert():
    if state.active_alerts:
        alert = state.active_alerts.pop(0)
        device = state.devices.get(alert['device_id'])
        if device:
            device.has_active_alert = False
        print("Alert acknowledged for device {}".format(alert['device_id']))
        if state.active_alerts:
            next_alert = state.active_alerts[0]
            state.current_alert_device = next_alert['device_id']
            state.alert_cycle_start = running_time()
            state.showing_alert = True
        else:
            state.showing_alert = False
            state.current_alert_device = None
        return True
    return False

def show_alert_pattern(device_id):
    """Show 'device id' then three flashes of ! in a loop until acknowledged."""
    if device_id is None:
        display.show("!")
        return
    elapsed = (running_time() - state.alert_cycle_start) % 2000  # 2s cycle
    if elapsed < 500:
        display.show(str(device_id))
    else:
        flash_slot = int((elapsed - 500) // 250)  # 0..5 over 1500ms
        if flash_slot % 2 == 0:
            display.show("!")
        else:
            display.clear()

def update_display():
    current_time = running_time()
    if state.showing_alert:
        show_alert_pattern(state.current_alert_device)
    else:
        active_count = 0
        for device in state.devices.values():
            if current_time - device.last_seen < DEVICE_TIMEOUT_MS:
                active_count += 1
        if state.active_alerts:
            display.show("!")
        elif active_count > 0:
            display.show(str(active_count))
        else:
            display.show("-")

def print_status():
    current_time = running_time()
    print("\n--- System Status ---")
    print("Active Alerts: {}".format(len(state.active_alerts)))
    print("Registered Devices: {}".format(len(state.devices)))
    for device_id, device in state.devices.items():
        age = (current_time - device.last_seen) // 1000
        status = "ONLINE" if age < DEVICE_TIMEOUT_MS // 1000 else "OFFLINE"
        alert_flag = " [ALERT!]" if device.has_active_alert else ""
        print("  Device {}: {} | Battery: {}% | Last seen: {}s ago{}".format(
            device_id, status, device.battery_level, age, alert_flag))
    print("-------------------\n")

# ============== MESSAGE PROCESSING ==============
def process_message(raw_msg):
    parsed = parse_message(raw_msg)
    if not parsed:
        return

    sender = parsed['sender']
    msg_type = parsed['type']

    # If this is a RELAY wrapper, unwrap and process inner message
    if msg_type == 'RELAY':
        inner = parse_message(parsed['data'])
        if not inner:
            return
        if inner['hops'] >= MAX_HOPS:
            return
        inner['hops'] += 1  # count this hop
        process_message("{}|{}|{}|{}|{}".format(
            inner['type'], inner['sender'], inner['target'], inner['data'], inner['hops']
        ))
        return

    # Ignore messages not intended for the hub
    if parsed['target'] != HUB_ID and msg_type != 'ACK':
        return

    if msg_type == 'FALL':
        handle_fall_alert(sender, parsed['data'], via_relay=False)
    elif msg_type == 'BATT':
        handle_battery_update(sender, parsed['data'])
    elif msg_type == 'HBEAT':
        handle_heartbeat(sender)
    elif msg_type == 'ACK':
        # ACKs to the hub are ignored
        return

# ============== MAIN LOOP ==============
def main():
    setup_radio()
    display.scroll("HUB")
    sleep(400)
    print("Central Hub started")

    while True:
        while True:
            msg = radio.receive()
            if not msg:
                break
            process_message(msg)

        if button_b.was_pressed():
            if acknowledge_alert():
                display.show(Image.YES)
                sleep(500)
            else:
                print_status()

        if button_a.was_pressed():
            print_status()

        current_time = running_time()
        if current_time - state.last_status_print > STATUS_PRINT_INTERVAL:
            check_offline_devices()
            state.last_status_print = current_time

        update_display()
        sleep(50)

# Run
main()
