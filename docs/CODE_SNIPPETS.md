# Assessment Evidence: Core Snippets (Multiple Nodes → Hub → Desktop)

This document contains *only* the snippets needed to show evidence of meeting the assessment criteria:
1) proof of concept of multiple sensors (nodes)
2) proof of radio communication
3) proof of desktop visualisation of sensor data via the hub (node → hub → USB serial → desktop)

---

## 1) Proof of concept: multiple sensors (nodes)

### 1.1 Wearables are uniquely identifiable (`wearable_device.py`)
```python
DEVICE_ID = 1              # CHANGE THIS: 1, 2, etc. for each sensor
HUB_ID = 0
```
Each physical wearable is flashed with the same code but a different `DEVICE_ID` (e.g., node 1 and node 2).

```python
display.show(str(DEVICE_ID))
```
On boot, each wearable shows its ID on the LED matrix so you can verify which node is which during the demo.

### 1.2 Hub tracks multiple devices (`central_hub.py`)
```python
class HubState:
    def __init__(self):
        self.devices = {}
```
```python
def get_or_create_device(device_id):
    if device_id not in state.devices:
        state.devices[device_id] = DeviceInfo(device_id)
    return state.devices[device_id]

def update_device_seen(device_id):
    device = get_or_create_device(device_id)
    device.last_seen = running_time()
    return device
```
The hub keeps a registry of devices keyed by `device_id`, which enables multiple nodes to be tracked at the same time.

### 1.3 Hub prints the set of nodes it has seen (`central_hub.py`)
```python
def handle_heartbeat(sender, data):
    was_known = sender in state.devices
    update_device_seen(sender)
    if not was_known:
        print("Device {} joined".format(sender))
```
When multiple wearables start up, the hub prints “Device 1 joined”, “Device 2 joined”, etc.

```python
if button_a.was_pressed():
    print("Devices: {}".format(list(state.devices.keys())))
```
Pressing button A prints the list of known device IDs as explicit “multiple sensors” evidence.

---

## 2) Proof of radio communication (node ↔ hub)

### 2.1 Both sides configure radio (`wearable_device.py`, `central_hub.py`)
```python
radio.on()
radio.config(group=RADIO_GROUP, power=RADIO_POWER)
```
Nodes and hub share the same `RADIO_GROUP`, enabling communication.

### 2.2 Node sends structured radio messages (`wearable_device.py`)
```python
def create_message(msg_type, data):
    return "{}|{}|{}|{}".format(msg_type, DEVICE_ID, HUB_ID, data)
```
```python
def send_heartbeat():
    radio.send(create_message("HBEAT", str(running_time())))

if now - last_data_send >= DATA_SEND_INTERVAL_MS:
    last_data_send = now
    mag = int(get_magnitude())
    msg = create_message("DATA", "ACC:{}".format(mag))
    radio.send(msg)
```
The wearable transmits messages that include the sender (`DEVICE_ID`), destination (`HUB_ID`), and payload (`ACC:...`).

### 2.3 Hub receives + dispatches radio messages (`central_hub.py`)
```python
msg = radio.receive()
if msg:
    process_message(msg)
```
```python
def parse_message(msg):
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
```
```python
if msg_type == 'FALL':
    handle_fall_alert(sender, data)
elif msg_type == 'HBEAT':
    handle_heartbeat(sender, data)
elif msg_type == 'IMPACT':
    handle_impact(sender, data)
elif msg_type == 'DATA':
    accel = 0
    if "ACC:" in data:
        try:
            accel = int(data.split("ACC:")[1])
        except:
            pass
    print("{},DATA,{}".format(sender, accel))
```
The hub receives a radio packet, parses it, and routes it by `msg_type` (FALL/HBEAT/IMPACT/DATA).

---

## 3) Proof of desktop visualisation via the hub (node → hub → USB → desktop)

### 3.1 Hub bridges radio → USB serial using CSV (`central_hub.py`)
```python
print("{},DATA,{}".format(sender, accel))
print("{},IMPACT,{}".format(sender, accel))
print("{},FALL,{}".format(sender, accel))
```
The hub outputs one CSV line per reading/event over USB serial:
`sensor_id,status,magnitude`

Example lines (what the desktop client consumes):
- `1,DATA,1008`
- `2,IMPACT,3470`
- `2,FALL,3470`

### 3.2 Desktop reads hub serial (not radio) and parses CSV (`desktop_client.py`)
```python
ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
```
```python
parts = line.split(',')
if len(parts) >= 3:
    try:
        sensor_id = int(parts[0])
        status = parts[1].strip()
        magnitude = int(parts[2])
        return {'sensor_id': sensor_id, 'status': status, 'magnitude': magnitude}
    except ValueError:
        pass
```
This shows the desktop client uses USB serial from the hub to ingest sensor data.

### 3.3 Desktop stores data per sensor and plots live (`desktop_client.py`)
```python
sensor_data = {}  # sensor_id -> {'times': deque, 'values': deque}

def ensure_sensor_data(sensor_id):
    if sensor_id not in sensor_data:
        sensor_data[sensor_id] = {
            'times': deque(maxlen=MAX_POINTS),
            'values': deque(maxlen=MAX_POINTS)
        }
```
```python
fig, axes = plt.subplots(2, 1, figsize=(10, 8))
lines = {}
for i, ax in enumerate(axes):
    line, = ax.plot([], [], linewidth=1.5)
    lines[i + 1] = line  # sensor IDs 1 and 2
```
```python
while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    parsed = parse_hub_message(line)
    if parsed:
        analyse_message(parsed)
```
```python
ani = FuncAnimation(fig, update_plot, fargs=(ser, axes, lines), interval=100)
plt.show()
```
The plot updates continuously from hub serial data, providing live desktop visualisation for multiple nodes.
