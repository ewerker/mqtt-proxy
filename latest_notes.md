## English

### RX Channel Metadata
- Added `channel_index` and `channel_name` to mirrored RX JSON records.
- Kept the existing `channel` field as a legacy/raw fallback for compatibility.
- Group packets without explicit channel metadata are now treated as channel `0` (`LongFast`) so default traffic can be routed consistently.

### RX Topic Routing
- Added channel-specific receive topics:
  - `msh/<region>/proxy/rx/!<gateway>/group/<channelIndex>`
- Added sender-specific direct receive topics:
  - `msh/<region>/proxy/rx/!<gateway>/direct/!<fromNodeId>`
- Existing compatibility topics such as `scope/group` and `scope/dm` remain unchanged.

### Documentation
- Updated README and CONFIG docs to explain the new RX fields and topic structure for browser and app consumers.

## Deutsch

### RX-Channel-Metadaten
- Gespiegelte RX-JSON-Datensaetze enthalten jetzt `channel_index` und `channel_name`.
- Das bestehende Feld `channel` bleibt als Legacy-/Roh-Fallback zur Kompatibilitaet erhalten.
- Gruppenpakete ohne explizite Channel-Metadaten werden jetzt als Kanal `0` (`LongFast`) behandelt, damit Default-Traffic konsistent geroutet werden kann.

### RX-Topic-Routing
- Neue channelspezifische Receive-Topics:
  - `msh/<region>/proxy/rx/!<gateway>/group/<channelIndex>`
- Neue absenderspezifische Direct-Receive-Topics:
  - `msh/<region>/proxy/rx/!<gateway>/direct/!<fromNodeId>`
- Bestehende Kompatibilitaets-Topics wie `scope/group` und `scope/dm` bleiben unveraendert erhalten.

### Dokumentation
- README und CONFIG wurden aktualisiert und erklaeren jetzt die neuen RX-Felder und die Topic-Struktur fuer Browser- und App-Clients.
