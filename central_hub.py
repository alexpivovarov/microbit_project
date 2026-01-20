"""
Central Hub (MicroPython, micro:bit v2)
- Receives fall alerts, battery reports, and heartbeats
- Sends ACKs and tracks device status
- Handles relayed messages with hop limits
"""

from microbit import *
import radio

# ============== INLINED KITRONIK OLED DRIVER ==============
# Driver lifted from OLED.py to avoid needing a separate file on the device.
OLED_FONT = [
 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422,
 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422,
 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422,
 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422, 0x0022d422,
 0x00000000, 0x000002e0, 0x00018060, 0x00afabea, 0x00aed6ea, 0x01991133, 0x010556aa, 0x00000060,
 0x000045c0, 0x00003a20, 0x00051140, 0x00023880, 0x00002200, 0x00021080, 0x00000100, 0x00111110,
 0x0007462e, 0x00087e40, 0x000956b9, 0x0005d629, 0x008fa54c, 0x009ad6b7, 0x008ada88, 0x00119531,
 0x00aad6aa, 0x0022b6a2, 0x00000140, 0x00002a00, 0x0008a880, 0x00052940, 0x00022a20, 0x0022d422,
 0x00e4d62e, 0x000f14be, 0x000556bf, 0x0008c62e, 0x0007463f, 0x0008d6bf, 0x000094bf, 0x00cac62e,
 0x000f909f, 0x000047f1, 0x0017c629, 0x0008a89f, 0x0008421f, 0x01f1105f, 0x01f4105f, 0x0007462e,
 0x000114bf, 0x000b6526, 0x010514bf, 0x0004d6b2, 0x0010fc21, 0x0007c20f, 0x00744107, 0x01f4111f,
 0x000d909b, 0x00117041, 0x0008ceb9, 0x0008c7e0, 0x01041041, 0x000fc620, 0x00010440, 0x01084210,
 0x00000820, 0x010f4a4c, 0x0004529f, 0x00094a4c, 0x000fd288, 0x000956ae, 0x000097c4, 0x0007d6a2,
 0x000c109f, 0x000003a0, 0x0006c200, 0x0008289f, 0x000841e0, 0x01e1105e, 0x000e085e, 0x00064a4c,
 0x0002295e, 0x000f2944, 0x0001085c, 0x00012a90, 0x010a51e0, 0x010f420e, 0x00644106, 0x01e8221e,
 0x00093192, 0x00222292, 0x00095b52, 0x0008fc80, 0x000003e0, 0x000013f1, 0x00841080, 0x0022d422
]
OLED_AVAILABLE = True
_oled_initialised = False

def _oled_i2c_write_cmd(cmd):
    i2c.write(0x3C, bytearray([0, cmd]))

def _oled_i2c_write_data(data):
    i2c.write(0x3C, bytearray([0x40]) + data)

def _oled_set_pos(col=0, page=0):
    _oled_i2c_write_cmd(0xB0 | page)
    _oled_i2c_write_cmd(0x00 | (col % 16))
    _oled_i2c_write_cmd(0x10 | (col >> 4))

def oled_init_display():
    global _oled_initialised
    try:
        i2c.init(freq=400000, sda=pin20, scl=pin19)
    except Exception as e:
        print("OLED i2c init failed: {}".format(e))
        raise
    cmds = [
        0xAE, 0xA4, 0xD5, 0xF0, 0xA8, 0x3F, 0xD3, 0x00, 0x00, 0x8D, 0x14,
        0x20, 0x00, 0x21, 0, 127, 0x22, 0, 63, 0xA0 | 0x1, 0xC8, 0xDA, 0x12,
        0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA6, 0xD6, 0x00, 0xAF
    ]
    for cmd in cmds:
        _oled_i2c_write_cmd(cmd)
    _oled_initialised = True
    oled_clear_display()

def oled_clear_display():
    for page in range(8):
        _oled_set_pos(0, page)
        _oled_i2c_write_data(bytearray(128))

