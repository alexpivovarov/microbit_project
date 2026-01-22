"""
Central Hub (MicroPython, micro:bit v2)
- Receives fall alerts from sensors
- Sends ACKs back to sensors
- OLED display for status
- Alert acknowledgment system
- Outputs data via serial to desktop

Flash to the hub MicroBit (connect to laptop via USB)
"""

from microbit import *
import radio

# ============== INLINED KITRONIK OLED DRIVER ==============
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

_oled_initialised = False
oled_present = False

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

# ============== STATE ==============
class DeviceInfo:
    def __init__(self, device_id):
        self.device_id = device_id
        self.last_seen = 0
        self.has_active_alert = False

class HubState:
    def __init__(self):
        self.devices = {}
        self.active_alerts = []
        self.showing_alert = False
        self.current_alert_device = None
        self.alert_cycle_start = 0
        self.oled_present = False
        self.last_oled_lines = ()

state = HubState()

# ============== SETUP ==============
def setup_radio():
    radio.on()
    radio.config(group=RADIO_GROUP, power=RADIO_POWER)

def setup_oled():
    try:
        oled_init_display()
        state.oled_present = True
        oled_write(["Hub ready", "Alerts: 0"])
    except:
        state.oled_present = False
        print("OLED not found")

# ============== MESSAGE FUNCTIONS ==============
def parse_message(msg):
    """Parse message format: TYPE|SENDER|TARGET|DATA"""
    if msg is None:
        return None
    try:
        if isinstance(msg, (bytes, bytearray)):
            msg = msg.decode("utf-8")
    except:
        return None
    
    parts = msg.split("|")
    if len(parts) >= 4:
        try:
            return {
                'type': parts[0],
                'sender': int(parts[1]),
                'target': int(parts[2]),
                'data': parts[3]
            }
        except ValueError:
            return None
    return None

def create_message(msg_type, target_id, data):
    """Create message: TYPE|SENDER|TARGET|DATA"""
    return "{}|{}|{}|{}".format(msg_type, HUB_ID, target_id, data)

def send_ack(device_id):
    """Send acknowledgment to device"""
    msg = create_message("ACK", device_id, "OK")
    radio.send(msg)

def send_clear(device_id):
    """Notify device that alert was acknowledged"""
    msg = create_message("CLR", device_id, "RESET")
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

# ============== ALERT HANDLING ==============
def handle_fall_alert(sender, data):
    """Process fall alert"""
    device = update_device_seen(sender)
    device.has_active_alert = True
    
    # Parse acceleration from data
    accel = 0
    if "ACC:" in data:
        try:
            accel = int(data.split("ACC:")[1])
        except:
            pass
    
    # Add to active alerts
    state.active_alerts.append({
        'device_id': sender,
        'time': running_time(),
        'impact': accel
    })
    
    state.showing_alert = True
    state.current_alert_device = sender
    state.alert_cycle_start = running_time()
    
    # Output to serial for desktop client
    print("FALL,{},{}".format(sender, accel))
    
    print("=" * 40)
    print("!!! FALL ALERT !!!")
    print("Device ID: {}".format(sender))
    print("Impact: {} mg".format(accel))
    print("=" * 40)
    
    # Visual alert
    display.show(Image.SKULL)
    sleep(500)
    
    # Send ACK to sensor
    send_ack(sender)

def handle_heartbeat(sender, data):
    """Update presence when a wearable pings the hub"""
    was_known = sender in state.devices
    update_device_seen(sender)
    if not was_known:
        print("Device {} joined".format(sender))

def acknowledge_alert():
    """Acknowledge and clear current alert (button press)"""
    if state.active_alerts:
        alert = state.active_alerts.pop(0)
        device = state.devices.get(alert['device_id'])
        if device:
            device.has_active_alert = False
        
        # Notify sensor that alert was acknowledged
        send_clear(alert['device_id'])
        print("Alert acknowledged for device {}".format(alert['device_id']))
        
        # Move to next alert if any
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

# ============== OLED FUNCTIONS ==============
def oled_write(lines):
    """Write lines to OLED display"""
    if not state.oled_present:
        return
    try:
        oled_clear_display()
        for idx, text in enumerate(lines[:8]):
            oled_show(str(text)[:26], line=idx)
        state.last_oled_lines = tuple(lines[:8])
    except:
        state.oled_present = False

def update_oled():
    """Update OLED with current status"""
    if not state.oled_present:
        return
    
    if state.showing_alert:
        alert = None
        for a in state.active_alerts:
            if a['device_id'] == state.current_alert_device:
                alert = a
                break
        impact = alert['impact'] if alert else "?"
        lines = [
            "ALERT dev {}".format(state.current_alert_device),
            "Impact: {} mg".format(impact),
            "Press B to ACK"
        ]
    else:
        lines = [
            "Hub online",
            "Devices: {}".format(len(state.devices)),
            "Alerts: {}".format(len(state.active_alerts))
        ]
    
    if tuple(lines) != state.last_oled_lines:
        oled_write(lines)

# ============== DISPLAY ==============
def show_alert_pattern(device_id):
    """Flash device ID and ! alternately"""
    if device_id is None:
        display.show("!")
        return
    elapsed = (running_time() - state.alert_cycle_start) % 2000
    if elapsed < 500:
        display.show(str(device_id))
    else:
        flash_slot = int((elapsed - 500) // 250)
        if flash_slot % 2 == 0:
            display.show("!")
        else:
            display.clear()

def update_display():
    """Update LED matrix display"""
    if state.showing_alert:
        show_alert_pattern(state.current_alert_device)
    else:
        if len(state.devices) > 0:
            display.show(str(len(state.devices)))
        else:
            display.show("-")

# ============== MESSAGE PROCESSING ==============
def process_message(msg):
    """Process incoming radio message"""
    parsed = parse_message(msg)
    if not parsed:
        return
    
    if parsed['target'] != HUB_ID:
        return
    
    sender = parsed['sender']
    msg_type = parsed['type']
    data = parsed['data']
    
    if msg_type == 'FALL':
        handle_fall_alert(sender, data)
    elif msg_type == 'HBEAT':
        handle_heartbeat(sender, data)

# ============== MAIN ==============
def main():
    setup_radio()
    setup_oled()
    display.scroll("HUB")
    sleep(400)
    print("Central Hub started")
    
    while True:
        # Process incoming messages
        msg = radio.receive()
        if msg:
            process_message(msg)
        
        # Button B: acknowledge alert
        if button_b.was_pressed():
            if acknowledge_alert():
                display.show(Image.YES)
                sleep(500)
        
        # Button A: print status
        if button_a.was_pressed():
            print("\n--- Status ---")
            print("Devices: {}".format(list(state.devices.keys())))
            print("Active alerts: {}".format(len(state.active_alerts)))
            print("--------------\n")
        
        update_display()
        update_oled()
        sleep(50)

main()
