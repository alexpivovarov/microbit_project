# Data Capture

Use `data_capture_node.py` to capture simple fall records without labeling in-field.

## What it records
- Timestamped accelerometer samples: x/y/z (mg) and magnitude (mg)
- A rolling pre-impact buffer plus a fixed post-impact window
- CSV-like output over serial (USB)

## How to use
1. Set `DEVICE_ID` in `data_capture_node.py` (optional but recommended).
2. Flash `data_capture_node.py` to a micro:bit v2.
3. Open a serial monitor at `115200` baud and save output to a file.

## Controls
- Button A arms a single recording. After impact trigger, it auto-captures ~4s.
- Button B stops the script (you can also press B during capture to stop).

## Capture configuration
Tune these constants in `data_capture_node.py`:
- `DEVICE_ID`
- `IMPACT_THRESHOLD_MG`
- `SAMPLE_RATE_MS`

## Output format
- Header lines start with `#`.
- Per event (one CSV line):
  `device_id,event_id,max_mag,t0_mag,t1_mag,t2_mag,t3_mag,t4_mag`
  - `max_mag`: maximum magnitude during capture window
  - `t0_mag`: magnitude at impact trigger
  - `t1_mag..t4_mag`: magnitudes at ~1s, ~2s, ~3s, ~4s post impact
