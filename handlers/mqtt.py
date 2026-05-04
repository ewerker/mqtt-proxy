"""MQTT Handler for MQTT Proxy."""
# Copyright (c) 2026 LN4CY
# This software is licensed under the MIT License. See LICENSE file for details.

import json
import time
import logging
import ssl
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from meshtastic import mesh_pb2
from meshtastic.protobuf import mqtt_pb2

logger = logging.getLogger("mqtt-proxy.handlers.mqtt")

class MQTTHandler:
    """Handles MQTT connection and message processing."""

    def __init__(self, config, node_id, on_message_callback=None, deduplicator=None):
        self.config = config
        self.node_id = node_id
        self.deduplicator = deduplicator
        self.client = None
        self.connected = False
        self.health_check_enabled = False
        self.last_activity = 0
        self.tx_count = 0
        self.tx_failures = 0
        self.rx_count = 0
        
        # Callback for when an MQTT message is received that needs to go to the radio
        # Signature: (topic, payload, retained)
        self.on_message_callback = on_message_callback
        
        self.prefixed_node_id = f"!{node_id}" if node_id else None
        self.current_mqtt_cfg = None
        self._presence_published = False

    def _presence_topic(self):
        """Return the standard Meshtastic presence topic for this gateway."""
        if not getattr(self, "mqtt_root", None) or not self.prefixed_node_id:
            return None
        return f"{self.mqtt_root}/2/stat/{self.prefixed_node_id}"

    def _presence_detail_topic(self):
        """
        Extra status detail topic (JSON).

        This is intentionally outside the Meshtastic /2/* namespace so it won't be
        forwarded to the radio by accident.
        """
        if not getattr(self, "mqtt_root", None) or not self.prefixed_node_id:
            return None
        return f"{self.mqtt_root}/proxy/status/{self.prefixed_node_id}"

    def publish_presence(self, status, detail=None, retain=True):
        """
        Publish proxy presence.

        Topics:
          - <root>/2/stat/!<nodeId>            payload: "online"|"offline"|"broken" (retained)
          - <root>/proxy/status/!<nodeId>      payload: JSON detail (retained)

        Notes:
          - The LWT is also set to publish "offline" on <root>/2/stat/!<nodeId> for unclean exits.
          - For clean shutdowns, callers should explicitly publish "offline" before disconnect().
        """
        if not self.client or not self.prefixed_node_id:
            return False

        status_norm = str(status or "").strip().lower()
        if status_norm not in ("online", "offline", "broken"):
            raise ValueError(f"Invalid presence status: {status}")

        topic_stat = self._presence_topic()
        if not topic_stat:
            return False

        ok = True
        try:
            self.client.publish(topic_stat, payload=status_norm, retain=bool(retain))
            self._presence_published = True
        except Exception:
            ok = False

        # Optional detail JSON for richer monitoring.
        try:
            topic_detail = self._presence_detail_topic()
            if topic_detail:
                payload = {
                    "status": status_norm,
                    "ts": int(time.time()),
                    "gateway_id": self.prefixed_node_id,
                    "app": "mqtt-proxy",
                }
                if detail and isinstance(detail, dict):
                    payload.update(detail)
                self.client.publish(topic_detail, payload=json.dumps(payload, ensure_ascii=False), retain=bool(retain))
        except Exception:
            ok = False

        return ok

    def configure(self, node_mqtt_config):
        """Configure the MQTT client based on node settings."""
        self.current_mqtt_cfg = node_mqtt_config
        cfg = node_mqtt_config

        if not getattr(cfg, 'enabled', False):
            logger.warning("⚠️ MQTT is NOT enabled in node config! Please enable it via 'meshtastic --set mqtt.enabled true'")
        
        # Safely get attributes with defaults
        mqtt_address = getattr(cfg, 'address', None)
        mqtt_port = int(getattr(cfg, 'port', 1883) or 1883)
        mqtt_username = getattr(cfg, 'username', None)
        mqtt_password = getattr(cfg, 'password', None)
        self.mqtt_root = getattr(cfg, 'root', 'msh')
        
        logger.info("🌐 Starting MQTT Client...")
        logger.info("  📡 Server: %s:%d", mqtt_address, mqtt_port)
        logger.info("  👤 User: %s", mqtt_username)
        logger.info("  🌳 Root Topic: %s", self.mqtt_root)
        
        # Client ID matching iOS pattern
        client_id = f"MeshtasticPythonMqttProxy-{self.node_id}"
        logger.info("🆔 Setting MQTT Client ID: %s", client_id)
        
        client_kwargs = {
            "callback_api_version": mqtt.CallbackAPIVersion.VERSION2,
            "client_id": client_id,
        }
        if getattr(self.config, "mqtt_publish_expiry_enabled", False):
            client_kwargs["protocol"] = mqtt.MQTTv5
        self.client = mqtt.Client(**client_kwargs)
        if mqtt_username and mqtt_password:
            self.client.username_pw_set(mqtt_username, mqtt_password)
            
        # SSL/TLS Configuration
        # Meshtastic protobuf fields may appear in snake_case on current Python builds.
        use_ssl = getattr(cfg, 'tlsEnabled', getattr(cfg, 'tls_enabled', False))
        if mqtt_address and "mqtt.meshtastic.org" in mqtt_address:
             use_ssl = True
             
        if use_ssl:
             logger.info("🔒 SSL/TLS Enabled")
             context = ssl.create_default_context()
             context.check_hostname = False
             context.verify_mode = ssl.CERT_NONE
             self.client.tls_set_context(context)
             
             if mqtt_port == 1883:
                 mqtt_port = 8883
                 logger.info("🔄 Switching to default SSL port: 8883")
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Store for connection
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port

    def start(self):
        """Connect and start the MQTT loop."""
        if not self.client or not self.mqtt_address:
            logger.error("❌ MQTT not configured, cannot start.")
            return

        try:
            if not self.mqtt_address or self.mqtt_address == "255.255.255.255":
                logger.warning("⚠️ Invalid MQTT address in config: %s", self.mqtt_address)
                return

            # LWT (Last Will and Testament)
            if self.node_id:
               topic_stat = f"{self.mqtt_root}/2/stat/{self.prefixed_node_id}"
               # Unclean exit => broker publishes offline (retained).
               self.client.will_set(topic_stat, payload="offline", retain=True)
            
            logger.info(f"🔌 Connecting to {self.mqtt_address}:{self.mqtt_port}...")
            self.client.connect(self.mqtt_address, self.mqtt_port, 60)
            self.client.loop_start()
            
        except Exception as e:
            logger.error("❌ Failed to connect to MQTT broker: %s", e)

    def stop(self):
        """Stop the MQTT loop and disconnect."""
        if self.client:
            try:
                # Clean shutdown => publish offline explicitly (retained).
                try:
                    self.publish_presence("offline", detail={"reason": "shutdown"})
                except Exception:
                    pass
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass

    def publish(self, topic, payload, retain=False):
        """Publish a message to MQTT."""
        if self.client:
            gateway_id = self.prefixed_node_id or "!unknown"
            properties = self._build_publish_properties()
            logger.info(
                "TX MQTT %s -> broker topic=%s retain=%s bytes=%d expiry=%s",
                gateway_id,
                topic,
                retain,
                len(payload),
                getattr(properties, "MessageExpiryInterval", "-") if properties else "-",
            )
            publish_kwargs = {"retain": retain}
            if properties is not None:
                publish_kwargs["properties"] = properties
            result = self.client.publish(topic, payload, **publish_kwargs)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.tx_count += 1
                self.tx_failures = 0
                return True
            else:
                logger.warning("⚠️ MQTT publish failed: rc=%s", result.rc)
                self.tx_failures += 1
                return False
        return False

    def publish_json(self, topic, payload, retain=False):
        """Publish a JSON-serializable payload to MQTT."""
        return self.publish(topic, json.dumps(payload, ensure_ascii=False), retain=retain)

    def _build_publish_properties(self):
        """Build MQTT 5 publish properties when message expiry is enabled."""
        if not getattr(self.config, "mqtt_publish_expiry_enabled", False):
            return None

        expiry_seconds = max(0, int(getattr(self.config, "mqtt_publish_expiry_seconds", 86400)))
        properties = Properties(PacketTypes.PUBLISH)
        properties.MessageExpiryInterval = expiry_seconds
        return properties

    def _compute_virtual_channel_hash(self, channel_name):
        """
        Compute a synthetic PSK hash for a virtual channel name.
        
        Meshtastic firmware uses packet.channel (a uint32 PSK hash) to look up
        the decryption key for incoming packets. By replacing the real hash with
        a deterministic but synthetic value derived from the virtual channel name,
        the radio will find no matching key and cannot decrypt or rebroadcast.
        
        The hash is intentionally kept in the range 200-254 to avoid colliding
        with real channel hashes (LongFast=0, and most common values near 0).
        """
        h = 0
        for b in channel_name.encode('utf-8'):
            h = (h * 31 + b) & 0xFF
        # Shift into 200-254 range to reduce collision likelihood with real channels
        return 200 + (h % 55)

    def _mutate_virtual_channel_payload(self, payload, new_channel_name):
        """
        Mutate ServiceEnvelope protobuf to rewrite the PSK hash.

        Changes:
          - packet.channel       : PSK hash    → synthetic hash unique to the virtual channel

        The string name (envelope.channel_id) and encrypted payload bytes 
        (packet.encrypted) are left completely untouched. 
        MeshMonitor can still decrypt the message using the original key and original
        channel name via its Channel Database entry.

        This prevents the radio firmware from matching its local PSK and rebroadcasting
        the packet over RF, which would cause crosstalk between MQTT server regions.
        """
        try:
            from meshtastic.protobuf import mqtt_pb2
            envelope = mqtt_pb2.ServiceEnvelope()
            envelope.ParseFromString(payload)

            original_channel_hash = envelope.packet.channel

            # Rewrite only the PSK hash to blind the radio firmware
            envelope.packet.channel = self._compute_virtual_channel_hash(new_channel_name)

            mutated = envelope.SerializeToString()
            logger.debug(
                "🔒 Payload mutation: packet.channel %d→%d",
                original_channel_hash, envelope.packet.channel
            )
            return mutated
        except Exception as e:
            logger.warning("⚠️ Failed to mutate virtual channel payload, using original: %s", e)
            return payload

    def _on_connect(self, client, userdata, flags, rc, props=None):
        logger.info("✅ MQTT Connected with result code: %s", rc)
        if rc == 0:
            self.connected = True
            self.health_check_enabled = True
            self.last_activity = time.time()
            
            if self.current_mqtt_cfg:
                root_topic = self.mqtt_root
                
                # Publish Online Presence
                self.publish_presence(
                    "online",
                    detail={
                        "reason": "connected",
                        "mqtt": {"host": self.mqtt_address, "port": int(self.mqtt_port)},
                    },
                )
                
                # Subscribe to ALL Encrypted Traffic
                topic_enc = f"{root_topic}/2/e/#"
                logger.info("📥 Subscribing to Encrypted Wildcard: %s", topic_enc)
                client.subscribe(topic_enc)

                # Subscribe to simple plaintext commands handled directly by the proxy.
                topic_send = f"{root_topic}/proxy/send/{self.prefixed_node_id}/#"
                logger.info("📥 Subscribing to Plaintext Commands: %s", topic_send)
                client.subscribe(topic_send)
                
                # Subscribe to extra MQTT root topics
                subscribed_roots = {root_topic}
                for extra_root, _ in getattr(self.config, 'extra_mqtt_roots', []):
                    if extra_root not in subscribed_roots:
                        extra_topic = f"{extra_root}/2/e/#"
                        logger.info("📥 Subscribing to Extra Root: %s", extra_topic)
                        client.subscribe(extra_topic)
                        subscribed_roots.add(extra_root)
        else:
            self.connected = False
            logger.error("❌ MQTT Connect failed: %s", rc)

    def _on_disconnect(self, client, userdata, flags, rc, props=None):
        self.connected = False
        if rc != 0:
            logger.warning("⚠️ MQTT Disconnected unexpectedly (rc=%s). Will attempt to reconnect.", rc)
        else:
            logger.info("🛑 MQTT Disconnected gracefully.")

    def _on_message(self, client, userdata, message):
        """Handle incoming MQTT messages."""
        try:
            # Check if this is an echo of our own message (Firmware needs this to generate Implicit ACKs)
            is_echo = False
            try:
                envelope = mqtt_pb2.ServiceEnvelope()
                envelope.ParseFromString(message.payload)
                if envelope.gateway_id:
                    if self.node_id and (envelope.gateway_id == self.node_id or envelope.gateway_id == self.prefixed_node_id):
                        packet = envelope.packet
                        # Only allow echo bypass for packets that are eligible for Implicit ACKs
                        if packet.HasField("encrypted") or \
                           (packet.HasField("decoded") and packet.decoded.request_id):
                            is_echo = True
            except Exception:
                pass

            # Skip stat messages
            if "/stat/" in message.topic:
                return

            # Topic check loop prevention (Bypass for echoes so firmware gets its ACK)
            if self.node_id and message.topic.endswith(self.prefixed_node_id) and not is_echo:
                 logger.debug("🛡️ Ignoring own MQTT message (Loop protection): %s", message.topic)
                 return

            # Enhanced Loop Protection: Check for duplicate Packet ID from same Sender
            if not is_echo:
                try:
                    sender_node_id = None
                    packet_id = None
                    
                    # Attempt to parse as ServiceEnvelope
                    try:
                        envelope = mqtt_pb2.ServiceEnvelope()
                        envelope.ParseFromString(message.payload)
                        packet = envelope.packet
                        
                        sender_val = getattr(packet, "from")
                        if sender_val:
                             sender_node_id = f"{sender_val:08x}"
                        
                        if packet.id:
                             packet_id = packet.id
                    except Exception:
                        # Fallback? Maybe it's a raw MeshPacket?
                        try:
                            packet = mesh_pb2.MeshPacket()
                            packet.ParseFromString(message.payload)
                            sender_val = getattr(packet, "from")
                            if sender_val:
                                 sender_node_id = f"{sender_val:08x}"
                            
                            if packet.id:
                                 packet_id = packet.id
                        except:
                            pass
                    
                    if self.deduplicator and sender_node_id and packet_id:
                         if self.deduplicator.is_duplicate(sender_node_id, packet_id):
                             logger.info(f"🛡️ Ignoring duplicate MQTT message from {sender_node_id} (PacketId={packet_id}) (Loop Prevention)")
                             return

                except Exception as e:
                    logger.debug(f"⚠️ Error checking loop tracker: {e}")
             
            # Skip retained messages by default - they're historical state, not new mesh traffic
            # This prevents startup floods when connecting to broker with many retained messages
            if message.retain and not (self.config and getattr(self.config, 'mqtt_forward_retained', False)):
                logger.debug(f"⏭️ Skipping retained MQTT message: {message.topic}")
                return
              
            modified_topic = message.topic
            modified_payload = message.payload
            
            # Virtual Channel mapping for Extra Roots
            extra_roots = getattr(self.config, 'extra_mqtt_roots', [])
            for er_root, er_prefix in extra_roots:
                if modified_topic.startswith(f"{er_root}/"):
                    # Avoid rewriting if the configured extra root exactly matches the primary root
                    if self.mqtt_root and er_root == self.mqtt_root:
                        continue
                        
                    parts = modified_topic.split("/")
                    if len(parts) >= 4 and parts[-3] in ("e", "c"):
                        channel_name = parts[-2]
                        # Prevent double-prefixing if we receive our own re-published message
                        if not channel_name.startswith(f"{er_prefix}-"):
                            new_channel_name = f"{er_prefix}-{channel_name}"
                            parts[-2] = new_channel_name
                            modified_topic = "/".join(parts)
                            # CRITICAL: Also mutate the protobuf payload to change the channel
                            # identity field (packet.channel PSK hash).
                            # The radio firmware uses packet.channel (PSK hash) to look up
                            # its decryption key. By replacing it with a synthetic hash that
                            # no local radio has configured, the firmware cannot decrypt the
                            # packet and will NOT rebroadcast it over RF.
                            # The encrypted bytes and original channel_id string are left 
                            # untouched so MeshMonitor can still decrypt using the original 
                            # key and channel name via its Channel Database.
                            modified_payload = self._mutate_virtual_channel_payload(
                                message.payload, new_channel_name
                            )
                            logger.info("🔄 Virtual Channel Rewrite: %s -> %s (extra root: %s)",
                                        channel_name, new_channel_name, er_root)
                    break

            self.last_activity = time.time()
            self.rx_count += 1
            
            logger.info("📥 MQTT->Node: Topic=%s Size=%d bytes Retained=%s", modified_topic, len(modified_payload), message.retain)
            
            if self.on_message_callback:
                self.on_message_callback(modified_topic, modified_payload, message.retain)
                
        except Exception as e:
            logger.error("❌ Error handling MQTT message: %s", e)
