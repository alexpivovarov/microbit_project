"""
Fall Detection Wearable Device - MicroBit

Features:
- Accelerometer-based fall detection (spike + stillness)
- Simulated GPS coordinates
- Battery level monitoring
- Mesh network routing with failover
- Heartbeat system for connectivity monitoring

"""

from microbit import *
import radio
import math
import random

# ============== CONFIGURATION ==============
DEVICE_ID = 1  # Change for each wearable (1, 2, 3, etc.)
CENTRAL_HUB_ID = 0
RADIO_GROUP = 42
RADIO_POWER = 7  # Max power for range

# Fall detection thresholds
IMPACT_THRESHOLD = 2500      # mg - spike detection (gravity = 1000mg)
STILLNESS_THRESHOLD = 150    # mg - deviation from 1g considered "still"
STILLNESS_DURATION_MS = 2000 # Must be still for 2 seconds after impact
SAMPLE_RATE_MS = 50          # Accelerometer sampling rate

# Battery simulation (MicroBit doesn't have real battery sensor)
BATTERY_REPORT_INTERVAL_MS = 30000  # Report every 30 seconds
SIMULATED_BATTERY_DRAIN = 0.01      # % per report cycle

# Heartbeat for mesh network
HEARTBEAT_INTERVAL_MS = 5000
MAX_MISSED_HEARTBEATS = 3

# Simulated GPS (Leeds area coordinates)
BASE_LAT = 53.8008
BASE_LON = -1.5491

# ============== STATE VARIABLES ==============
class State:
    battery_level = 100.0
    last_battery_report = 0
    last_heartbeat_sent = 0
    last_hub_response = 0
    hub_responsive = True
    known_relays = set()  # Other wearables that can relay
    
    # Fall detection state machine
    impact_detected = False
    impact_time = 0
    is_monitoring_stillness = False
    
    # Movement history for pattern detection
    accel_history = []
    HISTORY_SIZE = 20

state = State()

# ============== RADIO SETUP ==============
def setup_radio():
    radio.on()
    radio.config(group=RADIO_GROUP, power=RADIO_POWER, length=251)

# ============== ACCELEROMETER FUNCTIONS ==============
def get_acceleration_magnitude():
    """Calculate total acceleration magnitude in mg"""
    x = accelerometer.get_x()
    y = accelerometer.get_y()
    z = accelerometer.get_z()
    return math.sqrt(x*x + y*y + z*z)

def detect_impact(magnitude):
    """Detect sudden spike indicating potential fall"""
    return magnitude > IMPACT_THRESHOLD

def is_still(magnitude):
    """Check if device is relatively still (close to 1g = resting)"""
    # At rest, magnitude should be ~1000mg (gravity only)
    deviation = abs(magnitude - 1000)
    return deviation < STILLNESS_THRESHOLD

def analyze_movement():
    """
    Fall detection algorithm:
    1. Detect sudden spike (impact)
    2. Monitor for stillness after impact
    3. Confirm fall if still for STILLNESS_DURATION_MS
    """
    current_time = running_time()
    magnitude = get_acceleration_magnitude()
    
    # Store in history for pattern analysis
    state.accel_history.append((current_time, magnitude))
    if len(state.accel_history) > state.HISTORY_SIZE:
        state.accel_history.pop(0)
    
    # State machine for fall detection
    if not state.is_monitoring_stillness:
        # Looking for impact
        if detect_impact(magnitude):
            state.impact_detected = True
            state.impact_time = current_time
            state.is_monitoring_stillness = True
            display.show("!")
            return None  # Don't confirm yet, wait for stillness
    else:
        # Monitoring for stillness after impact
        if is_still(magnitude):
            time_since_impact = current_time - state.impact_time
            if time_since_impact >= STILLNESS_DURATION_MS:
                # FALL CONFIRMED
                state.is_monitoring_stillness = False
                state.impact_detected = False
                return True  # Fall detected!
        else:
            # Movement detected - might be recovering or false alarm
            if current_time - state.impact_time > STILLNESS_DURATION_MS * 2:
                # Too long since impact without sustained stillness
                state.is_monitoring_stillness = False
                state.impact_detected = False
                display.show(".")
    
    return False

# ============== GPS SIMULATION ==============
def get_simulated_gps():
    """
    Simulate GPS coordinates with slight variation.
    In real implementation, connect external GPS module via I2C/UART.
    """
    # Add small random walk to simulate movement
    lat = BASE_LAT + random.uniform(-0.001, 0.001)
    lon = BASE_LON + random.uniform(-0.001, 0.001)
    return (round(lat, 6), round(lon, 6))

# ============== BATTERY MONITORING ==============
def get_battery_level():
    """
    Simulate battery level.
    Real implementation would read from ADC pin connected to battery.
    """
    state.battery_level = max(0, state.battery_level - SIMULATED_BATTERY_DRAIN)
    return round(state.battery_level, 1)

