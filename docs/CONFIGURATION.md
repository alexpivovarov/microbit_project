# Configuration Reference

## wearable_device.py (node/wearable)

### Identity and radio
- DEVICE_ID: unique wearable ID (integer)
- HUB_ID: hub ID (default 0)
- RADIO_GROUP: radio group shared by all devices
- RADIO_POWER: 0-7 transmit power
- RADIO_LENGTH: radio packet length

### Fall detection
- IMPACT_THRESHOLD: acceleration spike threshold in mg
- STILLNESS_THRESHOLD: allowed deviation from 1g in mg
- STILLNESS_DURATION_MS: stillness window after impact
- SAMPLE_RATE_MS: accelerometer sampling interval
- POST_IMPACT_WINDOW_MS: max time to confirm stillness after an impact

### Battery and GPS simulation
- BATTERY_REPORT_INTERVAL_MS: interval between battery reports
- SIMULATED_BATTERY_DRAIN: percent drained per report
- BASE_LAT, BASE_LON: base coordinates for simulated GPS

### Heartbeat and relay
- HEARTBEAT_INTERVAL_MS: heartbeat interval
- MAX_MISSED_HEARTBEATS: missed ACKs before marking hub as unresponsive
- MAX_HOPS: hop limit for relayed messages

## central_hub.py

### Identity and radio
- HUB_ID: hub ID (default 0)
- RADIO_GROUP: radio group shared by all devices
- RADIO_POWER: 0-7 transmit power
- RADIO_LENGTH: radio packet length

### Timing
- DEVICE_TIMEOUT_MS: time before a device is considered offline
- ALERT_DISPLAY_MS: how long to show alert on the display
- STATUS_PRINT_INTERVAL: interval for periodic status/health logs
- MAX_HOPS: hop limit for relayed messages

## Notes
- See docs/LIMITATIONS.md for current gaps (e.g., ACKs are not relayed).
