"""
Wearable / Node (MicroPython, micro:bit v2)
- Detects falls (impact + stillness)
- Sends fall alerts to the hub
- Minimal implementation for assessment

Flash to each sensor MicroBit (change DEVICE_ID for each)
"""

from microbit import *
import radio
import math

# ============== CONFIGURATION ==============
DEVICE_ID = 1              # CHANGE THIS: 1, 2, etc. for each sensor
HUB_ID = 0
RADIO_GROUP = 42
RADIO_POWER = 7

# Fall detection thresholds
IMPACT_THRESHOLD = 3200        # mg (3.2g) - spike detection
STILLNESS_THRESHOLD = 150      # mg - deviation from 1g
STILLNESS_DURATION_MS = 2000   # 2 seconds still = fall confirmed
POST_IMPACT_WINDOW_MS = 4000   # 4 seconds to detect stillness after impact

SAMPLE_RATE_MS = 50
HEARTBEAT_INTERVAL_MS = 5000   # advertise presence to the hub every 5s

last_data_send = 0
DATA_SEND_INTERVAL_MS = 500  # Send data every 500ms

# ============== STATE ==============
impact_detected = False
impact_time = 0
monitoring_stillness = False
still_start_time = 0
last_heartbeat_sent = 0

# ============== SETUP ==============
radio.on()
radio.config(group=RADIO_GROUP, power=RADIO_POWER)

# ============== FUNCTIONS ==============
def get_magnitude():
    """Total acceleration in milli-g"""
    x = accelerometer.get_x()
    y = accelerometer.get_y()
    z = accelerometer.get_z()
    return math.sqrt(x*x + y*y + z*z)

def create_message(msg_type, data):
    """Create message: TYPE|SENDER|TARGET|DATA"""
    return "{}|{}|{}|{}".format(msg_type, DEVICE_ID, HUB_ID, data)

def send_fall_alert():
    """Send fall alert to hub"""
    accel = int(get_magnitude())
    msg = create_message("FALL", "ACC:{}".format(accel))
    
    # Send multiple times for reliability
    for _ in range(3):
        radio.send(msg)
        sleep(100)
    
    # Visual feedback
    display.show(Image.SAD)
    sleep(2000)

def send_heartbeat():
    """Send a lightweight presence ping so the hub tracks this device"""
    radio.send(create_message("HBEAT", str(running_time())))

def maybe_send_heartbeat():
    """Emit heartbeat at a fixed interval"""
    global last_heartbeat_sent
    now = running_time()
    if last_heartbeat_sent == 0 or now - last_heartbeat_sent >= HEARTBEAT_INTERVAL_MS:
        send_heartbeat()
        last_heartbeat_sent = now

def analyze_movement():
    """
    Fall detection algorithm:
    1. Detect impact spike (>3.2g)
    2. Monitor for stillness after impact
    3. Confirm fall if still for 2 seconds within 4 second window
    """
    global impact_detected, impact_time, monitoring_stillness, still_start_time
    
    now = running_time()
    magnitude = get_magnitude()
    
    if not monitoring_stillness:
        # Phase 1: Looking for impact
        if magnitude > IMPACT_THRESHOLD:
            impact_detected = True
            impact_time = now
            monitoring_stillness = True
            still_start_time = 0
            display.show("!")
            return False
    else:
        # Phase 2: Monitoring for stillness after impact
        deviation = abs(magnitude - 1000)
        
        if deviation < STILLNESS_THRESHOLD:
            # Device is still
            if still_start_time == 0:
                still_start_time = now
            
            # Check if still long enough
            if now - still_start_time >= STILLNESS_DURATION_MS:
                # FALL CONFIRMED
                monitoring_stillness = False
                impact_detected = False
                return True
        else:
            # Movement detected - reset stillness timer
            still_start_time = 0
        
        # Timeout - too long since impact without sustained stillness
        if now - impact_time > POST_IMPACT_WINDOW_MS:
            monitoring_stillness = False
            impact_detected = False
            display.show(Image.HAPPY)
    
    return False

def run_test_mode():
    """Test mode - press A to simulate fall, B to show acceleration"""
    display.scroll("TEST")
    while True:
        maybe_send_heartbeat()
        if button_a.was_pressed():
            display.scroll("FALL")
            send_fall_alert()
        if button_b.was_pressed():
            mag = int(get_magnitude())
            display.scroll(str(mag))
        if button_a.is_pressed() and button_b.is_pressed():
            break
        sleep(100)

# ============== MAIN ==============
display.show(str(DEVICE_ID))
sleep(1000)
maybe_send_heartbeat()  # initial presence beacon

# Hold A on startup for test mode
if button_a.is_pressed():
    run_test_mode()

# Main loop
while True:
    maybe_send_heartbeat()
    fall_detected = analyze_movement()
    
    if fall_detected:
        send_fall_alert()
    
    # Show status
    if not monitoring_stillness:
        display.show(Image.HEART_SMALL)

    now = running_time()
    
    if now - last_data_send >= DATA_SEND_INTERVAL_MS:
        last_data_send = now
        mag = int(get_magnitude())
        msg = create_message("DATA", "ACC:{}".format(mag))
        radio.send(msg)
    
    sleep(SAMPLE_RATE_MS)
