# Meshtastic MQTT Proxy

Python-first MQTT proxy for Meshtastic nodes.

This fork is focused on a simple local Python installation with `venv`, direct USB or TCP connectivity to a Meshtastic node, and practical MQTT tooling for monitoring and sending messages.

## Purpose / Zweck

**English**

This fork keeps the original bidirectional `mqttClientProxyMessage` workflow, but adds a USB-first workflow for local Meshtastic setups. The proxy reads MQTT settings from the node configuration, mirrors received mesh traffic to dedicated JSON MQTT topics, and accepts simple plaintext MQTT send commands for group and direct messages.

**Deutsch**

Dieser Fork behält den ursprünglichen bidirektionalen `mqttClientProxyMessage`-Workflow bei, ergänzt ihn aber um einen praxisnahen USB-First-Ansatz für lokale Meshtastic-Setups. Der Proxy liest die MQTT-Einstellungen aus der Node-Konfiguration, spiegelt empfangenen Mesh-Verkehr auf eigene JSON-MQTT-Topics und akzeptiert einfache Plaintext-MQTT-Befehle für Gruppen- und Direktnachrichten.

## Features

- Bidirectional MQTT proxying between node and broker
- TCP and Serial support
- Listener-based JSON mirroring via `meshtastic.receive`
- Configurable listener target topics to avoid duplicate MQTT storage
- Listener messages can be published retained by config and are retained by default
- ACK lifecycle topics have their own retained-message switch
- Plaintext MQTT send commands for group and direct messages
- TLS support based on node MQTT config
- Channel uplink/downlink filtering based on node settings
- Virtual channel support via `EXTRA_MQTT_ROOTS`
- Windows-friendly startup scripts

## Requirements

