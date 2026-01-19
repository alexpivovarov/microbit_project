"""
Central Hub / Monitoring Station - MicroBit
=============================================
Features:
- Receives fall alerts from wearables
- Tracks battery levels of all devices
- Manages mesh network health
- Dispatches alerts (visual/audio + serial output)
- Maintains device registry

Hardware: BBC MicroBit V2
"""

from microbit import *
import radio

# ============== CONFIGURATION ==============
HUB_ID = 0
RADIO_GROUP = 42
RADIO_POWER = 7

# Timing
DEVICE_TIMEOUT_MS = 20000  # Device considered offline after this
ALERT_DISPLAY_MS = 10000   # How long to show alert

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
    devices = {}  # device_id -> DeviceInfo
    active_alerts = []
    alert_display_start = 0
    showing_alert = False

state = HubState()

# ============== RADIO SETUP ==============
def setup_radio():
    radio.on()
    radio.config(group=RADIO_GROUP, power=RADIO_POWER, length=251)

# ============== MESSAGE HANDLING ==============
def parse_message(msg):
    """Parse incoming message"""
    try:
        parts = msg.split("|")
        if len(parts) >= 5:
            return {
                'type': parts[0],
                'sender': int(parts[1]),
                'target': int(parts[2]),
                'data': parts[3],
                'hops': int(parts[4])
            }
    except:
        pass
    return None

def send_ack(device_id):
    """Send acknowledgment to device"""
    msg = "ACK|{}|{}|OK|0".format(HUB_ID, device_id)
    radio.send(msg)

def parse_fall_data(data):
    """Parse fall alert data: GPS:lat,lon;ACC:value"""
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
    except:
        pass
    return result

# ============== DEVICE MANAGEMENT ==============
def get_or_create_device(device_id):
    """Get device info or create new entry"""
    if device_id not in state.devices:
        state.devices[device_id] = DeviceInfo(device_id)
    return state.devices[device_id]

def update_device_seen(device_id):
    """Update last seen timestamp"""
    device = get_or_create_device(device_id)
    device.last_seen = running_time()

def check_offline_devices():
    """Check for devices that haven't reported in"""
    current_time = running_time()
    offline = []
    for device_id, device in state.devices.items():
        if current_time - device.last_seen > DEVICE_TIMEOUT_MS:
            offline.append(device_id)
    return offline

# ============== ALERT HANDLING ==============
def handle_fall_alert(device_id, data):
    """Process incoming fall alert"""
    device = get_or_create_device(device_id)
    fall_data = parse_fall_data(data)
    
    device.has_active_alert = True
    device.alert_time = running_time()
    device.last_location = (fall_data['lat'], fall_data['lon'])
    
    state.active_alerts.append({
        'device_id': device_id,
        'time': running_time(),
        'location': (fall_data['lat'], fall_data['lon']),
        'impact': fall_data['accel']
    })
    
    # Trigger alert display
    state.showing_alert = True
    state.alert_display_start = running_time()
    
    # Output to serial for external systems
    print("=" * 50)
    print("!!! FALL ALERT !!!")
    print("Device ID: {}".format(device_id))
    print("Location: {}, {}".format(fall_data['lat'], fall_data['lon']))
    print("Impact Force: {} mg".format(fall_data['accel']))
    print("Time: {} ms".format(running_time()))
    print("=" * 50)
    
    # Sound alarm
    trigger_alarm()

def handle_battery_update(device_id, level):
    """Update device battery level"""
    device = get_or_create_device(device_id)
    device.battery_level = float(level)
    
    # Warn if low battery
    if device.battery_level < 20:
        print("WARNING: Device {} battery low: {}%".format(
            device_id, device.battery_level))
    
    print("Device {} battery: {}%".format(device_id, device.battery_level))

def handle_heartbeat(device_id):
    """Process heartbeat from device"""
    update_device_seen(device_id)
    send_ack(device_id)

