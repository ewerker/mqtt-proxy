# Release beta-0.9

## English

### RX Channel Metadata
- Added `channel_index` and `channel_name` to mirrored RX JSON records.
- Kept the existing `channel` field as a legacy/raw fallback for compatibility.
- Group packets without explicit channel metadata now fall back to channel `0` (`LongFast`) so default traffic can be routed consistently.

### RX Topic Routing
- Added channel-specific receive topics on `<root>/proxy/rx/!<gateway>/group/<channelIndex>`.
- Added sender-specific direct receive topics on `<root>/proxy/rx/!<gateway>/direct/!<fromNodeId>`.
- Existing compatibility topics such as `scope/group` and `scope/dm` remain available.

### Documentation
- Updated README and CONFIG docs to explain the new RX fields and topic structure for browser and app consumers.

## Deutsch

### RX-Channel-Metadaten
- Gespiegelte RX-JSON-Datensaetze enthalten jetzt `channel_index` und `channel_name`.
- Das bestehende Feld `channel` bleibt als Legacy-/Roh-Fallback zur Kompatibilitaet erhalten.
- Gruppenpakete ohne explizite Channel-Metadaten fallen jetzt auf Kanal `0` (`LongFast`) zurueck, damit Default-Traffic konsistent geroutet werden kann.

### RX-Topic-Routing
- Neue channelspezifische Receive-Topics unter `<root>/proxy/rx/!<gateway>/group/<channelIndex>`.
- Neue absenderspezifische Direct-Receive-Topics unter `<root>/proxy/rx/!<gateway>/direct/!<fromNodeId>`.
- Bestehende Kompatibilitaets-Topics wie `scope/group` und `scope/dm` bleiben erhalten.

### Dokumentation
- README und CONFIG wurden aktualisiert und erklaeren jetzt die neuen RX-Felder und die Topic-Struktur fuer Browser- und App-Clients.

---

# Release beta-0.8.1

## English

### Console Start Notices
- Added direct console notices for high log levels such as `WARNING`, `ERROR`, and `CRITICAL`.
- This prevents healthy proxy runs from appearing completely silent when `INFO` output is filtered out.
- The notice includes app name, version, interface, active log level, verbose state, and MQTT target details.

### Documentation
- Updated example configuration and release documentation to reflect the new startup visibility behavior.

## Deutsch

### Konsolen-Startmeldungen
- Direkte Konsolenmeldungen fuer hohe Loglevel wie `WARNING`, `ERROR` und `CRITICAL` wurden hinzugefuegt.
- Dadurch wirken gesunde Proxy-Laeufe nicht mehr komplett stumm, wenn `INFO`-Ausgaben weggefiltert werden.
- Die Meldung enthaelt App-Name, Version, Interface, aktiven Loglevel, Verbose-Status und MQTT-Zieldaten.

### Dokumentation
- Beispiel-Konfiguration und Release-Dokumentation wurden auf das neue Startverhalten aktualisiert.

---

# Release beta-0.8

## English

### Presence / Status Topics
- Added retained gateway presence on `<root>/2/stat/!<gatewayNodeId>`.
- The proxy publishes:
  - `online` on connect
  - `offline` on clean shutdown
  - `broken` before exiting on health failure
- The MQTT LWT is configured to publish `offline` on unclean exits.
- Optional retained JSON detail is published on `<root>/proxy/status/!<gatewayNodeId>` (includes reasons on `broken`).

### Documentation
- Documented exact presence/status topics and payload semantics in `CONFIG.md`.

## Deutsch

### Presence- / Status-Topics
- Retained Presence-Status auf `<root>/2/stat/!<gatewayNodeId>` hinzugefuegt.
- Der Proxy veroeffentlicht:
  - `online` beim Connect
  - `offline` bei sauberem Shutdown
  - `broken` vor dem Beenden bei Health-Fehler
