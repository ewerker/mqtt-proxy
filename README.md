# Meshtastic MQTT Proxy

**Version**: beta-0.8.1

## English

Python-first MQTT proxy for Meshtastic nodes. This fork keeps the original bidirectional `mqttClientProxyMessage` workflow, adds a USB-first local setup, mirrors received mesh packets to browser-friendly JSON MQTT topics, and accepts simple MQTT send commands for group and direct messages.

The current focus is practical local operation with a Meshtastic node connected over USB serial or TCP. On macOS and Windows, `SERIAL_PORT=auto` can detect common Meshtastic USB serial devices automatically.

## Deutsch

Python-basierter MQTT-Proxy fuer Meshtastic-Nodes. Dieser Fork behaelt den bidirektionalen `mqttClientProxyMessage`-Workflow bei, ergaenzt einen USB-First-Betrieb fuer lokale Setups, spiegelt empfangene Mesh-Pakete auf browserfreundliche JSON-MQTT-Topics und akzeptiert einfache MQTT-Sendebefehle fuer Gruppen- und Direktnachrichten.

Der aktuelle Schwerpunkt ist der praktische lokale Betrieb mit einem Meshtastic-Node ueber USB-Seriell oder TCP. Unter macOS und Windows kann `SERIAL_PORT=auto` typische Meshtastic-USB-Seriell-Geraete automatisch erkennen.

## Features

English:

- Bidirectional MQTT proxying between Meshtastic node and MQTT broker
- USB serial and TCP connection support
- Serial auto-detection with `SERIAL_PORT=auto`
- macOS TinyUSB/CDC support via `/dev/cu.usbmodem*`
- Windows `COMx` support via pyserial device detection
- Listener-based JSON mirroring via `meshtastic.receive`
- Configurable listener target topics to avoid duplicate MQTT storage
- Retained listener messages and retained ACK lifecycle topics
- Optional MQTT 5 message expiry for broker-published topics
- Plaintext MQTT send commands for channel and direct messages
- TLS support based on the node MQTT configuration
- Channel uplink/downlink filtering based on the node channel settings
- Virtual channel support via `EXTRA_MQTT_ROOTS`
- Windows and macOS/Linux startup scripts

Deutsch:

- Bidirektionales MQTT-Proxying zwischen Meshtastic-Node und MQTT-Broker
- USB-Seriell- und TCP-Verbindungen
- Serielle Auto-Erkennung mit `SERIAL_PORT=auto`
- macOS TinyUSB/CDC-Unterstuetzung ueber `/dev/cu.usbmodem*`
- Windows-`COMx`-Unterstuetzung ueber pyserial-Geraeteerkennung
- JSON-Spiegelung empfangener Pakete ueber `meshtastic.receive`
- Konfigurierbare Listener-Zieltopics zur Vermeidung doppelter MQTT-Ablage
- Retained Listener-Nachrichten und retained ACK-Lifecycle-Topics
- Optionale MQTT-5-Message-Expiry fuer zum Broker publizierte Topics
- Plaintext-MQTT-Befehle fuer Gruppen- und Direktnachrichten
- TLS-Unterstuetzung auf Basis der MQTT-Konfiguration des Nodes
- Uplink-/Downlink-Filter anhand der Channel-Einstellungen des Nodes
- Virtuelle Channels ueber `EXTRA_MQTT_ROOTS`
- Startskripte fuer Windows und macOS/Linux

## Requirements / Voraussetzungen

English:

- Python 3.10+
- A Meshtastic node reachable by USB serial or TCP
- MQTT configured on the connected Meshtastic node
- For USB operation: a real USB data cable, not a charge-only cable

Deutsch:

- Python 3.10+
- Ein Meshtastic-Node, erreichbar per USB-Seriell oder TCP
- MQTT-Konfiguration auf dem verbundenen Meshtastic-Node
- Fuer USB-Betrieb: ein echtes USB-Datenkabel, kein reines Ladekabel

## Quick Start: macOS / Linux

English:

```bash
git clone https://github.com/ewerker/mqtt-proxy.git
cd mqtt-proxy
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
./start-mqtt-proxy.sh --verbose
```

Deutsch:

```bash
git clone https://github.com/ewerker/mqtt-proxy.git
cd mqtt-proxy
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
./start-mqtt-proxy.sh --verbose
```

The macOS/Linux script loads `.env`, starts `.venv/bin/python`, and restarts the proxy automatically when `.env` changes and the app exits with the hot-reload code.