def trigger_alarm():
    """Visual and audio alarm for fall detection"""
    # Flash display
    for _ in range(3):
        display.show(Image.SKULL)
        pin0.write_digital(1)  # Buzzer
        sleep(300)
        display.clear()
        pin0.write_digital(0)
        sleep(200)

def acknowledge_alert():
    """Operator acknowledges alert (button press)"""
    if state.active_alerts:
        alert = state.active_alerts.pop(0)
        device = state.devices.get(alert['device_id'])
        if device:
            device.has_active_alert = False
        
        print("Alert acknowledged for device {}".format(alert['device_id']))
        state.showing_alert = False
        return True
    return False

# ============== DISPLAY ==============
def update_display():
    """Update display based on current state"""
    current_time = running_time()
    
    if state.showing_alert:
        # Show alert animation
        if (current_time // 500) % 2 == 0:
            display.show(Image.SKULL)
        else:
            display.show("!")
        
        # Auto-dismiss display after timeout (alert still active)
        if current_time - state.alert_display_start > ALERT_DISPLAY_MS:
            state.showing_alert = False
    else:
        # Show device count or status
        active_count = len([d for d in state.devices.values() 
                          if current_time - d.last_seen < DEVICE_TIMEOUT_MS])
        
        if state.active_alerts:
            # Pending alerts
            display.show("!")
        elif active_count > 0:
            display.show(str(active_count))
        else:
            display.show("-")

# ============== STATUS REPORTING ==============
def print_status():
    """Print full system status (for monitoring)"""
    current_time = running_time()
    print("\n--- System Status ---")
    print("Active Alerts: {}".format(len(state.active_alerts)))
    print("Registered Devices: {}".format(len(state.devices)))
    
    for device_id, device in state.devices.items():
        age = (current_time - device.last_seen) // 1000
        status = "ONLINE" if age < DEVICE_TIMEOUT_MS // 1000 else "OFFLINE"
        alert_status = " [ALERT!]" if device.has_active_alert else ""
        print("  Device {}: {} | Battery: {}% | Last seen: {}s ago{}".format(
            device_id, status, device.battery_level, age, alert_status))
    
    print("-------------------\n")

# ============== MESSAGE PROCESSING ==============
def process_messages():
    """Process all incoming radio messages"""
    while True:
        msg = radio.receive()
        if not msg:
            break
        
        parsed = parse_message(msg)
        if not parsed:
            continue
        
        sender = parsed['sender']
        msg_type = parsed['type']
        data = parsed['data']
        
        # Update device tracking
        update_device_seen(sender)
        
        # Handle message types
        if msg_type == 'FALL':
            handle_fall_alert(sender, data)
            send_ack(sender)
        
        elif msg_type == 'BATT':
            handle_battery_update(sender, data)
            send_ack(sender)
        
        elif msg_type == 'HBEAT':
            handle_heartbeat(sender)
        
        # Relayed messages (came through another device)
        elif msg_type == 'RELAY':
            # Process as if direct, but note the relay
            print("Relayed message from device {} (hops: {})".format(
                sender, parsed['hops']))

# ============== MAIN LOOP ==============
def main():
    setup_radio()
    display.scroll("HUB")
    sleep(500)
    
    last_status_print = 0
    STATUS_PRINT_INTERVAL = 10000  # Print status every 10 seconds
    
    print("Central Hub Started")
    print("Waiting for devices...")
    
    while True:
        # Process incoming messages
        process_messages()
        
        # Check for button press to acknowledge alerts
        if button_a.was_pressed():
            if acknowledge_alert():
                display.show(Image.YES)
                sleep(500)
        
        # Button B for manual status print
        if button_b.was_pressed():
            print_status()
        
        # Periodic status update
        current_time = running_time()
        if current_time - last_status_print > STATUS_PRINT_INTERVAL:
            # Check for offline devices
            offline = check_offline_devices()
            for device_id in offline:
                print("WARNING: Device {} appears offline".format(device_id))
            
            last_status_print = current_time
        
        # Update display
        update_display()
        
        sleep(50)

# Run
main()