- MQTT-LWT ist so konfiguriert, dass bei unsauberem Abbruch `offline` veroeffentlicht wird.
- Optional werden retained JSON-Details auf `<root>/proxy/status/!<gatewayNodeId>` veroeffentlicht (enthaelt bei `broken` u.a. Gruende).

### Dokumentation
- Presence-/Status-Topics und Payload-Semantik sind in `CONFIG.md` dokumentiert.

---

# Release beta-0.7

## English

### Console Visibility
- Improved `Node -> MQTT` console visibility so incoming text packets and their mirrored broker publishes are shown consistently.
- Broker publishes now log clear `TX MQTT ... -> broker` lines instead of only node-list-specific output.
- RX text preview logging was aligned with TX logging for easier live troubleshooting.

### MQTT 5 Message Expiry
- Added optional MQTT 5 Message Expiry support for broker publishes.
- New settings:
  - `MQTT_PUBLISH_EXPIRY_ENABLED`
  - `MQTT_PUBLISH_EXPIRY_SECONDS`
- Recommended and example value is `86400` seconds (24 hours).
- This is especially useful for retained JSON topics that should disappear automatically after a day.

### Documentation
- Updated `.env` templates, `README.md`, and `CONFIG.md` with the new expiry configuration and log behavior.

### Tests
- Added coverage for visible broker publish logging.
- Added coverage for MQTT 5 client selection and publish expiry properties.

## Deutsch

### Konsolen-Sichtbarkeit
- Die Sichtbarkeit fuer `Node -> MQTT` in der Konsole wurde verbessert, damit eingehende Textpakete und ihre gespiegelten Broker-Publishes konsistent sichtbar sind.
- Broker-Publishes werden jetzt mit klaren `TX MQTT ... -> broker`-Zeilen geloggt und nicht mehr nur implizit ueber die Node-Liste.
- Die RX-Textvorschau wurde an den TX-Stil angeglichen, damit Live-Debugging leichter wird.

### MQTT-5-Message-Expiry
- Optionale MQTT-5-Message-Expiry fuer Broker-Publishes wurde hinzugefuegt.
- Neue Einstellungen:
  - `MQTT_PUBLISH_EXPIRY_ENABLED`
  - `MQTT_PUBLISH_EXPIRY_SECONDS`
- Empfohlener und beispielhafter Wert ist `86400` Sekunden (24 Stunden).
- Das ist besonders fuer retained JSON-Topics nuetzlich, die nach einem Tag automatisch verschwinden sollen.

### Dokumentation
- `.env`-Vorlagen, `README.md` und `CONFIG.md` wurden fuer die neue Expiry-Konfiguration und das Log-Verhalten aktualisiert.

### Tests
- Testabdeckung fuer sichtbare Broker-Publish-Logs wurde hinzugefuegt.
- Testabdeckung fuer MQTT-5-Clientwahl und Publish-Expiry-Properties wurde hinzugefuegt.

---

# Release beta-0.6

## English

### Gateway-Specific Topics
- Changed plaintext send subscriptions from shared topics to gateway-specific topics.
- The proxy now subscribes only to `.../proxy/send/!<gateway>/#` for its own local node id.
- ACK lifecycle topics are now published under `.../proxy/ack/!<gateway>/<client_ref>`.
- This makes parallel proxy instances on the same MQTT broker addressable by topic path.

### Documentation
- Updated `README.md` and `CONFIG.md` to document the new gateway-specific send and ACK topics.
- Added examples for group send, direct send, and ACK retrieval with a concrete gateway id.

### Tests
- Updated plaintext command tests to cover gateway-specific send topics.
- Updated ACK flow tests to cover gateway-specific ACK topics.

## Deutsch

### Gateway-spezifische Topics
- Die Plaintext-Sendepfade wurden von gemeinsamen Topics auf gateway-spezifische Topics umgestellt.
- Der Proxy abonniert jetzt nur noch `.../proxy/send/!<gateway>/#` fuer seine eigene lokale Node-ID.
- ACK-Lifecycle-Topics werden jetzt unter `.../proxy/ack/!<gateway>/<client_ref>` veroeffentlicht.
- Dadurch lassen sich mehrere Proxy-Instanzen auf demselben MQTT-Broker sauber ueber den Topic-Pfad adressieren.

