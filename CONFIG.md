# Configuration Guide

Python-first configuration reference for the Meshtastic MQTT Proxy fork.

## Interface Settings

### TCP

```env
INTERFACE_TYPE=tcp
TCP_NODE_HOST=127.0.0.1
TCP_NODE_PORT=4404
TCP_TIMEOUT=300
```

Use this when you connect through a virtual node or another Meshtastic TCP endpoint.

### Serial

```env
INTERFACE_TYPE=serial
SERIAL_PORT=auto
```

Use this for direct USB access to a Meshtastic device. `SERIAL_PORT=auto` tries to select a Meshtastic/Seeed/TinyUSB USB serial port automatically. On macOS, TinyUSB/CDC devices commonly appear as `/dev/cu.usbmodem*`; on Windows the same auto-detection returns the matching `COMx` port. Explicit values such as `/dev/cu.usbmodem101` or `COM7` also work.

## Core Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `INTERFACE_TYPE` | string | `tcp` | `tcp` or `serial` |
| `LOG_LEVEL` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `VERBOSE` | boolean | `false` | Verbose console output for RX/TX/MQTT details |
| `ENV_HOT_RELOAD_ENABLED` | boolean | `true` | Restart the proxy when `.env` changes on disk |
| `ENV_HOT_RELOAD_INTERVAL_SECONDS` | float | `2` | Poll interval for checking `.env` changes |
| `TCP_NODE_HOST` | string | `localhost` | TCP node host |
| `TCP_NODE_PORT` | integer | `4403` | TCP node port |
| `TCP_TIMEOUT` | integer | `300` | TCP timeout in seconds |
| `SERIAL_PORT` | string | `/dev/ttyUSB0` | Serial device path, or `auto` for USB auto-detection |
| `CONFIG_WAIT_TIMEOUT` | integer | `60` | Wait time for node config |
| `POLL_INTERVAL` | integer | `1` | Poll interval while waiting for config |

## Verbose Console Mode

You can enable a more detailed console in two ways:

```cmd
start-mqtt-proxy.cmd --verbose
```

or

```env
VERBOSE=true
```

The command line also accepts the alias `--verbode`.

## .env Hot Reload

When you start via `start-mqtt-proxy.cmd`, the wrapper restarts the Python process automatically after `.env` changes.

Example:

```env
ENV_HOT_RELOAD_ENABLED=true
ENV_HOT_RELOAD_INTERVAL_SECONDS=2
```

## Listener Mirror

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MQTT_LISTENER_ENABLED` | boolean | `false` | Enable JSON mirroring of received packets |
| `MQTT_LISTENER_PORTS` | string | `""` | Optional comma-separated `decoded.portnum` allowlist |
| `MQTT_LISTENER_EXCLUDE_PORTS` | string | `""` | Optional comma-separated `decoded.portnum` blocklist |
| `MQTT_LISTENER_DM_ONLY` | boolean | `false` | Only mirror direct messages |
| `MQTT_LISTENER_GROUP_ONLY` | boolean | `false` | Only mirror broadcast/group messages |
| `MQTT_LISTENER_TEXT_ONLY` | boolean | `false` | Only mirror text-like messages |
| `MQTT_LISTENER_RETAIN` | boolean | `true` | Publish mirrored listener messages with the MQTT retained flag |
| `MQTT_LISTENER_INCLUDE_RAW` | boolean | `true` | Include the full packet object in mirrored JSON |
| `MQTT_LISTENER_PUBLISH_ALL` | boolean | `true` | Publish to `<root>/proxy/rx/!<gateway>/all` |
| `MQTT_LISTENER_PUBLISH_PORT` | boolean | `true` | Publish to `<root>/proxy/rx/!<gateway>/port/<PORTNUM>` |
| `MQTT_LISTENER_PUBLISH_SCOPE` | boolean | `true` | Publish to `<root>/proxy/rx/!<gateway>/scope/<dm|group>` |
| `MQTT_ACK_RETAIN` | boolean | `true` | Publish ACK lifecycle messages on `<root>/proxy/ack/!<gateway>/<client_ref>` with retained flag |
| `MQTT_PUBLISH_EXPIRY_ENABLED` | boolean | `false` | Enable MQTT 5 Message Expiry on broker publishes |
| `MQTT_PUBLISH_EXPIRY_SECONDS` | integer | `86400` | Message expiry time in seconds for broker publishes |

Example:

```env
MQTT_LISTENER_ENABLED=true
MQTT_LISTENER_PORTS=TEXT_MESSAGE_APP,POSITION_APP,TELEMETRY_APP
MQTT_LISTENER_EXCLUDE_PORTS=ROUTING_APP,ADMIN_APP
MQTT_LISTENER_DM_ONLY=false
MQTT_LISTENER_GROUP_ONLY=false
MQTT_LISTENER_TEXT_ONLY=false
MQTT_LISTENER_RETAIN=true
MQTT_LISTENER_INCLUDE_RAW=false
MQTT_LISTENER_PUBLISH_ALL=true
MQTT_LISTENER_PUBLISH_PORT=true
MQTT_LISTENER_PUBLISH_SCOPE=true
MQTT_ACK_RETAIN=true
MQTT_PUBLISH_EXPIRY_ENABLED=true
MQTT_PUBLISH_EXPIRY_SECONDS=86400
```

Published topics:

```text
<root>/proxy/rx/!<gateway>/all
<root>/proxy/rx/!<gateway>/port/<PORTNUM>
<root>/proxy/rx/!<gateway>/scope/dm
<root>/proxy/rx/!<gateway>/scope/group
```

The listener is additive. The original bidirectional `mqttClientProxyMessage` path remains active.

If `MQTT_PUBLISH_EXPIRY_ENABLED=true`, the proxy uses MQTT 5 for broker communication and attaches a Message Expiry Interval to its PUBLISH packets. This controls how long queued or retained broker messages persist before the broker deletes them.

Example to avoid duplicate storage and keep only the group/direct scope topics:

```env
MQTT_LISTENER_PUBLISH_ALL=false
MQTT_LISTENER_PUBLISH_PORT=false
MQTT_LISTENER_PUBLISH_SCOPE=true
```

Common Meshtastic `portnum` values worth filtering:

- `TEXT_MESSAGE_APP`
- `TELEMETRY_APP`
- `POSITION_APP`
- `NODEINFO_APP`
- `NEIGHBORINFO_APP`
- `ROUTING_APP`
- `TRACEROUTE_APP`
- `WAYPOINT_APP`
- `STORE_FORWARD_APP`
- `RANGE_TEST_APP`
- `ADMIN_APP`

## Periodic Node List Export

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MQTT_NODE_LIST_ENABLED` | boolean | `true` | Enable periodic node list snapshots |
| `MQTT_NODE_LIST_INTERVAL_SECONDS` | integer | `3600` | Publish interval in seconds |
| `MQTT_NODE_LIST_RETAIN` | boolean | `true` | Publish retained MQTT snapshots |