Das macOS/Linux-Skript laedt `.env`, startet `.venv/bin/python` und startet den Proxy automatisch neu, wenn `.env` geaendert wurde und die App mit dem Hot-Reload-Code beendet wird.

## Quick Start: Windows

English:

```powershell
git clone https://github.com/ewerker/mqtt-proxy.git
cd mqtt-proxy
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\start-mqtt-proxy.cmd --verbose
```

Deutsch:

```powershell
git clone https://github.com/ewerker/mqtt-proxy.git
cd mqtt-proxy
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\start-mqtt-proxy.cmd --verbose
```

The Windows batch file loads `.env`, starts `.venv\Scripts\python.exe`, and restarts automatically when `.env` changes.

Die Windows-Batchdatei laedt `.env`, startet `.venv\Scripts\python.exe` und startet automatisch neu, wenn `.env` geaendert wurde.

Direct Python start also works:

Direkter Python-Start funktioniert ebenfalls:

```powershell
.\.venv\Scripts\python.exe mqtt-proxy.py --interface serial --serial-port auto --verbose
```

## Serial USB Setup / Serielle USB-Einrichtung

English:

Use this in `.env` for automatic USB serial detection:

```env
INTERFACE_TYPE=serial
SERIAL_PORT=auto
```

On macOS, TinyUSB/CDC devices such as Seeed Tracker boards normally appear as:

```text
/dev/cu.usbmodem101
```

On Windows, the same device usually appears as a `COMx` port:

```text
COM7
```

The proxy uses pyserial to inspect available ports. It first looks for Meshtastic/Seeed/TinyUSB-style descriptions, then known USB vendor IDs, then platform-specific port names. Bluetooth and debug-only ports are ignored.

If auto-detection is not desired, pin the port explicitly:

```env
SERIAL_PORT=/dev/cu.usbmodem101
# or on Windows:
SERIAL_PORT=COM7
```

Deutsch:

Fuer automatische USB-Seriell-Erkennung in `.env`:

```env
INTERFACE_TYPE=serial
SERIAL_PORT=auto
```

Unter macOS erscheinen TinyUSB/CDC-Geraete wie Seeed Tracker Boards normalerweise als:

```text
/dev/cu.usbmodem101
```

Unter Windows erscheint dasselbe Geraet typischerweise als `COMx`-Port:

```text
COM7
```

Der Proxy nutzt pyserial, um verfuegbare Ports zu pruefen. Zuerst werden Meshtastic-/Seeed-/TinyUSB-Beschreibungen gesucht, danach bekannte USB-Vendor-IDs und danach plattformspezifische Portnamen. Bluetooth- und reine Debug-Ports werden ignoriert.

Wenn keine Auto-Erkennung gewuenscht ist, kann der Port fest eingetragen werden:

```env
SERIAL_PORT=/dev/cu.usbmodem101
# oder unter Windows:
SERIAL_PORT=COM7
```

## TCP Setup / TCP-Einrichtung

English:

Use TCP when the node or a compatible endpoint exposes a Meshtastic TCP API:

```env
INTERFACE_TYPE=tcp
TCP_NODE_HOST=127.0.0.1
TCP_NODE_PORT=4404
TCP_TIMEOUT=300
```

Deutsch:

TCP verwenden, wenn der Node oder ein kompatibler Endpunkt eine Meshtastic-TCP-API bereitstellt:

```env
INTERFACE_TYPE=tcp
TCP_NODE_HOST=127.0.0.1
TCP_NODE_PORT=4404
TCP_TIMEOUT=300
```

## Local `.env`

English:

The local `.env` is intentionally ignored by Git. It should contain machine-specific runtime settings. The repository includes `.env.example` and `bundle/.env.example` as copyable templates.

Both templates are self-documented on purpose: the comments next to each setting explain what the option does, when it is useful, and which defaults are sensible for a normal local setup.

Recommended local USB setup:

```env
INTERFACE_TYPE=serial
SERIAL_PORT=auto
LOG_LEVEL=INFO
VERBOSE=false

MQTT_LISTENER_ENABLED=true
MQTT_LISTENER_PORTS=TEXT_MESSAGE_APP,TEXT_MESSAGE_COMPRESSED_APP
MQTT_LISTENER_EXCLUDE_PORTS=ROUTING_APP,ADMIN_APP
MQTT_LISTENER_TEXT_ONLY=true
MQTT_LISTENER_INCLUDE_RAW=false
MQTT_LISTENER_PUBLISH_ALL=false
MQTT_LISTENER_PUBLISH_PORT=false
MQTT_LISTENER_PUBLISH_SCOPE=true
MQTT_PUBLISH_EXPIRY_ENABLED=true
MQTT_PUBLISH_EXPIRY_SECONDS=86400

MQTT_NODE_LIST_ENABLED=true
MQTT_NODE_LIST_INTERVAL_SECONDS=3600
MQTT_NODE_LIST_RETAIN=true
```