### Dokumentation
- `README.md` und `CONFIG.md` wurden auf die neuen gateway-spezifischen Send- und ACK-Topics aktualisiert.
- Beispiele fuer Gruppensenden, Direktsenden und ACK-Abruf mit konkreter Gateway-ID wurden ergaenzt.

### Tests
- Die Plaintext-Command-Tests wurden auf gateway-spezifische Sendetopics angepasst.
- Die ACK-Flow-Tests wurden auf gateway-spezifische ACK-Topics angepasst.

---

# Release beta-0.5

## English

### Console UX
- Added colored console output for `INFO`, `WARNING`, `ERROR`, and `CRITICAL` levels when running in a real terminal.
- Highlighted `RX`, `TX`, `TX ACK`, `TX IMPLICIT_ACK`, `TX NAK`, and `TX TIMEOUT` log lines for faster live troubleshooting.
- Improved plaintext send logging so outgoing group and direct messages now show destination, channel, hop-limit, ACK mode, packet id, and text preview.
- Added visible console output for ACK lifecycle events that were previously only published back to MQTT.
- Improved queue send logging so queued MQTT-to-radio traffic is easier to follow during verbose runs.

### Tests
- Added coverage for visible TX logging in plaintext send flow.
- Added coverage for visible ACK logging in the ACK lifecycle flow.

## Deutsch

### Konsolen-UX
- Farbige Konsolenausgabe fuer `INFO`, `WARNING`, `ERROR` und `CRITICAL` in echten Terminals hinzugefuegt.
- `RX`, `TX`, `TX ACK`, `TX IMPLICIT_ACK`, `TX NAK` und `TX TIMEOUT` werden jetzt optisch hervorgehoben und sind bei Live-Debugging schneller erkennbar.
- Die Plaintext-Sendeausgabe zeigt jetzt bei Gruppen- und Direktnachrichten Ziel, Kanal, Hop-Limit, ACK-Modus, Paket-ID und Textvorschau.
- ACK-Lebenszyklus-Ereignisse werden nun nicht mehr nur an MQTT zurueckpubliziert, sondern auch sichtbar in die lokale Konsole geschrieben.
- Die Queue-Sendeausgabe wurde verbessert, damit MQTT-zu-Radio-Verkehr im Verbose-Modus besser nachverfolgbar ist.

### Tests
- Testabdeckung fuer sichtbare TX-Logs im Plaintext-Sendepfad hinzugefuegt.
- Testabdeckung fuer sichtbare ACK-Logs im ACK-Lebenszyklus hinzugefuegt.

---

# Release beta-0.4

## English

### Features
- Added cross-platform `SERIAL_PORT=auto` detection for Meshtastic USB serial devices.
- Supports macOS TinyUSB/CDC devices such as `/dev/cu.usbmodem*`.
- Supports Windows `COMx` detection through pyserial device metadata and known USB vendor IDs.
- Added a macOS/Linux `start-mqtt-proxy.sh` wrapper that loads `.env`, uses `.venv/bin/python`, and supports hot-reload restarts.
- Added a local USB-first `.env.example` setup for direct serial operation.

### Documentation
- Reworked `README.md` into a full German/English guide.
- Documented macOS, Windows, serial auto-detection, explicit serial port pinning, MQTT listener topics, node list topics, plaintext send topics, development, and release flow.
- Updated `CONFIG.md` and bundle examples for `SERIAL_PORT=auto`.

### Tests
- Added tests for macOS `/dev/cu.usbmodem*` auto-detection.
- Added tests for Windows `COMx` auto-detection.
- Added safeguards so Bluetooth/debug ports are not selected as fallback serial devices.

## Deutsch

