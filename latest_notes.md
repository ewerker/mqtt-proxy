## English

### Presence / Status Topics
- The proxy now publishes a retained gateway presence value on `<root>/2/stat/!<gatewayNodeId>`.
- Payloads:
  - `online` on successful broker connection
  - `offline` on clean shutdown (and via MQTT LWT on unclean exit)
  - `broken` when the proxy detects a health failure and is about to exit/restart
- Optional retained JSON detail is published on `<root>/proxy/status/!<gatewayNodeId>` (includes `reasons[]` on `broken`).

### Documentation
- Added a dedicated "Presence / Status Topics" section to `CONFIG.md` with exact topics and payload semantics.

## Deutsch

### Presence- / Status-Topics
- Der Proxy veroeffentlicht jetzt einen retained Presence-Status auf `<root>/2/stat/!<gatewayNodeId>`.
- Payloads:
  - `online` bei erfolgreicher Broker-Verbindung
  - `offline` bei sauberem Shutdown (und via MQTT-LWT bei unsauberem Abbruch)
  - `broken` wenn der Proxy einen Health-Fehler erkennt und gleich beendet/neustartet
- Optional werden retained JSON-Details auf `<root>/proxy/status/!<gatewayNodeId>` veroeffentlicht (enthaelt bei `broken` u.a. `reasons[]`).

### Dokumentation
- Ein eigener Abschnitt "Presence / Status Topics" wurde in `CONFIG.md` hinzugefuegt (exakte Topics + Semantik).

