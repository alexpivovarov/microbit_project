# Radio Message Protocol

## Format
All messages are UTF-8 strings with pipe separators:

TYPE|SENDER_ID|TARGET_ID|DATA|HOP_COUNT

### Field definitions
- TYPE: Message type (FALL, BATT, HBEAT, ACK, RELAY)
- SENDER_ID: Integer device ID of the sender
- TARGET_ID: Integer device ID of the intended recipient (0 for hub)
- DATA: Message payload, type-specific
- HOP_COUNT: Integer hop counter used for relays

## Message types

### FALL
- DATA: GPS:lat,lon;ACC:mg
- Example: FALL|1|0|GPS:53.8008,-1.5491;ACC:2480|0

### BATT
- DATA: percentage (0-100)
- Example: BATT|2|0|97.5|0

### HBEAT
- DATA: timestamp in ms (running_time)
- Example: HBEAT|3|0|123456|0

### ACK
- DATA: OK
- Example: ACK|0|1|OK|0

### RELAY (planned)
- DATA: original message or a relay wrapper
- Current implementation is experimental; see docs/LIMITATIONS.md.

## Size limits
- micro:bit radio defaults to a 32 byte payload.
- This project configures radio.config(length=251) on both hub and wearables.
- Keep payloads short for reliability and to avoid truncation.

## Relay and hop count
- HOP_COUNT should increment on each relay.
- The wearable code limits relays to 3 hops to prevent loops.