def oled_show(input_data, line=0):
    global _oled_initialised
    if not _oled_initialised:
        oled_init_display()
    pageBuf = bytearray(129)
    pageBuf[0] = 0x40
    input_string = str(input_data) + " "
    y = line
    string_array = [input_string[i:i+26] for i in range(0, len(input_string), 26)]
    for display_string in string_array:
        for i, char in enumerate(display_string):
            char_bytes = OLED_FONT[ord(char)]
            for k in range(5):
                col = sum((1 << (l + 1)) if char_bytes & (1 << (5 * k + l)) else 0 for l in range(5))
                pageBuf[(i * 5) + k + 1] = col
        _oled_set_pos(0, y)
        _oled_i2c_write_data(pageBuf)
        y += 1

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
        self.oled_present = False
        self.last_oled_lines = ()

state = HubState()

# ============== RADIO HELPERS ==============
def setup_radio():
    radio.on()
    radio.config(group=RADIO_GROUP, power=RADIO_POWER, length=RADIO_LENGTH)

def create_message(msg_type, target_id, data, hops=0):
    return "{}|{}|{}|{}|{}".format(msg_type, HUB_ID, target_id, data, hops)

def parse_message(msg):
    """Allow DATA to contain '|' by joining middle fields."""
    if msg is None:
        return None
    # radio.receive_full() returns bytes; normalize to string
    try:
        if isinstance(msg, (bytes, bytearray)):
            msg = msg.decode("utf-8")
    except Exception:
        return None
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

def send_clear(device_id):
    # Notify the wearable that the alert was acknowledged/reset at the hub.
    msg = create_message("CLR", device_id, "RESET", 0)
    for _ in range(2):
        radio.send(msg)
        sleep(80)

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

# ============== OLED HELPERS ==============
def setup_oled():
    try:
        oled_init_display()
        state.oled_present = True
        oled_write(["Hub ready", "Alerts: 0"], remember=True)
    except Exception as e:
        print("OLED init failed: {}".format(e))
        state.oled_present = False

def oled_write(lines, remember=True):
    if not state.oled_present:
        return
    try:
        oled_clear_display()
        for idx, text in enumerate(lines[:8]):
            oled_show(str(text)[:26], line=idx)
        if remember:
            state.last_oled_lines = tuple(lines[:8])
    except Exception as e:
        print("OLED write failed: {}".format(e))
        state.oled_present = False

def update_oled_status():
    if not state.oled_present:
        return

    current_time = running_time()
    active_count = 0
    for device in state.devices.values():
        if current_time - device.last_seen < DEVICE_TIMEOUT_MS:
            active_count += 1

    lines = []
    if state.showing_alert:
        alert = None
        for candidate in state.active_alerts:
            if candidate['device_id'] == state.current_alert_device:
                alert = candidate
                break
        impact = alert['impact'] if alert else "?"
        location = alert['location'] if alert else (0, 0)
        loc_text = "{:.4f},{:.4f}".format(location[0], location[1]) if location else "loc n/a"
        relay_flag = " relay" if alert and alert.get('via_relay') else ""
        lines = [
            "ALERT dev {}".format(state.current_alert_device if state.current_alert_device is not None else "?"),
            "Impact:{}mg{}".format(impact, relay_flag),
            "GPS:{}".format(loc_text),
        ]
    else:
        lines = [
            "Hub online",
            "Devices: {}".format(active_count),
            "Alerts: {}".format(len(state.active_alerts)),
        ]

    desired = tuple(lines[:8])
    if desired != state.last_oled_lines:
        oled_write(lines)

# ============== DISPLAY AND STATUS ==============
def acknowledge_alert():
    if state.active_alerts:
        alert = state.active_alerts.pop(0)
        device = state.devices.get(alert['device_id'])
        if device:
            device.has_active_alert = False
        send_clear(alert['device_id'])
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
    setup_oled()
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
        update_oled_status()
        sleep(50)

# Run
main()
