## English

### Gateway-Specific Topics
- Switched plaintext send topics from shared paths to gateway-specific paths.
- The proxy now subscribes only to `.../proxy/send/!<gateway>/#` for its own local node id.
- ACK lifecycle topics are now published under `.../proxy/ack/!<gateway>/<client_ref>`.
- This makes multiple proxy instances on the same broker addressable by topic path.

### Documentation
- Updated `README.md` and `CONFIG.md` to document the new send and ACK topic structure.
- Added concrete examples for group send, direct send, and ACK retrieval.

### Tests
- Updated plaintext command tests for gateway-specific send topics.
- Updated ACK flow tests for gateway-specific ACK topics.

## Deutsch

### Gateway-spezifische Topics
- Die Plaintext-Sendepfade wurden auf gateway-spezifische Topics umgestellt.
- Der Proxy abonniert jetzt nur noch `.../proxy/send/!<gateway>/#` fuer seine eigene lokale Node-ID.
- ACK-Lifecycle-Topics werden jetzt unter `.../proxy/ack/!<gateway>/<client_ref>` veroeffentlicht.
- Dadurch lassen sich mehrere Proxy-Instanzen auf demselben Broker sauber ueber den Topic-Pfad adressieren.

### Dokumentation
- `README.md` und `CONFIG.md` wurden auf die neue Send- und ACK-Topic-Struktur aktualisiert.
- Konkrete Beispiele fuer Gruppensenden, Direktsenden und ACK-Abruf wurden ergaenzt.

### Tests
- Die Plaintext-Command-Tests wurden auf gateway-spezifische Sendetopics angepasst.
- Die ACK-Flow-Tests wurden auf gateway-spezifische ACK-Topics angepasst.
