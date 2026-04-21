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

For a more chatty console with detailed receive/send logs, start it with:

```cmd
start-mqtt-proxy.cmd --verbose
```

## Windows Start

The preferred Windows entry point is [start-mqtt-proxy.cmd](C:\Users\richt\Documents\Codex\mqtt%20Proxy\mqtt-proxy\start-mqtt-proxy.cmd). It loads `.env` and starts the proxy from `.venv` without requiring PowerShell script execution.

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
| `MQTT_LISTENER_DM_ONLY` | `false` | Only mirror direct messages |
| `MQTT_LISTENER_GROUP_ONLY` | `false` | Only mirror group traffic |
| `MQTT_LISTENER_TEXT_ONLY` | `false` | Only mirror text-like messages |

See [CONFIG.md](C:\Users\richt\Documents\Codex\mqtt%20Proxy\mqtt-proxy\CONFIG.md) for the full reference.

## Listener Topics

When the listener is enabled, received packets are mirrored to:

- `msh/<region>/proxy/rx/!<gateway>/all`
- `msh/<region>/proxy/rx/!<gateway>/port/<PORTNUM>`
- `msh/<region>/proxy/rx/!<gateway>/scope/dm`
- `msh/<region>/proxy/rx/!<gateway>/scope/group`

The listener is additive. The original broker-to-node and node-to-broker proxy path remains active.

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