Published topics:

```text
<root>/proxy/nodes/!<gateway>/all
<root>/proxy/nodes/!<gateway>/index
```

`all` contains the full snapshot with raw node records. `index` contains a compact list intended for selector UIs and targeted send workflows.

## Plaintext MQTT Command Topics

The proxy subscribes to simple plaintext command topics below the current MQTT root:

```text
<root>/proxy/send/!<gateway>/group/<channelIndex>
<root>/proxy/send/!<gateway>/direct/!<nodeId>
```

Examples:

```text
msh/EU_868/proxy/send/!49b65bc8/group/0
msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b
```

Payload options:

Plain text:

```text
Hallo Gruppe 0
```

JSON:

```json
{"text":"Hallo","channel":0,"want_ack":true,"hop_limit":3}
```

Rules:

- Group topics use the channel index from the topic.
- Direct topics default to channel `0`.
- JSON can override `channel`, `want_ack`, and `hop_limit`.

For ACK correlation, include a `client_ref` in the JSON payload:

```json
{"text":"Hallo direkt","channel":0,"want_ack":true,"client_ref":"msg-001"}
```

ACK lifecycle topics:

```text
<root>/proxy/ack/!<gateway>/<client_ref>
```

ACK retain setting:

```env
MQTT_ACK_RETAIN=true
```

MQTT 5 publish expiry:

```env
MQTT_PUBLISH_EXPIRY_ENABLED=true
MQTT_PUBLISH_EXPIRY_SECONDS=86400
```

This is especially useful for retained JSON topics when the last known state should disappear automatically after a day.

Without `client_ref`, the proxy does not request or publish an ACK path even if `want_ack=true` is present.

The proxy keeps ACK correlation entries only in memory and expires them after 60 seconds.

## Queue and Forwarding

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MESH_TRANSMIT_DELAY` | float | `0.01` | Delay between outgoing radio packets |
| `MESH_MAX_QUEUE_SIZE` | integer | `5000` | Outgoing queue size |
| `MESH_ALLOW_UNCONFIGURED_CHANNELS` | boolean | `true` | Allow forwarding unknown channel names to the radio for virtual channel passthrough |
| `MQTT_FORWARD_RETAINED` | boolean | `false` | Forward retained MQTT packets |

## Health and Recovery

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HEALTH_CHECK_ACTIVITY_TIMEOUT` | integer | `300` | Silence threshold before probing |
| `HEALTH_CHECK_PROBE_INTERVAL` | integer | half of activity timeout | Probe interval |
| `HEALTH_CHECK_STATUS_INTERVAL` | integer | `60` | Status log cadence |
| `MQTT_RECONNECT_DELAY` | integer | `5` | Delay before MQTT reconnect |

Behavior:

- If MQTT disconnects repeatedly, the process exits.
- If the radio goes silent for too long and probing fails, the process exits.
- If the Meshtastic connection is lost and does not recover, the process exits.

This is meant to work well with manual restarts or an external supervisor.

## Extra MQTT Roots

```env
EXTRA_MQTT_ROOTS=msh/US/NC:NC,msh/US/OH:Ohio
```

This subscribes to additional encrypted MQTT roots and rewrites them into virtual channel names for passive monitoring without RF crosstalk.

## Node MQTT Configuration

The connected node should expose MQTT settings like:

```text
mqtt.enabled: true
mqtt.proxy_to_client_enabled: true
mqtt.address: <broker>
mqtt.username: <user>
mqtt.password: <password>
```

The proxy reads these settings from the node and uses them for the broker connection.

## Example `.env`

```env
INTERFACE_TYPE=serial
SERIAL_PORT=auto
LOG_LEVEL=INFO
MQTT_LISTENER_ENABLED=true
MQTT_LISTENER_PORTS=
MQTT_LISTENER_DM_ONLY=false
MQTT_LISTENER_GROUP_ONLY=false
MQTT_LISTENER_TEXT_ONLY=false
```
