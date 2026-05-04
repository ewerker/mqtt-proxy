## English

### Console Visibility
- Improved `Node -> MQTT` console visibility so incoming text packets and mirrored broker publishes are shown consistently.
- Added clear `TX MQTT ... -> broker` lines for broker publishes.
- Aligned RX text preview logging with the TX style for easier live troubleshooting.

### MQTT 5 Message Expiry
- Added optional MQTT 5 Message Expiry support for broker publishes.
- New settings:
  - `MQTT_PUBLISH_EXPIRY_ENABLED`
  - `MQTT_PUBLISH_EXPIRY_SECONDS`
- Example/default usage in local config is `86400` seconds (24 hours).

### Documentation and Tests
- Updated `.env` templates, `README.md`, and `CONFIG.md`.
- Added coverage for visible broker publish logging and MQTT 5 expiry properties.

## Deutsch

### Konsolen-Sichtbarkeit
- Die Sichtbarkeit fuer `Node -> MQTT` in der Konsole wurde verbessert, damit eingehende Textpakete und gespiegelte Broker-Publishes konsistent sichtbar sind.
- Klare `TX MQTT ... -> broker`-Zeilen fuer Broker-Publishes wurden hinzugefuegt.
- Die RX-Textvorschau wurde an den TX-Stil angeglichen, damit Live-Debugging leichter wird.

### MQTT-5-Message-Expiry
- Optionale MQTT-5-Message-Expiry fuer Broker-Publishes wurde hinzugefuegt.
- Neue Einstellungen:
  - `MQTT_PUBLISH_EXPIRY_ENABLED`
  - `MQTT_PUBLISH_EXPIRY_SECONDS`
- Beispiel-/Standardnutzung in der lokalen Konfiguration ist `86400` Sekunden (24 Stunden).

### Dokumentation und Tests
- `.env`-Vorlagen, `README.md` und `CONFIG.md` wurden aktualisiert.
- Testabdeckung fuer sichtbare Broker-Publish-Logs und MQTT-5-Expiry-Properties wurde hinzugefuegt.
