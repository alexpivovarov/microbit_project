"""
Fall Detection Desktop Client
==============================
Reads data from central_hub MicroBit via serial USB.
Performs analysis and provides live visualisation.

This completes the architecture:
    [Sensors] --radio--> [Central Hub] --serial--> [Desktop Client]
                                                        |
                                                        v
                                              Analysis & Visualisation

Requirements:
    pip install pyserial matplotlib

Usage:
    python desktop_client.py
"""

import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from datetime import datetime
import sys
import re

# ===== CONFIGURATION =====
BAUD_RATE = 115200
MAX_POINTS = 100  # Number of points on graph
FALL_THRESHOLD_MG = 3200

# ===== DATA STORAGE =====
sensor_data = {}  # sensor_id -> {'times': deque, 'values': deque}
fall_events = []  # List of fall event records
stats = {
    'total_messages': 0,
    'fall_alerts': 0,
    'impacts_detected': 0,
    'devices_seen': set()
}

# ===== FIND MICROBIT =====
def find_microbit_port():
    """Auto-detect MicroBit serial port"""
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        desc = port.description.lower()
        hwid = str(port.hwid)
        if 'mbed' in desc or 'microbit' in desc or '0204' in hwid:
            return port.device
    
    print("Available ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
    
    return None

def connect_serial():
    """Connect to MicroBit hub"""
    port = find_microbit_port()
    
    if port is None:
        print("MicroBit not found automatically.")
        port = input("Enter port (e.g., COM3 or /dev/ttyACM0): ").strip()
    
    print(f"Connecting to {port}...")
    
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        print(f"Connected successfully!")
        return ser
    except serial.SerialException as e:
        print(f"Error: {e}")
        sys.exit(1)

# ===== MESSAGE PARSING =====
def parse_hub_message(line):
    """
    Parse messages from central_hub.py
    
    Expected formats from your hub:
    - "SENSOR_ID,STATUS,MAGNITUDE" (if simple format)
    - Or parse the protocol format: "TYPE|SENDER|TARGET|DATA|HOPS"
    
    Adjust this based on your actual central_hub.py output format
    """
    line = line.strip()
    if not line:
        return None
    
    # Try simple CSV format: SENSOR_ID,STATUS,MAGNITUDE
    parts = line.split(',')
    if len(parts) >= 3:
        try:
            sensor_id = int(parts[0])
            status = parts[1].strip()
            magnitude = int(parts[2])
            return {'sensor_id': sensor_id, 'status': status, 'magnitude': magnitude}
        except ValueError:
            pass
    
    # Try protocol format: TYPE|SENDER|TARGET|DATA|HOPS
    parts = line.split('|')
    if len(parts) >= 4:
        try:
            msg_type = parts[0]
            sender = int(parts[1])
            data = parts[3]
            
            # Extract magnitude from data if present
            magnitude = 1000  # default
            if 'ACC:' in data:
                match = re.search(r'ACC:(\d+)', data)
                if match:
                    magnitude = int(match.group(1))
            
            status = 'FALL' if msg_type == 'FALL' else 'OK'
            return {'sensor_id': sender, 'status': status, 'magnitude': magnitude, 'raw': line}
        except (ValueError, IndexError):
            pass
    
    # Log unrecognised format for debugging
    if line and not line.startswith('='):  # Ignore separator lines
        print(f"[DEBUG] Unrecognised: {line[:50]}")
    
    return None

# ===== ANALYSIS =====
def ensure_sensor_data(sensor_id):
    """Create data storage for new sensor"""
    if sensor_id not in sensor_data:
        sensor_data[sensor_id] = {
            'times': deque(maxlen=MAX_POINTS),
            'values': deque(maxlen=MAX_POINTS)
        }

def analyse_message(parsed):
    """Perform analysis on incoming data"""
    if not parsed:
        return
    
    sensor_id = parsed['sensor_id']
    status = parsed['status']
    magnitude = parsed['magnitude']
    timestamp = datetime.now()
    
    # Update statistics
    stats['total_messages'] += 1
    stats['devices_seen'].add(sensor_id)
    
    # Store data for plotting
    ensure_sensor_data(sensor_id)
    sensor_data[sensor_id]['times'].append(timestamp)
    sensor_data[sensor_id]['values'].append(magnitude)
    
    # Handle fall events
    if status == 'FALL':
        stats['fall_alerts'] += 1
        fall_events.append({
            'time': timestamp,
            'sensor_id': sensor_id,
            'magnitude': magnitude
        })
        print_fall_alert(sensor_id, magnitude, timestamp)
    
    elif status == 'IMPACT':
        stats['impacts_detected'] += 1
        print(f"[{timestamp.strftime('%H:%M:%S')}] Sensor {sensor_id}: Impact detected ({magnitude} mg)")

def print_fall_alert(sensor_id, magnitude, timestamp):
    """Print formatted fall alert"""
    print()
    print("=" * 50)
    print("!!!  FALL DETECTED  !!!")
    print("=" * 50)
    print(f"  Sensor ID:    {sensor_id}")
    print(f"  Time:         {timestamp.strftime('%H:%M:%S')}")
    print(f"  Impact Force: {magnitude} mg ({magnitude/1000:.2f}g)")
    print("=" * 50)
    print()

def print_statistics():
    """Print current session statistics"""
    print()
    print("-" * 40)
    print("  SESSION STATISTICS")
    print("-" * 40)
    print(f"  Messages received: {stats['total_messages']}")
    print(f"  Devices seen:      {sorted(stats['devices_seen'])}")
    print(f"  Fall alerts:       {stats['fall_alerts']}")
    print(f"  Impacts detected:  {stats['impacts_detected']}")
    print("-" * 40)
    print()

# ===== VISUALISATION =====
def setup_plot():
    """Create matplotlib figure for live visualisation"""
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    
    fig.suptitle('Fall Detection System - Live Monitor', fontsize=14, fontweight='bold')
    
    lines = {}
    colors = ['#2196F3', '#FF9800', '#4CAF50', '#E91E63']
    
    for i, ax in enumerate(axes):
        ax.set_title(f'Sensor {i+1} - Accelerometer')
        ax.set_ylabel('Acceleration (mg)')
        ax.set_ylim(0, 4000)
        ax.axhline(
            y=FALL_THRESHOLD_MG,
            color='red',
            linestyle='--',
            alpha=0.7,
            label='Fall threshold ({}mg)'.format(FALL_THRESHOLD_MG),
        )
        ax.axhline(y=1000, color='green', linestyle=':', alpha=0.7, label='Rest state (1000mg)')
        ax.legend(loc='upper right', fontsize=8)
        
        line, = ax.plot([], [], color=colors[i % len(colors)], linewidth=1.5)
        lines[i + 1] = line  # Sensor IDs typically start at 1
    
    axes[-1].set_xlabel('Time (seconds)')
    plt.tight_layout()
    
    return fig, axes, lines

def update_plot(frame, ser, axes, lines):
    """Animation update - read serial and update graphs"""
    
    # Read all available serial data
    while ser.in_waiting:
        try:
            raw = ser.readline()
            line = raw.decode('utf-8', errors='ignore').strip()
            if line:
                parsed = parse_hub_message(line)
                if parsed:
                    analyse_message(parsed)
        except serial.SerialException:
            pass
    
    # Update each sensor's plot
    for sensor_id, line_obj in lines.items():
        if sensor_id in sensor_data:
            data = sensor_data[sensor_id]
            if len(data['times']) > 1:
                times = list(data['times'])
                values = list(data['values'])
                
                t0 = times[0]
                rel_times = [(t - t0).total_seconds() for t in times]
                
                line_obj.set_data(rel_times, values)
                
                # Update axis limits
                ax_idx = sensor_id - 1  # Convert sensor_id to axis index
                if ax_idx < len(axes):
                    axes[ax_idx].set_xlim(
                        rel_times[0], 
                        max(rel_times[-1], rel_times[0] + 10)
                    )
    
    return list(lines.values())

# ===== MAIN =====
def main():
    print()
    print("=" * 50)
    print("  FALL DETECTION - DESKTOP CLIENT")
    print("=" * 50)
    print()
    print("Architecture:")
    print("  [Sensors] --radio--> [Hub] --USB--> [This Client]")
    print()
    
    # Connect
    ser = connect_serial()
    ser.reset_input_buffer()
    
    print()
    print("Listening for data...")
    print("Close the plot window to exit.")
    print("-" * 50)
    
    # Setup visualisation
    fig, axes, lines = setup_plot()
    
    # Start animation
    ani = FuncAnimation(
        fig,
        update_plot,
        fargs=(ser, axes, lines),
        interval=100,
        blit=False,
        cache_frame_data=False
    )
    
    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("\nConnection closed.")
        print_statistics()
        
        # Final summary
        if fall_events:
            print("\nFALL EVENTS LOG:")
            for event in fall_events:
                print(f"  - Sensor {event['sensor_id']} at {event['time'].strftime('%H:%M:%S')} ({event['magnitude']} mg)")

if __name__ == "__main__":
    main()
