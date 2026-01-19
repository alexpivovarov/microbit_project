"""
Data Capture Node (MicroPython, micro:bit v2)

Purpose (minimal, per your flow):
- Press A to arm a single recording.
- When an impact crosses the threshold, capture:
  field1: max impact magnitude during the capture window
  field2: magnitude at impact detection (t0)
  field3-6: magnitudes at ~1s, ~2s, ~3s, ~4s after impact
- Press B to stop the script.

Output:
- CSV line: device_id,event_id,max_mag,t0_mag,t1_mag,t2_mag,t3_mag,t4_mag
"""

from microbit import *
import math

# ============== CONFIGURATION ==============
DEVICE_ID = 1
IMPACT_THRESHOLD_MG = 3200
SAMPLE_RATE_MS = 50

# ============== INTERNALS ==============
THRESH2 = IMPACT_THRESHOLD_MG * IMPACT_THRESHOLD_MG


def read_mag():
    x = accelerometer.get_x()
    y = accelerometer.get_y()
    z = accelerometer.get_z()
    return int(math.sqrt(x * x + y * y + z * z))


def capture_once(event_id):
    """
    Wait for an impact, then capture t0 + 4 seconds of samples,
    recording magnitudes at 1s intervals and the maximum observed.
    """
    display.show("A")  # armed

    # Wait for impact trigger
    while True:
        if button_b.was_pressed():
            return False  # stop script
        mag = read_mag()
        if mag * mag > THRESH2:
            break
        sleep(SAMPLE_RATE_MS)

    start_t = running_time()
    t0_mag = mag
    max_mag = mag
    buckets = [None, None, None, None]  # for ~1s,2s,3s,4s marks
    next_mark = 1

    # Sample for ~4 seconds post impact
    while running_time() - start_t <= 4000:
        if button_b.was_pressed():
            return False  # stop script

        mag = read_mag()
        if mag > max_mag:
            max_mag = mag

        elapsed = running_time() - start_t
        # Set bucket when we cross each second mark
        if next_mark <= 4 and elapsed >= next_mark * 1000:
            buckets[next_mark - 1] = mag
            next_mark += 1

        sleep(SAMPLE_RATE_MS)

    # Fill any missing buckets with last known mag
    last_val = buckets[0] if buckets[0] is not None else t0_mag
    for i in range(4):
        if buckets[i] is None:
            buckets[i] = last_val
        last_val = buckets[i]

    # Emit CSV line
    print("{},{},{},{},{},{},{},{}".format(
        DEVICE_ID,
        event_id,
        max_mag,
        t0_mag,
        buckets[0],
        buckets[1],
        buckets[2],
        buckets[3],
    ))
    return True


def main():
    print("# data_capture_node")
    print("# columns: device_id,event_id,max_mag,t0_mag,t1_mag,t2_mag,t3_mag,t4_mag")
    event_id = 0
    display.show("-")

    while True:
        # Press A to arm a new recording
        if button_a.was_pressed():
            event_id += 1
            ok = capture_once(event_id)
            if not ok:
                break
            display.show("-")

        if button_b.was_pressed():
            break

        sleep(50)

    display.show(Image.NO)


main()