Deutsch:

Die lokale `.env` ist absichtlich durch Git ignoriert. Sie enthaelt maschinenspezifische Laufzeitwerte. Das Repository enthaelt `.env.example` und `bundle/.env.example` als kopierbare Vorlagen.

Beide Vorlagen sind bewusst selbstdokumentierend aufgebaut: Die Kommentare direkt neben den Einstellungen erklaeren Zweck, typische Einsatzfaelle und sinnvolle Standardwerte fuer ein normales lokales Setup.

Empfohlenes lokales USB-Setup:

```env
INTERFACE_TYPE=serial
SERIAL_PORT=auto
LOG_LEVEL=INFO
VERBOSE=false

MQTT_LISTENER_ENABLED=true
MQTT_LISTENER_PORTS=TEXT_MESSAGE_APP,TEXT_MESSAGE_COMPRESSED_APP
MQTT_LISTENER_EXCLUDE_PORTS=ROUTING_APP,ADMIN_APP
MQTT_LISTENER_TEXT_ONLY=true
MQTT_LISTENER_INCLUDE_RAW=false
MQTT_LISTENER_PUBLISH_ALL=false
MQTT_LISTENER_PUBLISH_PORT=false
MQTT_LISTENER_PUBLISH_SCOPE=true
MQTT_PUBLISH_EXPIRY_ENABLED=true
MQTT_PUBLISH_EXPIRY_SECONDS=86400

MQTT_NODE_LIST_ENABLED=true
MQTT_NODE_LIST_INTERVAL_SECONDS=3600
MQTT_NODE_LIST_RETAIN=true
```

## Configuration Reference / Konfigurationsuebersicht

| Variable | Default | English | Deutsch |
|----------|---------|---------|---------|
| `INTERFACE_TYPE` | `tcp` | `tcp` or `serial` | `tcp` oder `serial` |
| `TCP_NODE_HOST` | `localhost` | TCP node host | TCP-Host des Nodes |
| `TCP_NODE_PORT` | `4403` | TCP node port | TCP-Port des Nodes |
| `TCP_TIMEOUT` | `300` | TCP timeout in seconds | TCP-Timeout in Sekunden |
| `SERIAL_PORT` | `/dev/ttyUSB0` | Serial path or `auto` | Serieller Port oder `auto` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `VERBOSE` | `false` | More detailed console output | Ausfuehrlichere Konsolenausgabe |
| `ENV_HOT_RELOAD_ENABLED` | `true` | Restart when `.env` changes | Neustart bei `.env`-Aenderung |
| `MQTT_LISTENER_ENABLED` | `false` | Enable JSON receive mirror | JSON-Empfangsspiegelung aktivieren |
| `MQTT_LISTENER_PORTS` | empty | Optional allowlist of portnums | Optionale Portnum-Erlaubnisliste |
| `MQTT_LISTENER_EXCLUDE_PORTS` | empty | Optional blocklist of portnums | Optionale Portnum-Sperrliste |
| `MQTT_LISTENER_TEXT_ONLY` | `false` | Mirror only text-like packets | Nur textartige Pakete spiegeln |
| `MQTT_LISTENER_INCLUDE_RAW` | `true` | Include full raw packet JSON | Vollstaendiges Rohpaket einbetten |
| `MQTT_LISTENER_RETAIN` | `true` | Publish listener topics retained | Listener-Topics retained publishen |
| `MQTT_ACK_RETAIN` | `true` | Publish ACK lifecycle retained | ACK-Lifecycle retained publishen |
| `MQTT_PUBLISH_EXPIRY_ENABLED` | `false` | Enable MQTT 5 Message Expiry on broker publishes | MQTT-5-Message-Expiry fuer Broker-Publishes aktivieren |
| `MQTT_PUBLISH_EXPIRY_SECONDS` | `86400` | Expiry time in seconds for broker-published messages | Ablaufzeit in Sekunden fuer Broker-Publishes |
| `MQTT_NODE_LIST_ENABLED` | `true` | Publish periodic node list | Periodische Node-Liste publishen |
| `MQTT_NODE_LIST_INTERVAL_SECONDS` | `3600` | Node list interval | Node-Listen-Intervall |
| `MQTT_FORWARD_RETAINED` | `false` | Forward retained broker messages | Retained Broker-Nachrichten weiterleiten |
| `EXTRA_MQTT_ROOTS` | empty | Additional MQTT roots | Zusaetzliche MQTT-Roots |