### Funktionen
- Plattformuebergreifende `SERIAL_PORT=auto`-Erkennung fuer Meshtastic-USB-Seriell-Geraete hinzugefuegt.
- Unterstuetzt macOS-TinyUSB/CDC-Geraete wie `/dev/cu.usbmodem*`.
- Unterstuetzt Windows-`COMx`-Erkennung ueber pyserial-Geraetedaten und bekannte USB-Vendor-IDs.
- Neues macOS/Linux-Startskript `start-mqtt-proxy.sh`, das `.env` laedt, `.venv/bin/python` nutzt und Hot-Reload-Neustarts unterstuetzt.
- Lokales USB-First-Setup in `.env.example` fuer direkten seriellen Betrieb.

### Dokumentation
- `README.md` als vollstaendigen deutsch/englischen Leitfaden ueberarbeitet.
- macOS, Windows, serielle Auto-Erkennung, explizite Port-Angabe, MQTT-Listener-Topics, Node-Listen-Topics, Plaintext-Sendebefehle, Entwicklung und Release-Ablauf dokumentiert.
- `CONFIG.md` und Bundle-Beispiele auf `SERIAL_PORT=auto` aktualisiert.

### Tests
- Tests fuer macOS-`/dev/cu.usbmodem*`-Auto-Erkennung hinzugefuegt.
- Tests fuer Windows-`COMx`-Auto-Erkennung hinzugefuegt.
- Schutz ergaenzt, damit Bluetooth-/Debug-Ports nicht als Fallback-Seriellgeraete gewaehlt werden.

---

# Release v1.6.5

## ✨ Features & Enhancements
- **Strict Channel Verification:** Added configuration flag `MESH_ALLOW_UNCONFIGURED_CHANNELS` (default: `True`) allowing users to strictly enforce network forwarding restrictions based on physical node definitions, preventing extraneous traffic from traversing the proxy (fixes Issue 45).
- **Drop-Oldest Queue Eviction:** Replaced the node interface transmission buffer with a `collections.deque` implementing a drop-oldest eviction strategy. This ensures that the most recent packets consistently reach the radio during peak load and connection reconnects without latency blocks (combines PR 46 & 47).

---

# Release v1.6.4

## 🚀 Infrastructure & CI/CD
- **Windows Executable Release Flow:** Fixed the GitHub Actions workflow to correctly attach the Windows `.exe` standalone application to immutable releases.

---

# Release v1.6.3

## Virtual Channel RF Crosstalk Prevention

This release fixes a critical bug where Virtual Channel packets injected into the local radio (via `EXTRA_MQTT_ROOTS`) could be decrypted and rebroadcast over RF to nearby nodes, effectively bridging two independent MQTT server regions against the user's intent.

## 🐛 Bug Fixes