def should_report_battery():
    current_time = running_time()
    if current_time - state.last_battery_report >= BATTERY_REPORT_INTERVAL_MS:
        state.last_battery_report = current_time
        return True
    return False

# ============== MESSAGE PROTOCOL ==============
def create_message(msg_type, data):
    """
    Message format: TYPE|SENDER|TARGET|DATA|HOP_COUNT
    Types: FALL, BATT, HBEAT, ACK, RELAY
    """
    return "{}|{}|{}|{}|0".format(msg_type, DEVICE_ID, CENTRAL_HUB_ID, data)

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

def increment_hop_count(msg):
    """Increment hop count for relay"""
    parts = msg.split("|")
    if len(parts) >= 5:
        parts[4] = str(int(parts[4]) + 1)
        return "|".join(parts)
    return msg

# ============== NETWORK FUNCTIONS ==============
def send_to_hub(message, allow_relay=True):
    """
    Send message to central hub.
    If hub unresponsive, attempt relay through other wearables.
    """
    radio.send(message)
    
    if not state.hub_responsive and allow_relay:
        # Try relay via known peers
        relay_msg = message.replace("|{}|".format(CENTRAL_HUB_ID), 
                                    "|RELAY|")
        radio.send(relay_msg)

def send_fall_alert():
    """Send fall alert with GPS coordinates"""
    lat, lon = get_simulated_gps()
    accel = get_acceleration_magnitude()
    data = "GPS:{},{};ACC:{}".format(lat, lon, int(accel))
    msg = create_message("FALL", data)
    
    # Send multiple times for reliability
    for _ in range(3):
        send_to_hub(msg)
        sleep(100)
    
    # Visual/audio alert on device
    display.show(Image.SAD)
    for _ in range(5):
        pin0.write_digital(1)  # Buzzer on
        sleep(200)
        pin0.write_digital(0)
        sleep(200)

def send_battery_status():
    """Send battery level to hub"""
    level = get_battery_level()
    msg = create_message("BATT", str(level))
    send_to_hub(msg)

def send_heartbeat():
    """Send heartbeat to maintain connection"""
    current_time = running_time()
    if current_time - state.last_heartbeat_sent >= HEARTBEAT_INTERVAL_MS:
        msg = create_message("HBEAT", str(current_time))
        send_to_hub(msg, allow_relay=False)
        state.last_heartbeat_sent = current_time

def check_hub_connectivity():
    """Monitor if hub is responding"""
    current_time = running_time()
    if current_time - state.last_hub_response > HEARTBEAT_INTERVAL_MS * MAX_MISSED_HEARTBEATS:
        if state.hub_responsive:
            state.hub_responsive = False
            display.scroll("!")  # Alert user of connectivity issue

def process_incoming():
    """Process incoming radio messages"""
    msg = radio.receive()
    if msg:
        parsed = parse_message(msg)
        if parsed:
            # ACK from hub
            if parsed['type'] == 'ACK' and parsed['target'] == DEVICE_ID:
                state.last_hub_response = running_time()
                state.hub_responsive = True
            
            # Heartbeat from another wearable (potential relay)
            elif parsed['type'] == 'HBEAT' and parsed['sender'] != DEVICE_ID:
                state.known_relays.add(parsed['sender'])
            
            # Relay request for another device
            elif parsed['type'] == 'RELAY' and parsed['sender'] != DEVICE_ID:
                if parsed['hops'] < 3:  # Limit relay hops
                    relay_msg = increment_hop_count(msg)
                    relay_msg = relay_msg.replace("|RELAY|", 
                                                  "|{}|".format(CENTRAL_HUB_ID))
                    radio.send(relay_msg)

# ============== TEST MODE ==============
def run_test_mode():
    """
    Test mode activated by holding button A on startup.
    Simulates different scenarios.
    """
    display.scroll("TEST")
    
    while True:
        if button_a.was_pressed():
            # Simulate fall
            display.scroll("FALL")
            send_fall_alert()
        
        if button_b.was_pressed():
            # Show current readings
            mag = get_acceleration_magnitude()
            display.scroll(str(int(mag)))
        
        if button_a.is_pressed() and button_b.is_pressed():
            # Exit test mode
            break
        
        sleep(100)

# ============== MAIN LOOP ==============
def main():
    setup_radio()
    display.show(str(DEVICE_ID))
    sleep(1000)
    
    # Check for test mode
    if button_a.is_pressed():
        run_test_mode()
    
    display.show(Image.HEART_SMALL)
    
    while True:
        # Fall detection (high priority)
        fall_detected = analyze_movement()
        if fall_detected:
            send_fall_alert()
        
        # Process incoming messages
        process_incoming()
        
        # Periodic tasks
        send_heartbeat()
        check_hub_connectivity()
        
        if should_report_battery():
            send_battery_status()
        
        # Visual status indicator
        if not state.is_monitoring_stillness:
            if state.hub_responsive:
                display.show(Image.HEART_SMALL)
            else:
                display.show(Image.CONFUSED)
        
        sleep(SAMPLE_RATE_MS)

# Run
main()