See [CONFIG.md](CONFIG.md) for the full reference.

The fastest way to understand the runtime options is usually the commented `.env.example`, because it is grouped by use case and written for copy-and-adjust workflows.

Die vollstaendige Referenz steht in [CONFIG.md](CONFIG.md).

Am schnellsten versteht man die Laufzeitoptionen meist ueber die kommentierte `.env.example`, weil sie nach Einsatzfaellen gruppiert ist und direkt fuer Copy-and-adjust gedacht ist.

## Listener Topics / Listener-Topics

English:

When the listener is enabled, received mesh packets are mirrored to dedicated JSON topics:

```text
msh/<region>/proxy/rx/!<gateway>/all
msh/<region>/proxy/rx/!<gateway>/port/<PORTNUM>
msh/<region>/proxy/rx/!<gateway>/scope/dm
msh/<region>/proxy/rx/!<gateway>/scope/group
```

The listener is additive. The original node-to-broker and broker-to-node proxy path remains active.

When `MQTT_PUBLISH_EXPIRY_ENABLED=true`, the proxy switches its broker client to MQTT 5 and attaches a Message Expiry Interval to published topics. This is useful for retained JSON topics that should disappear automatically after a defined time, for example after `86400` seconds (24 hours).

Useful port filters:

```env
MQTT_LISTENER_PORTS=TEXT_MESSAGE_APP,TELEMETRY_APP,POSITION_APP,NODEINFO_APP
MQTT_LISTENER_EXCLUDE_PORTS=ROUTING_APP,ADMIN_APP
MQTT_LISTENER_INCLUDE_RAW=false
```

Deutsch:

Wenn der Listener aktiv ist, werden empfangene Mesh-Pakete auf eigene JSON-Topics gespiegelt:

```text
msh/<region>/proxy/rx/!<gateway>/all
msh/<region>/proxy/rx/!<gateway>/port/<PORTNUM>
msh/<region>/proxy/rx/!<gateway>/scope/dm
msh/<region>/proxy/rx/!<gateway>/scope/group
```

Der Listener ist additiv. Der urspruengliche Node-zu-Broker- und Broker-zu-Node-Proxy-Pfad bleibt aktiv.

Wenn `MQTT_PUBLISH_EXPIRY_ENABLED=true` gesetzt ist, nutzt der Proxy fuer Broker-Publishes MQTT 5 und haengt eine Message Expiry Interval an. Das ist besonders fuer retained JSON-Topics nuetzlich, die nach einer definierten Zeit automatisch verschwinden sollen, zum Beispiel nach `86400` Sekunden (24 Stunden).

Nuetzliche Port-Filter:

```env
MQTT_LISTENER_PORTS=TEXT_MESSAGE_APP,TELEMETRY_APP,POSITION_APP,NODEINFO_APP
MQTT_LISTENER_EXCLUDE_PORTS=ROUTING_APP,ADMIN_APP
MQTT_LISTENER_INCLUDE_RAW=false
```

## Periodic Node List / Periodische Node-Liste

English:

The proxy publishes retained node list snapshots for selector UIs and remote tooling:

```text
msh/<region>/proxy/nodes/!<gateway>/all
msh/<region>/proxy/nodes/!<gateway>/index
```

`all` contains the full snapshot. `index` contains a compact list for UI pickers.

Deutsch:

Der Proxy veroeffentlicht retained Node-Listen-Snapshots fuer Auswahloberflaechen und Remote-Tools:

```text
msh/<region>/proxy/nodes/!<gateway>/all
msh/<region>/proxy/nodes/!<gateway>/index
```

`all` enthaelt den vollstaendigen Snapshot. `index` enthaelt eine kompakte Liste fuer UI-Auswahllisten.

## Plaintext Send Commands / Plaintext-Sendebefehle

English:

The proxy subscribes to simple send command topics:

```text
msh/<region>/proxy/send/!<gateway>/group/<channelIndex>
msh/<region>/proxy/send/!<gateway>/direct/!<nodeId>
```

Plain text payload:

```text
Topic:   msh/EU_868/proxy/send/!49b65bc8/group/0
Payload: Hello group 0
```

Optional JSON payload:

```json
{"text":"Hello","channel":0,"want_ack":true,"hop_limit":3,"client_ref":"msg-001"}
```