* **Fix: Virtual Channel RF Crosstalk** (PR #41)
  * **Root Cause:** The radio firmware uses `packet.channel` — a PSK hash integer embedded in the `ServiceEnvelope` protobuf payload — to look up its decryption key. Because the topic-only rewrite (`NC-LongFast`) left the original PSK hash intact, the radio could still match its local channel key and decrypt the packet, causing it to rebroadcast over RF.
  * **Fix:** The proxy now mutates the `packet.channel` field in the protobuf payload before injecting it into the radio:
    * `packet.channel` — replaced with a synthetic hash unique to the virtual channel name that no local radio will ever have configured
  * The `packet.encrypted` bytes and original `channel_id` string are left completely untouched. MeshMonitor natively decrypts the message using its standard Channel Database. **Known Defect:** Because the PSK hash is faked, MeshMonitor's "Enforce Channel Name Validation" cannot be used. Consequently, if multiple channels share the exact same key, MeshMonitor will decode and merge their traffic into a single channel display.
  * Added `INFO`-level log entry on every virtual channel rewrite for easy discovery of exact virtual channel names.

## 📝 Documentation

* Updated `CONFIG.md` Virtual Channels section to accurately describe the payload mutation mechanism and added **MeshMonitor Channel Database setup instructions** explaining which channel name and key to configure for each virtual channel.

---

# Release v1.6.2

This release introduces two major new features to handle advanced broker routing and to improve fidelity with Meshtastic node configurations: **Virtual Channels (Multi-Root)** and **Per-Channel Uplink/Downlink Filtering**.

## ✨ New Features

### Virtual Channels & Extra MQTT Roots (PR #38)
* **`EXTRA_MQTT_ROOTS` Configuration:** You can now configure the proxy to listen to multiple MQTT root topics simultaneously. This allows you to monitor and interact with additional roots seamlessly without complex external broker forwarding rules.
* **Topic Rewriting:** Traffic from extra MQTT roots is automatically rewritten to appear as local "Virtual Channels" (e.g., matching the root name like `NC-LongFast`), preventing cross-talk while making remote region traffic accessible in standard clients such as MeshMonitor.

### Per-Channel Uplink/Downlink Filtering (PR #37)
* **Respect Node Configuration:** The proxy now fully parses and respects the per-channel `uplink_enabled` and `downlink_enabled` settings configured directly on your physical Meshtastic node. 
* **Selective Forwarding:** Only packets on channels explicitly permitted for uplink or downlink will be forwarded between the MQTT broker and the local radio queue, saving serial bandwidth and perfectly matching the firmware's intended behavior.

## 📝 Documentation
* Documented the new channel-based filtering and extra MQTT roots features.
* Updated configuration documentation (`CONFIG.md` and `README.md`) to clearly explain `EXTRA_MQTT_ROOTS`.

---

# Release v1.5.3
## 🚀 New Features

### Windows Standalone Executables
- **Zero-Setup Windows Deployment:** Added an automated PyInstaller build pipeline that compiles `mqtt-proxy` into a standalone, click-and-run `.exe` for Windows users.
  - No Python installation or virtual environment is required.
  - Windows AMD64 binaries are now automatically generated via GitHub Actions and attached directly to Releases.
  - **Subprocess-Ready:** The executable is specially configured to force line-buffered `stdout` and `stderr` streams using `utf-8` encoding. This prevents buffering lags and `cp1252` encoding crashes when embedded and executed natively by external tools or desktop apps on Windows.
  - Updated configuration documentation to recommend this execution method for easiest integration with the MeshMonitor Desktop App.

### Version Tracking & Identification
- **Single Source of Truth:** Introduced `version.py` to manage the application version globally.
- **Improved Visibility:**
  - The binary version is now printed in the startup logs: `🚀 MQTT Proxy v1.5.3 starting...`.
  - Added a `--version` flag to the CLI for quick verification.
  - Added a version tag to the `README.md` for consistent project tracking.

### Command-Line Interface (CLI) Arguments
- **Argparse Support:** The proxy now fully supports standard command-line flags to configure connection settings directly on launch.
  - Supported execution flags: `--interface`, `--tcp-host`, `--tcp-port`, `--serial-port`, `--log-level`, and `--version`.
  - Backwards-compatible: Existing environment variables and `.env` files still function normally as fallbacks for any omitted flags.

## 📦 Dependencies
- **Bump Meshtastic to 2.7.8**: Upgraded python `meshtastic` dependency to the latest `2.7.8` version for compatibility with the newest firmware module configs (e.g. Traffic Management and StatusMessage).

## 🛠️ Infrastructure & CI/CD
- **Docker Build Fixes**:
  - Fixed a missing build context issue where `version.py` was not copied into the container, preventing the proxy from launching.
  - Enabled multi-arch (AMD64/Arm64/Armv7) Docker image pushes for internal Pull Requests, allowing real-time testing on devices like Raspberry Pi.
- **Workflow Optimizations**:
  - Fixed a "double build" issue in CI by removing redundant triggers on feature branches.
  - Resolved `WinError 10106` by setting the PyInstaller runtime temporary directory to `%LOCALAPPDATA%\Temp`.
  - Added detailed **"Releasing New Versions"** documentation to guide developers through PR-safe tagging workflows on protected branches.

## 🧹 Refactoring
- **Simplify Echo Bypass**: Cached prefixed node ID and cleaned up the `_on_message` boolean logic structure. Thank you @NearlCrews!

---

# Release v1.4.2

## 🐛 Bug Fixes

### Echo Bypass is Too Broad (Issue #25)
- **Narrowed Implicit ACK Echo Bypass**: Fixed an issue where the loop prevention bypass was too broad, causing unencrypted routing, position, and telemetry packets to echo back to the node unnecessarily.
  - Instead of bypassing loop protection for all packets from the local gateway, the proxy now explicitly checks if the packet is `encrypted` or has a valid `request_id`.
  - Administrative/plain packets are properly dropped by the loop tracker to minimize unnecessary RF traffic.

## 🧪 Test Coverage
- Added new test cases in `tests/test_echo_bypass.py` to ensure only correct packet types (encrypted, request_id) explicitly bypass loop prevention.

---

**Full Changelog**: https://github.com/LN4CY/mqtt-proxy/compare/v1.4.1...v1.4.2

# Release v1.4.1
## 🐛 Bug Fixes

### "Proxy to Client" Ack Restoration (The "Red X" Fix)
- **Implicit ACK Echoes**: Fixed a critical bug where `mqtt-proxy`'s strict loop protection dropped echoed messages from the MQTT Broker.
  - When the Meshtastic firmware has `proxy_to_client_enabled: true` set, it stops generating automatic "Implicit ACKs" for transmissions.
  - Instead, the firmware expects the MQTT broker to echo the message back so it knows it was successfully delivered.
  - By bypassing the deduplicator specifically for echoed messages (where `gateway_id` matches the local node ID), the firmware now receives the delivery confirmation it needs.
  - This prevents `MAX_RETRANSMIT` timeouts and fixes the "Red X" (Failed delivery status) issue in MeshMonitor for both DMs and Channel Broadcasts.

## 📝 Documentation
- **CONFIG.md**: Added warnings and explanations around the `proxy_to_client_enabled` setting and how it alters firmware timeout behavior.
- **README.md**: Added "Implicit ACK Restoration" to the core features list and clarified the Architecture section's "How It Works".

---

**Full Changelog**: https://github.com/LN4CY/mqtt-proxy/compare/v1.3.0...v1.4.0

# Release v1.3.0

## 🐛 Bug Fixes

### Missed Messages (False Positive ACKs)
- **Ignored Implicit ACKs from Self/Local**: Fixed an issue where local routing confirmation packets were incorrectly interpreted as successful delivery acknowledgments from remote nodes.
  - The proxy now explicitly checks the `sender` of `ROUTING_APP` packets.
  - Packets where `sender == 0` (local routing confirmation) are ignored.
  - Packets where `sender == myNodeNum` (echoes from self) are ignored.
  - This ensures `meshtastic.ack` events are only emitted for high-confidence confirmations, improving message reliability logic.

## 🧪 Test Coverage
- Added new unit tests in `tests/test_meshtastic_extended.py` to verify implicit ACK suppression for self and sender 0.

---

**Full Changelog**: https://github.com/LN4CY/mqtt-proxy/compare/v1.2.0...v1.3.0

# Release v1.2.0

## 🛡️ Reliability & Stability Improvements

### Thread-Safe Radio Interactions
- **Locked Radio Access**: Implemented thread-safe `_sendToRadio` using the interface's internal locking mechanism.
  - Prevents potential race conditions when multiple handlers attempt to send data to the radio simultaneously.
  - Added fallback with warning if `_sendToRadio` is missing (e.g., in older `meshtastic` library versions).

### Enhanced Packet Management
- **Improved Deduplication**: Refined the deduplication logic to better handle packet IDs and sender tracking.
  - Prevents message loops when proxying traffic between MQTT and the mesh network.

### Robust Health Monitoring
- **Configuration Race Condition Fix**: Addressed a race condition in MQTT handler initialization to ensure reliable startup and state management.
- **Improved Health Checks**: Enhanced watchdog mechanisms for better reporting of proxy status.

## 📊 Performance & Monitoring

### Latency Logging
- **Detailed Message Queue Stats**: Added precise timing logs for message processing.
  - New Log Format: `Message processed. Queue: N msgs, Wait: X.XXXs, Send: X.XXXs`
  - Helps track transit times and identify bottlenecks in radio transmissions.

## 🧪 Test Coverage & CI/CD

### Enhanced Test Suite
- **Queue Handler Coverage**: Increased test coverage for `handlers/queue.py` to ensure reliable buffering and rate limiting.
- **Thread Safety Validation**: Added tests to verify thread-safe usage of the radio interface.

### CI/CD Optimizations
- **Build Trigger Cleanup**: Fixed duplicate Docker image builds by refining push event wildcard triggers.
- **Cleanup Workflow Fix**: Resolved `Invalid Cut-off` errors in image retention policy by updating to properly formatted duration strings (`14d`).

## 🔄 Breaking Changes
None - all changes are backward compatible.

## 📊 Testing Status
All tests passing with improved coverage in core message handling modules.

---

**Full Changelog**: https://github.com/LN4CY/mqtt-proxy/compare/v1.1.2...v1.2.0

# Release v1.1.2

## 🚀 Performance & Reliability Improvements

### Major Performance Enhancement
- **50x faster MQTT-to-node forwarding**: Reduced default `MESH_TRANSMIT_DELAY` from 500ms to 10ms
  - Typical transmission is ~1ms, 10ms provides safe spacing while maintaining responsiveness
  - Configurable via `MESH_TRANSMIT_DELAY` environment variable
  
### Retained Message Filtering  
- **Prevents startup floods**: Skip retained MQTT messages by default
  - Eliminates 4+ second queue backlogs when connecting to broker
  - Retained messages are historical state, not live mesh traffic
  - Opt-in via `MQTT_FORWARD_RETAINED=true` if needed

### Enhanced Monitoring
- **Queue depth logging**: Added current queue size to message processing logs
  - Format: `Queue: N msgs, Wait: X.XXXs, Send: X.XXXs`
  - Helps identify backlogs and performance issues

## 🧪 Test Coverage Improvements

### Comprehensive Test Suite
- **40 tests → 42 tests**: Added extensive coverage for critical paths
- **87% total coverage** across all handlers
  - `handlers/mqtt.py`: 90% coverage
  - `handlers/meshtastic.py`: 77% coverage  
  - `handlers/node_tracker.py`: 86% coverage
  - `handlers/queue.py`: 92% coverage

### New Test Files
- `test_mqtt_extended.py`: TLS configuration, error handling, edge cases
- `test_meshtastic_extended.py`: Byte parsing, implicit ACKs, DecodeError handling
- `test_proxy_health.py`: Health checks, watchdog mechanisms, state management
- `test_retained_messages.py`: Retained message filtering validation

## 🐛 Bug Fixes

- **Critical**: Fixed `fromId` AttributeError in packet tracking
  - MeshPacket protobuf only has `from` field, not `fromId`
  - Was causing "Failed to track node/packet: fromId" errors
  
- **CI/CD**: Fixed module import errors in GitHub Actions
  - Added `sys.path.append()` to test files for proper module resolution

- **Pytest**: Renamed `TestInterface` to `MixinTestHelper`
  - Eliminates pytest warning about test classes with `__init__` constructors

## 📝 Configuration

### New Environment Variables
- `MESH_TRANSMIT_DELAY`: Delay between messages (default: `0.01` seconds)
- `MQTT_FORWARD_RETAINED`: Forward retained messages (default: `false`)

## 🔄 Breaking Changes
None - all changes are backward compatible

## 📊 Testing
All 42 tests passing with 87% coverage across handlers

## 🙏 Contributors
Thank you to everyone who helped test and validate these improvements!

---

**Full Changelog**: https://github.com/LN4CY/mqtt-proxy/compare/v1.1.1...v1.1.2