- Python 3.10+
- A Meshtastic node reachable via TCP or Serial
- MQTT configured on the node

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/ewerker/mqtt-proxy.git
cd mqtt-proxy
```

2. Create a virtual environment:

```bash
python -m venv .venv
```

3. Install dependencies:

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Create a local `.env` from [\.env.example](C:\Users\richt\Documents\Codex\mqtt%20Proxy\mqtt-proxy\.env.example) and adjust your interface settings:

```env
INTERFACE_TYPE=serial
SERIAL_PORT=COM7
LOG_LEVEL=INFO
MQTT_LISTENER_ENABLED=true
```

5. Start the proxy:

```cmd
start-mqtt-proxy.cmd
```

When `.env` changes on disk, `start-mqtt-proxy.cmd` now restarts the proxy automatically so the new values take effect without manual intervention.

For a more chatty console with detailed receive/send logs, start it with:

```cmd
start-mqtt-proxy.cmd --verbose
```

## Windows Start

The preferred Windows entry point is [start-mqtt-proxy.cmd](C:\Users\richt\Documents\Codex\mqtt%20Proxy\mqtt-proxy\start-mqtt-proxy.cmd). It loads `.env` and starts the proxy from `.venv` without requiring PowerShell script execution.
It also watches for `.env` changes and restarts the Python process automatically when the file changes.

Direct Python start is also possible:

```powershell
.\.venv\Scripts\python.exe mqtt-proxy.py --interface serial --serial-port COM7
```

Verbose mode also works here:

```powershell
.\.venv\Scripts\python.exe mqtt-proxy.py --interface serial --serial-port COM7 --verbose
```

## Configuration

Core variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `INTERFACE_TYPE` | `tcp` | `tcp` or `serial` |
| `TCP_NODE_HOST` | `localhost` | TCP node host |
| `TCP_NODE_PORT` | `4403` | TCP node port |
| `SERIAL_PORT` | `/dev/ttyUSB0` | Serial port |
| `LOG_LEVEL` | `INFO` | Log level |
| `MQTT_LISTENER_ENABLED` | `false` | Enable JSON listener mirror |
| `MQTT_LISTENER_PORTS` | `""` | Optional `decoded.portnum` allowlist |
| `MQTT_LISTENER_EXCLUDE_PORTS` | `""` | Optional `decoded.portnum` blocklist |
| `MQTT_LISTENER_DM_ONLY` | `false` | Only mirror direct messages |
| `MQTT_LISTENER_GROUP_ONLY` | `false` | Only mirror group traffic |
| `MQTT_LISTENER_TEXT_ONLY` | `false` | Only mirror text-like messages |
| `MQTT_LISTENER_INCLUDE_RAW` | `true` | Include full packet payload in mirrored JSON |

See [CONFIG.md](C:\Users\richt\Documents\Codex\mqtt%20Proxy\mqtt-proxy\CONFIG.md) for the full reference.

A copyable bundle example is included at [bundle/.env.example](C:\Users\richt\Documents\Codex\mqtt%20Proxy\mqtt-proxy\bundle\.env.example).

## Listener Topics

When the listener is enabled, received packets are mirrored to:

- `msh/<region>/proxy/rx/!<gateway>/all`
- `msh/<region>/proxy/rx/!<gateway>/port/<PORTNUM>`
- `msh/<region>/proxy/rx/!<gateway>/scope/dm`
- `msh/<region>/proxy/rx/!<gateway>/scope/group`

The listener is additive. The original broker-to-node and node-to-broker proxy path remains active.

Useful Meshtastic port filters include:

- `TEXT_MESSAGE_APP`
- `TELEMETRY_APP`
- `POSITION_APP`
- `NODEINFO_APP`
- `NEIGHBORINFO_APP`
- `TRACEROUTE_APP`
- `WAYPOINT_APP`
- `STORE_FORWARD_APP`
- `RANGE_TEST_APP`
- `ROUTING_APP`
- `ADMIN_APP`

Example filter setup:

```env
MQTT_LISTENER_PORTS=TEXT_MESSAGE_APP,TELEMETRY_APP,POSITION_APP,NODEINFO_APP
MQTT_LISTENER_EXCLUDE_PORTS=ROUTING_APP,ADMIN_APP
MQTT_LISTENER_INCLUDE_RAW=false
```

## Periodic Node List

The proxy also publishes a retained node list snapshot for selector UIs and remote tooling. By default this happens every 3600 seconds and can be changed in `.env`.

Topics:

- `msh/<region>/proxy/nodes/!<gateway>/all`
- `msh/<region>/proxy/nodes/!<gateway>/index`

The `all` topic contains a full snapshot with raw node data. The `index` topic contains a compact list for UI pickers and quick receiver selection.

Relevant configuration:

```env
MQTT_NODE_LIST_ENABLED=true
MQTT_NODE_LIST_INTERVAL_SECONDS=3600
MQTT_NODE_LIST_RETAIN=true
```

## Plaintext MQTT Send Commands

The proxy subscribes to:

- `msh/<region>/proxy/send/group/<channelIndex>`
- `msh/<region>/proxy/send/direct/!<nodeId>`

Examples:

```text
Topic:   msh/EU_868/proxy/send/group/0
Payload: Hallo Gruppe 0
```

```text
Topic:   msh/EU_868/proxy/send/direct/!13c2288b
Payload: Hallo direkt
```

Optional JSON payload:

```json
{"text":"Hallo","channel":0,"want_ack":true,"hop_limit":3}
```

For group topics, the channel index from the topic is used. For direct topics, channel `0` is used unless a JSON payload overrides it.

If you want ACK correlation over MQTT, include a `client_ref` in the JSON payload:

```json
{"text":"Hallo direkt","channel":0,"want_ack":true,"client_ref":"msg-001"}
```

ACK lifecycle events are published to:

- `msh/<region>/proxy/ack/<client_ref>`

Without `client_ref`, the proxy skips the ACK return path entirely even if `want_ack` is set.

The proxy keeps ACK correlations in memory for 60 seconds and then emits a `timeout` status if no ACK arrives in that window.

## Web Messenger

This proxy can be used together with the separate web-based dashboard project **MeshNode Bridge**:

- GitHub: [ewerker/meshnode-bridge](https://github.com/ewerker/meshnode-bridge)
- Base44 app: [mesh-link-bridge.base44.app](https://mesh-link-bridge.base44.app/about)

MeshNode Bridge is a browser-based MQTT bridge for the Meshtastic mesh network. It allows users to send and receive text messages from the browser without connecting a physical Meshtastic device directly to that browser session.

Conceptually the flow is:

```text
Browser <-> MQTT Broker <-> Gateway Node <-> Mesh Network
```

The web app is built around the JSON topics provided by this fork. The proxy translates between Meshtastic's native Protobuf MQTT traffic and a browser-friendly JSON format that the dashboard can read and write.

Main web dashboard capabilities:

- Send text messages to channels or directly to specific nodes
- Poll and display incoming MQTT-backed messages
- Request and track ACK states in near real time
- Browse the known node directory with battery, signal, position, and uptime data
- Configure topic prefix, region, node id, and channel names per user

Quick web app setup:

1. Open the settings view in the web app.
2. Enter your node id, for example `!49b65bc8`.
3. Set the region to match the Meshtastic configuration.
4. Adjust the topic prefix if your broker uses a custom path.
5. Save and start sending or receiving through the proxy topics.

Requirements for the web dashboard:

- This `ewerker/mqtt-proxy` running locally or on a server
- At least one Meshtastic node with MQTT uplink enabled as gateway
- Access to the same MQTT broker used by the gateway node
- Broker credentials configured by the app administrator

## More Browser Tools

If you also want a browser-based mesh viewer, have a look at:

- [ewerker/meshview](https://github.com/ewerker/meshview)

This is a separate project focused on viewing mesh data directly in the browser and complements the send/receive workflow provided by MeshNode Bridge and this MQTT proxy.

## Node Requirements

The node should have MQTT enabled and configured, for example:

```text
mqtt.enabled: true
mqtt.proxy_to_client_enabled: true
mqtt.address: <broker>
mqtt.username: <user>
mqtt.password: <password>
```

The proxy reads these settings directly from the connected node.

## Development

Install test dependencies:

```bash
.venv\Scripts\python.exe -m pip install -r requirements-test.txt
```

Run tests:

```bash
.venv\Scripts\python.exe -m pytest tests/
```

## Releases

Releases in this fork are source-focused. Tag a commit, push the tag, and create or update a GitHub release for that tag.

Examples:

```bash
git tag -a alpha-0.1 -m "Alpha 0.1"
git push origin alpha-0.1
```

## License

This project is MIT-licensed at the source level. Because it depends on `meshtastic-python` (GPLv3), distribution of combined builds must still respect GPLv3 obligations.