ACK lifecycle events are published to:

```text
msh/<region>/proxy/ack/!<gateway>/<client_ref>
```

Deutsch:

Der Proxy abonniert einfache Sendebefehls-Topics:

```text
msh/<region>/proxy/send/!<gateway>/group/<channelIndex>
msh/<region>/proxy/send/!<gateway>/direct/!<nodeId>
```

Plaintext-Payload:

```text
Topic:   msh/EU_868/proxy/send/!49b65bc8/group/0
Payload: Hallo Gruppe 0
```

Optionale JSON-Payload:

```json
{"text":"Hallo","channel":0,"want_ack":true,"hop_limit":3,"client_ref":"msg-001"}
```

ACK-Lifecycle-Events werden hier veroeffentlicht:

```text
msh/<region>/proxy/ack/!<gateway>/<client_ref>
```

## Node MQTT Requirements / MQTT-Anforderungen am Node

English:

The connected Meshtastic node must expose MQTT settings. The proxy reads broker settings directly from the node:

```text
mqtt.enabled: true
mqtt.proxy_to_client_enabled: true
mqtt.address: <broker>
mqtt.username: <user>
mqtt.password: <password>
```

Deutsch:

Der verbundene Meshtastic-Node muss MQTT-Einstellungen bereitstellen. Der Proxy liest die Broker-Konfiguration direkt aus dem Node:

```text
mqtt.enabled: true
mqtt.proxy_to_client_enabled: true
mqtt.address: <broker>
mqtt.username: <user>
mqtt.password: <password>
```

## Browser Tools / Browser-Werkzeuge

English:

This proxy can be used with the separate browser dashboard **MeshNode Bridge**:

- GitHub: [ewerker/meshnode-bridge](https://github.com/ewerker/meshnode-bridge)
- Base44 app: [mesh-link-bridge.base44.app](https://mesh-link-bridge.base44.app/about)

Conceptual flow:

```text
Browser <-> MQTT Broker <-> Gateway Node <-> Mesh Network
```

The dashboard uses the JSON topics provided by this proxy to send messages, receive messages, track ACK states, and browse node information.

Another related project is [ewerker/meshview](https://github.com/ewerker/meshview), focused on viewing mesh data in the browser.

Deutsch:

Dieser Proxy kann zusammen mit dem separaten Browser-Dashboard **MeshNode Bridge** genutzt werden:

- GitHub: [ewerker/meshnode-bridge](https://github.com/ewerker/meshnode-bridge)
- Base44-App: [mesh-link-bridge.base44.app](https://mesh-link-bridge.base44.app/about)

Konzeptioneller Ablauf:

```text
Browser <-> MQTT Broker <-> Gateway Node <-> Mesh Network
```

Das Dashboard nutzt die JSON-Topics dieses Proxys zum Senden, Empfangen, ACK-Tracking und Anzeigen von Node-Informationen.

Ein weiteres verwandtes Projekt ist [ewerker/meshview](https://github.com/ewerker/meshview), fokussiert auf Mesh-Datenanzeige im Browser.

## Development / Entwicklung

English:

Install runtime and test dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements-test.txt
```

Run tests:

```bash
.venv/bin/python -m pytest
```

Deutsch:

Runtime- und Test-Abhaengigkeiten installieren:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements-test.txt
```

Tests ausfuehren:

```bash
.venv/bin/python -m pytest
```

## Releases

English:

This fork currently uses beta tags. The current release is `beta-0.8.1`.

Typical release flow:

```bash
git commit -m "release: beta-0.8.1"
git tag beta-0.8.1
git push origin master
git push origin beta-0.8.1
gh release create beta-0.8.1 --title "beta-0.8.1" --notes-file latest_notes.md
```

Deutsch:

Dieser Fork nutzt aktuell Beta-Tags. Das aktuelle Release ist `beta-0.8.1`.

Typischer Release-Ablauf:

```bash
git commit -m "release: beta-0.8.1"
git tag beta-0.8.1
git push origin master
git push origin beta-0.8.1
gh release create beta-0.8.1 --title "beta-0.8.1" --notes-file latest_notes.md
```

## License / Lizenz

English:

This project is MIT-licensed at the source level. Because it depends on `meshtastic-python` (GPLv3), distribution of combined builds must still respect GPLv3 obligations.

Deutsch:

Dieses Projekt steht auf Source-Ebene unter der MIT-Lizenz. Da es von `meshtastic-python` (GPLv3) abhaengt, muss die Verteilung kombinierter Builds weiterhin die GPLv3-Pflichten beachten.
