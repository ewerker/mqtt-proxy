#!/usr/bin/env python3
# Copyright (c) 2026 LN4CY
# This software is licensed under the MIT License. See LICENSE file for details.
import time
import logging
import signal
import sys
import os
import argparse
import json
import threading
from pubsub import pub

from config import cfg
from version import APP_NAME, __version__
from handlers.listener import ReceiveMirrorListener, sanitize_value
from handlers.mqtt import MQTTHandler
from handlers.node_list import NodeListPublisher
from handlers.meshtastic import create_interface
from handlers.node_tracker import PacketDeduplicator
from handlers.queue import MessageQueue

# Force unbuffered standard output and utf-8 encoding for real-time logging when run via spawn/exec
if sys.stdout and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if sys.stderr and not sys.stderr.isatty():
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

class ConsoleFormatter(logging.Formatter):
    """Colorize console output for level and common RX/TX lifecycle messages."""

    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"

    LEVEL_COLORS = {
        logging.DEBUG: "\033[37m",
        logging.INFO: "\033[36m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }

    MESSAGE_COLORS = (
        ("TX IMPLICIT_ACK", "\033[95m"),
        ("TX ACK", "\033[92m"),
        ("TX SENT", "\033[96m"),
        ("TX NAK", "\033[91m"),
        ("TX TIMEOUT", "\033[93m"),
        ("TX QUEUE", "\033[94m"),
        ("TX MQTT", "\033[94m"),
        ("TX DM", "\033[94m"),
        ("TX GROUP", "\033[94m"),
        ("RX ", "\033[92m"),
    )

    def __init__(self, use_color):
        super().__init__("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        self.use_color = use_color

    def format(self, record):
        original_levelname = record.levelname
        original_name = record.name
        original_message = record.msg
        original_args = record.args

        if self.use_color:
            level_color = self.LEVEL_COLORS.get(record.levelno, "")
            record.levelname = f"{self.BOLD}{level_color}{original_levelname}{self.RESET}"
            record.name = f"{self.DIM}{original_name}{self.RESET}"
            message_text = record.getMessage()
            record.msg = self._colorize_message(message_text, record.levelno)
            record.args = ()

        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname
            record.name = original_name
            record.msg = original_message
            record.args = original_args

    def _colorize_message(self, message_text, levelno):
        for prefix, color in self.MESSAGE_COLORS:
            if message_text.startswith(prefix):
                return f"{self.BOLD}{color}{prefix}{self.RESET}{message_text[len(prefix):]}"

        fallback = self.LEVEL_COLORS.get(levelno)
        if fallback and levelno >= logging.WARNING:
            return f"{fallback}{message_text}{self.RESET}"
        return message_text


def configure_logging():
    """Configure console logging with optional ANSI colors when attached to a TTY."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(cfg.log_level)

    use_color = bool(
        sys.stdout
        and hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(cfg.log_level)
    handler.setFormatter(ConsoleFormatter(use_color=use_color))
    root_logger.addHandler(handler)


configure_logging()
logger = logging.getLogger("mqtt-proxy")
ENV_RELOAD_EXIT_CODE = 75


def build_runtime_notice(stage, **fields):
    """Build a compact console notice for high log levels."""
    parts = [stage]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    return " | ".join(parts)


def emit_runtime_notice(stage, **fields):
    """Write a direct console notice when the configured log level suppresses INFO."""
    if cfg.log_level <= logging.INFO:
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    line = f"{timestamp} [NOTICE] mqtt-proxy: {build_runtime_notice(stage, **fields)}"
    if sys.stdout:
        sys.stdout.write(f"{line}\n")
        sys.stdout.flush()

class MQTTProxy:
    """
    Main application class for MQTT Proxy.
    Orchestrates the connection between Meshtastic and MQTT.
    """
    def __init__(self):
        self.running = True
        self.iface = None
        self.mqtt_handler = None
        
        # Initialize Packet Deduplicator (Loop Prevention)
        self.deduplicator = PacketDeduplicator()
        
        # Initialize Message Queue
        # We pass a lambda to always get the current interface instance
        self.message_queue = MessageQueue(cfg, lambda: self.iface)
        self.listener = ReceiveMirrorListener(cfg, lambda: self.iface, lambda: self.mqtt_handler)
        self.node_list_publisher = NodeListPublisher(cfg, lambda: self.iface, lambda: self.mqtt_handler)
        self.pending_acks = {}
        self.pending_ack_lock = threading.Lock()
        self.pending_ack_ttl_seconds = 60
        self.env_file_path = os.path.join(os.getcwd(), ".env")
        self.env_hot_reload_last_check = 0.0
        self.env_hot_reload_last_mtime = self._get_env_file_mtime()
        
        # State
        self.last_radio_activity = 0
        self.connection_lost_time = 0
        self.last_probe_time = 0
        self.last_status_log_time = 0

        pub.subscribe(self.on_radio_packet_received, "meshtastic.receive")

    def start(self):
        emit_runtime_notice(
            "START",
            app=APP_NAME,
            version=__version__,
            interface=cfg.interface_type.upper(),
            log_level=cfg.log_level_str,
            verbose=str(bool(getattr(cfg, "verbose", False))).lower(),
        )
        if getattr(cfg, "verbose", False):
            logger.info("Verbose console output enabled.")
        logger.info("🚀 %s %s starting (interface: %s)...", APP_NAME, __version__, cfg.interface_type.upper())

        # Subscribe to events
        pub.subscribe(self.on_connection, "meshtastic.connection.established")
        pub.subscribe(self.on_connection_lost, "meshtastic.connection.lost")
        
        # Signal handling
        signal.signal(signal.SIGINT, self.handle_sigint)
        signal.signal(signal.SIGTERM, self.handle_sigint)

        while self.running:
            self.iface = None
            try:
                # Create interface (this connects to the radio)
                self.iface = create_interface(cfg, self)
                logger.info("🔌 TCP/Serial connection initiated...")
                
                # Wait for node configuration (connection + config packet)
                self._wait_for_config()
                
                # Initialize MQTT after config is fully loaded
                self._init_mqtt()
                
                logger.info("✅ Node config fully loaded. Proxy active.")
                
                # Start (or restart) the message queue
                self.message_queue.start()
                self.node_list_publisher.publish_if_due(force=True)
                
                # Main Loop
                while self.running and self.iface:
                    time.sleep(1)
                    current_time = time.time()
                    
                    self._check_env_hot_reload(current_time)
                    self._log_status(current_time)
                    self.node_list_publisher.publish_if_due(current_time=current_time)
                    self._expire_pending_acks(current_time)
                    health_ok, reasons = self._perform_health_check(current_time)
                    self._update_heartbeat(current_time, health_ok, reasons)
                    
            except Exception as e:
                logger.error("❌ Connection error: %s", e)
            finally:
                self._cleanup()

            if self.running:
                logger.info("⏳ Reconnecting in 5 seconds...")
                time.sleep(5)

    def _wait_for_config(self):
        """Wait for the node to provide its configuration."""
        wait_start = time.time()
        while self.running:
            if self.iface.localNode and self.iface.localNode.nodeNum != -1 and self.iface.localNode.moduleConfig:
                return
            
            if time.time() - wait_start > cfg.config_wait_timeout:
                logger.warning(f"⚠️ Connected but no config received for {cfg.config_wait_timeout}s...")
                # We don't exit, just warn, as sometimes config takes a while or is partial
            
            time.sleep(cfg.poll_interval)

    def _get_env_file_mtime(self):
        """Return the current mtime of the local .env file or None when absent."""
        try:
            return os.path.getmtime(self.env_file_path)
        except OSError:
            return None

    def _check_env_hot_reload(self, current_time):
        """Restart the process when the local .env file changes on disk."""
        if not getattr(cfg, "env_hot_reload_enabled", True):
            return

        interval = max(0.25, float(getattr(cfg, "env_hot_reload_interval_seconds", 2)))
        if current_time - self.env_hot_reload_last_check < interval:
            return

        self.env_hot_reload_last_check = current_time
        current_mtime = self._get_env_file_mtime()

        if self.env_hot_reload_last_mtime is None:
            self.env_hot_reload_last_mtime = current_mtime
            return

        if current_mtime is None:
            logger.info(".env was removed. Restarting process to reload runtime configuration.")
            raise SystemExit(ENV_RELOAD_EXIT_CODE)

        if current_mtime != self.env_hot_reload_last_mtime:
            logger.info(".env changed on disk. Restarting process to reload runtime configuration.")
            raise SystemExit(ENV_RELOAD_EXIT_CODE)

    def on_connection(self, interface, **kwargs):
        """Callback when Meshtastic connection is established."""
        node = interface.localNode
        if not node:
            logger.warning("⚠️ No localNode available")
            return

        self.last_radio_activity = time.time()
        self.connection_lost_time = 0

        # Node ID
        try:
            if hasattr(node, "nodeId"):
                node_id = node.nodeId.replace('!', '')
            else:
                node_id = "{:08x}".format(node.nodeNum)
        except Exception as e:
            logger.error("❌ Error getting node ID: %s", e)
            node_id = "unknown"

        logger.info("📻 Connected to node !%s", node_id)

    def _init_mqtt(self):
        """Initialize and start the MQTT handler."""
        if not self.iface or not self.iface.localNode:
            logger.warning("⚠️ No interface or localNode for MQTT initialization")
            return

        node = self.iface.localNode
        
        # Determine Node ID
        try:
            if hasattr(node, "nodeId"):
                node_id = node.nodeId.replace('!', '')
            else:
                node_id = "{:08x}".format(node.nodeNum)
        except Exception:
            node_id = "unknown"

        # Cleanup existing handler if any
        if self.mqtt_handler:
            logger.info("🛑 Stopping old MQTT handler before restart...")
            self.mqtt_handler.stop()
            self.mqtt_handler = None

        # Initialize MQTT if config exists
        if node.moduleConfig and node.moduleConfig.mqtt:
            logger.info("🌐 Initializing MQTT Handler for node !%s...", node_id)
            self.mqtt_handler = MQTTHandler(cfg, node_id, self.on_mqtt_message_to_radio, deduplicator=self.deduplicator)
            self.mqtt_handler.configure(node.moduleConfig.mqtt)
            emit_runtime_notice(
                "MQTT_TARGET",
                node=f"!{node_id}",
                broker=f"{self.mqtt_handler.mqtt_address}:{self.mqtt_handler.mqtt_port}",
                root=self.mqtt_handler.mqtt_root,
                log_level=cfg.log_level_str,
            )
            self.mqtt_handler.start()
        else:
            logger.warning("⚠️ No MQTT configuration found on node !%s!", node_id)

    def on_connection_lost(self, interface, **kwargs):
        """Callback when connection to radio is lost."""
        if self.connection_lost_time > 0 and (time.time() - self.connection_lost_time < 2):
            return # Debounce

        logger.warning("⚠️ Meshtastic connection reported LOST!")
        self.connection_lost_time = time.time()

        # Force the main loop to unwind quickly so we can clean up and reconnect.
        self.iface = None

    def on_mqtt_message_to_radio(self, topic, payload, retained):
        """Callback from MQTT Handler to send message to Radio."""
        if self._handle_plaintext_command(topic, payload):
            return

        # 1. Extract channel name from topic
        channel_name = self._extract_channel_from_topic(topic)
        
        # 2. Check if downlink is enabled for this channel
        if channel_name:
            if not self._is_channel_downlink_enabled(channel_name):
                logger.info("🛡️ Dropping MQTT->Node message (downlink_enabled=False for channel '%s'): %s", 
                            channel_name, topic)
                return

        self._log_outgoing_queue_enqueue(topic, payload, retained, channel_name)
        # Queue the message instead of sending directly
        self.message_queue.put(topic, payload, retained)

    def _handle_plaintext_command(self, topic, payload):
        """Handle simple MQTT plaintext send commands for group and direct sends."""
        command = self._parse_plaintext_command(topic, payload)
        if not command:
            return False

        if command["mode"] == "invalid":
            return True

        if not self.iface:
            logger.warning("⚠️ Cannot send plaintext command without an active Meshtastic interface")
            return True

        try:
            text = command["text"]
            channel_index = command["channel_index"]
            want_ack = command["want_ack"]
            hop_limit = command["hop_limit"]
            client_ref = command.get("client_ref")
            effective_want_ack = bool(want_ack and client_ref)
            ack_callback = self.onAckNak if effective_want_ack else None

            if want_ack and not client_ref:
                logger.info("Skipping ACK path because no client_ref was provided for topic %s", topic)

            if command["mode"] == "group":
                sent_packet = self.iface.sendText(
                    text,
                    destinationId="^all",
                    wantAck=effective_want_ack,
                    onResponse=ack_callback,
                    channelIndex=channel_index,
                    hopLimit=hop_limit,
                )
            else:
                destination_id = command["destination_id"]
                sent_packet = self.iface.sendText(
                    text,
                    destinationId=destination_id,
                    wantAck=effective_want_ack,
                    onResponse=ack_callback,
                    channelIndex=channel_index,
                    hopLimit=hop_limit,
                )
            self._log_plaintext_send(command, sent_packet, effective_want_ack)
            if effective_want_ack:
                self._remember_pending_ack(command, sent_packet)
        except Exception as e:
            logger.error("❌ Failed to send plaintext MQTT command: %s", e)

        return True

    def _parse_plaintext_command(self, topic, payload):
        """Parse simple MQTT command topics into send instructions."""
        root_topic = getattr(self.mqtt_handler, "mqtt_root", None) if self.mqtt_handler else None
        if not root_topic:
            return None

        command_prefix = f"{root_topic}/proxy/send/"
        if not topic.startswith(command_prefix):
            return None

        topic_suffix = topic[len(command_prefix):]
        topic_parts = [part for part in topic_suffix.split("/") if part]
        if len(topic_parts) < 3:
            logger.warning("⚠️ Ignoring plaintext command with incomplete topic: %s", topic)
            return {"mode": "invalid", "text": "", "channel_index": 0, "want_ack": False, "hop_limit": None}

        gateway_id = topic_parts[0]
        expected_gateway_id = self._current_node_id()
        if gateway_id != expected_gateway_id:
            logger.warning(
                "⚠️ Ignoring plaintext command for different gateway %s (local gateway is %s): %s",
                gateway_id,
                expected_gateway_id,
                topic,
            )
            return {"mode": "invalid", "text": "", "channel_index": 0, "want_ack": False, "hop_limit": None}

        body = self._decode_plaintext_command_payload(payload)
        if not body["text"]:
            logger.warning("⚠️ Ignoring plaintext command without text payload: %s", topic)
            return {"mode": "invalid", "text": "", "channel_index": 0, "want_ack": False, "hop_limit": None}

        mode = topic_parts[1].lower()
        if mode == "group":
            try:
                channel_index = int(topic_parts[2])
            except ValueError:
                logger.warning("⚠️ Invalid group channel in plaintext command topic: %s", topic)
                return {"mode": "invalid", "text": "", "channel_index": 0, "want_ack": False, "hop_limit": None}

            body["mode"] = "group"
            body["channel_index"] = channel_index
            body["command_topic"] = topic
            body["gateway_id"] = gateway_id
            return body

        if mode == "direct":
            destination_id = topic_parts[2]
            if not destination_id.startswith("!"):
                logger.warning("⚠️ Direct plaintext command target must start with '!': %s", topic)
                return {"mode": "invalid", "text": "", "channel_index": 0, "want_ack": False, "hop_limit": None}

            body["mode"] = "direct"
            body["destination_id"] = destination_id
            body["command_topic"] = topic
            body["gateway_id"] = gateway_id
            return body

        logger.warning("⚠️ Unsupported plaintext command topic: %s", topic)
        return {"mode": "invalid", "text": "", "channel_index": 0, "want_ack": False, "hop_limit": None}

    def _decode_plaintext_command_payload(self, payload):
        """Decode plaintext command payloads from UTF-8 text or small JSON envelopes."""
        text_payload = payload.decode("utf-8").strip()
        result = {
            "text": text_payload,
            "channel_index": 0,
            "want_ack": False,
            "hop_limit": None,
            "client_ref": None,
        }

        if not text_payload:
            return result

        if text_payload.startswith("{"):
            try:
                data = json.loads(text_payload)
                result["text"] = str(data.get("text") or "").strip()
                result["channel_index"] = int(data.get("channel", 0) or 0)
                result["want_ack"] = bool(data.get("want_ack", False))
                hop_limit = data.get("hop_limit")
                result["hop_limit"] = int(hop_limit) if hop_limit is not None else None
                client_ref = data.get("client_ref")
                result["client_ref"] = str(client_ref).strip() if client_ref is not None else None
            except Exception as e:
                logger.warning("⚠️ Failed to parse plaintext command JSON payload, falling back to raw text: %s", e)

        return result

    def _remember_pending_ack(self, command, sent_packet):
        """Store outgoing plaintext ACK tracking in memory for one minute."""
        client_ref = command.get("client_ref")
        if not client_ref:
            return

        packet_id = getattr(sent_packet, "id", None)
        if packet_id is None:
            logger.warning("âš ï¸ Plaintext command requested ACK but sendText returned no packet id")
            return

        entry = {
            "packet_id": int(packet_id),
            "client_ref": client_ref,
            "created_at": int(time.time()),
            "mode": command.get("mode"),
            "text": command.get("text"),
            "channel_index": command.get("channel_index"),
            "destination_id": command.get("destination_id", "^all"),
            "command_topic": command.get("command_topic"),
        }

        with self.pending_ack_lock:
            self.pending_acks[int(packet_id)] = entry

        if getattr(cfg, "verbose", False):
            logger.info("Tracking ACK packet_id=%s client_ref=%s", packet_id, client_ref)

        self._publish_ack_event(entry, "sent", source="send")

    def _current_node_id(self):
        """Return the current local node id when available."""
        try:
            node = getattr(self.iface, "localNode", None)
            node_id = getattr(node, "nodeId", None) if node else None
            if isinstance(node_id, str) and node_id.strip():
                return node_id

            node_num = getattr(node, "nodeNum", None) if node else None
            if isinstance(node_num, int) and node_num != -1:
                return f"!{int(node_num):08x}"
        except Exception:
            pass

        if self.mqtt_handler and getattr(self.mqtt_handler, "prefixed_node_id", None):
            return self.mqtt_handler.prefixed_node_id
        return "!unknown"

    @staticmethod
    def _text_preview(text, limit=120):
        """Return a compact single-line preview for console logging."""
        value = str(text or "").replace("\r", " ").replace("\n", " ").strip()
        if len(value) > limit:
            return f"{value[:limit - 1]}…"
        return value

    def _log_plaintext_send(self, command, sent_packet, effective_want_ack):
        """Emit a concise TX log entry for plaintext sends."""
        source_id = self._current_node_id()
        destination_id = command.get("destination_id", "^all")
        scope = "DM" if command.get("mode") == "direct" else "GROUP"
        packet_id = getattr(sent_packet, "id", None)
        packet_label = str(packet_id) if packet_id is not None else "-"
        hop_limit = command.get("hop_limit")
        hop_label = hop_limit if hop_limit is not None else "-"
        logger.info(
            "TX %s %s -> %s ch=%s hop=%s ack=%s packet=%s text=%s",
            scope,
            source_id,
            destination_id,
            command.get("channel_index", 0),
            hop_label,
            "yes" if effective_want_ack else "no",
            packet_label,
            self._text_preview(command.get("text")),
        )

    def _log_outgoing_queue_enqueue(self, topic, payload, retained, channel_name):
        """Emit a concise TX log entry for proxied MQTT messages queued for radio send."""
        if not getattr(cfg, "verbose", False):
            return

        source_id = self._current_node_id()
        channel_label = channel_name or "-"
        logger.info(
            "TX MQTT %s -> radio topic=%s channel=%s retained=%s bytes=%d",
            source_id,
            topic,
            channel_label,
            retained,
            len(payload),
        )

    def _publish_ack_event(self, entry, status, packet=None, source=None, error_reason=None):
        """Publish ACK lifecycle events for plaintext MQTT sends."""
        if not self.mqtt_handler:
            return

        payload = {
            "status": status,
            "client_ref": entry.get("client_ref"),
            "packet_id": entry.get("packet_id"),
            "mode": entry.get("mode"),
            "destination_id": entry.get("destination_id"),
            "channel_index": entry.get("channel_index"),
            "text": entry.get("text"),
            "command_topic": entry.get("command_topic"),
            "created_at": entry.get("created_at"),
            "resolved_at": int(time.time()),
        }
        if source:
            payload["source"] = source
        if error_reason:
            payload["error_reason"] = error_reason
        if packet is not None:
            payload["response_packet"] = sanitize_value(packet)

        self._log_ack_event(payload)

        gateway_id = entry.get("gateway_id") or self._current_node_id()
        base_topic = f"{self.mqtt_handler.mqtt_root}/proxy/ack/{gateway_id}"
        if entry.get("client_ref"):
            retain = bool(getattr(cfg, "mqtt_ack_retain", True))
            self.mqtt_handler.publish_json(f"{base_topic}/{entry['client_ref']}", payload, retain=retain)

    def _log_ack_event(self, payload):
        """Emit visible console output for ACK lifecycle events."""
        status = str(payload.get("status") or "").lower()
        status_label_map = {
            "sent": "TX SENT",
            "ack": "TX ACK",
            "implicit_ack": "TX IMPLICIT_ACK",
            "nak": "TX NAK",
            "timeout": "TX TIMEOUT",
        }
        label = status_label_map.get(status, f"TX {status.upper()}" if status else "TX ACK_EVENT")

        packet_id = payload.get("packet_id")
        destination_id = payload.get("destination_id") or "^all"
        channel_index = payload.get("channel_index")
        mode = str(payload.get("mode") or "").upper() or "-"
        client_ref = payload.get("client_ref") or "-"
        source = payload.get("source") or "-"
        error_reason = payload.get("error_reason")

        suffix = f"mode={mode} to={destination_id} ch={channel_index} packet={packet_id} ref={client_ref} source={source}"
        if error_reason and error_reason != "NONE":
            suffix = f"{suffix} error={error_reason}"
        if payload.get("text"):
            suffix = f"{suffix} text={self._text_preview(payload.get('text'))}"

        if status in {"ack", "implicit_ack", "nak", "timeout"}:
            logger.info("%s %s", label, suffix)
        elif getattr(cfg, "verbose", False):
            logger.info("%s %s", label, suffix)

    def _resolve_pending_ack(self, packet_id, status, packet=None, source=None, error_reason=None):
        """Resolve a tracked ACK/NAK/timeout by packet id."""
        try:
            packet_id = int(packet_id)
        except (TypeError, ValueError):
            return False

        with self.pending_ack_lock:
            entry = self.pending_acks.pop(packet_id, None)

        if not entry:
            return False

        self._publish_ack_event(entry, status, packet=packet, source=source, error_reason=error_reason)
        return True

    def _expire_pending_acks(self, current_time):
        """Expire pending ACK correlations after one minute."""
        expired_entries = []
        with self.pending_ack_lock:
            for packet_id, entry in list(self.pending_acks.items()):
                if current_time - entry.get("created_at", 0) >= self.pending_ack_ttl_seconds:
                    expired_entries.append(self.pending_acks.pop(packet_id))

        for entry in expired_entries:
            self._publish_ack_event(entry, "timeout", source="expiry")

    def onAckNak(self, packet):
        """Classify ACK/NAK responses like the working mass_com tool."""
        decoded = packet.get("decoded") or {}
        request_id = decoded.get("requestId")
        if request_id is None:
            request_id = decoded.get("request_id")
        if request_id is None:
            return

        routing = decoded.get("routing") or {}
        error_reason = routing.get("errorReason") or routing.get("error_reason") or "NONE"
        if error_reason != "NONE":
            status = "nak"
        else:
            packet_from = packet.get("from")
            local_num = getattr(getattr(self.iface, "localNode", None), "nodeNum", None)
            status = "implicit_ack" if local_num is not None and packet_from == local_num else "ack"
        self._resolve_pending_ack(request_id, status, packet=packet, source="response_handler", error_reason=error_reason)

    def on_radio_packet_received(self, packet, interface=None, **kwargs):
        """Publish received packets through the listener pipeline when enabled."""
        try:
            self.listener.handle_receive(packet)
        except Exception as e:
            logger.warning("⚠️ Failed to handle receive packet for MQTT listener: %s", e)

    def _extract_channel_from_topic(self, topic):
        """
        Extract the channel name from a Meshtastic MQTT topic.
        Format: <root>/2/e/<channel_name>/...
        """
        try:
            parts = topic.split('/')
            # Meshtastic topic format: <root>/<version>/<type>/<channel>/<node_id>
            # type is usually 'e' (encrypted) or 'c' (cleartext)
            if len(parts) >= 4 and parts[-3] in ('e', 'c'):
                return parts[-2]
        except Exception:
            pass
        return None

    def _is_channel_downlink_enabled(self, channel_name):
        """Check if a specific channel has downlink enabled."""
        if not self.iface or not self.iface.localNode:
            return True # Conservative default
            
        # Case-insensitive comparison because MQTT topics might vary
        search_name = channel_name.lower()
        
        for i, ch in enumerate(self.iface.localNode.channels):
            if ch.role == 0: # DISABLED
                continue
                
            # Determine channel name
            ch_name = ch.settings.name
            if not ch_name:
                if i == 0:
                    ch_name = "LongFast"
                else:
                    ch_name = f"CH{i}"
            
            if ch_name.lower() == search_name:
                # We found the channel, check its settings
                # Note: Meshtastic protobuf might use default values if field is not present
                enabled = getattr(ch.settings, "downlink_enabled", True)
                return enabled
                
        # Virtual Channel Pass-Through:
        # If the channel is not defined on the physical radio, we still
        # forward the packet to the radio. The proxy has already mutated the packet.channel
        # PSK hash, so the radio has no matching key and CANNOT decrypt or rebroadcast it.
        # However, the raw encrypted packet is sent to all connected TCP clients 
        # (e.g. MeshMonitor), which can natively decrypt it using its own Channel Database 
        # based on the original channelname embedded in the packet.
        # This keeps the key off the node, preventing RF crosstalk while allowing monitoring.
        if getattr(cfg, "mesh_allow_unconfigured_channels", True):
            logger.debug("📡 Channel '%s' not defined on radio, forwarding for MeshMonitor (virtual channel passthrough)", channel_name)
            return True
        else:
            logger.info("🛡️ Channel '%s' not defined on radio, dropping (mesh_allow_unconfigured_channels=false)", channel_name)
            return False

    def _is_channel_uplink_enabled(self, channel_name):
        """Check if a specific channel has uplink enabled."""
        if not self.iface or not self.iface.localNode:
            return True
            
        search_name = channel_name.lower()
        
        for i, ch in enumerate(self.iface.localNode.channels):
            if ch.role == 0: continue
            
            ch_name = ch.settings.name
            if not ch_name:
                ch_name = "LongFast" if i == 0 else f"CH{i}"
                
            if ch_name.lower() == search_name:
                enabled = getattr(ch.settings, "uplink_enabled", True)
                return enabled
                
        # CRITICAL LOOP PREVENTION: If the channel is unknown (like a Virtual Channel
        # e.g., US-LongFast), we MUST NOT publish it back to MQTT!
        # If we return True here, any echo from MeshMonitor creates an infinite publish loop.
        logger.warning("🛡️ Channel '%s' not found in node config (uplink), dropping by default to prevent loops", channel_name)
        return False

    def _perform_health_check(self, current_time):
        """Check system health."""
        health_ok = True
        reasons = []

        # 1. MQTT Check
        if self.mqtt_handler:
            if self.mqtt_handler.health_check_enabled and not self.mqtt_handler.connected:
                health_ok = False
                reasons.append("MQTT disconnected")
            
            # 4. MQTT TX Failures (Ensure we use integers for comparison)
            tx_fails = getattr(self.mqtt_handler, 'tx_failures', 0)
            if isinstance(tx_fails, (int, float)) and tx_fails > 5:
                health_ok = False
                reasons.append(f"Recurring MQTT Publish Failures ({tx_fails})")
        elif self.iface and self.iface.localNode and self.iface.localNode.moduleConfig:
            # We have config but no handler? 
            if self.iface.localNode.moduleConfig.mqtt and getattr(self.iface.localNode.moduleConfig.mqtt, 'enabled', False):
                 health_ok = False
                 reasons.append("MQTT handler uninitialized")

        # 2. Connection Lost Watchdog
        if self.connection_lost_time > 0:
            if current_time - self.connection_lost_time > 60:
                logger.error("🚨 Connection LOST for >60s. Forcing restart...")
                sys.exit(1)

        # 3. Radio Watchdog
        if self.last_radio_activity > 0:
            time_since_radio = current_time - self.last_radio_activity
            if time_since_radio > cfg.health_check_activity_timeout:
                # Silence...
                time_since_probe = current_time - self.last_probe_time
                if time_since_probe > 40:
                    logger.warning(f"📡 Radio silent for {int(time_since_radio)}s. Sending active probe...")
                    try:
                        self.last_probe_time = current_time
                        if self.iface:
                             self.iface.sendPosition()
                    except Exception as e:
                        logger.warning("⚠️ Failed to probe: %s", e)
                elif time_since_probe > 30:
                     health_ok = False
                     reasons.append(f"Radio silent (Probed {int(time_since_probe)}s ago - NO REPLY)")

        return health_ok, reasons

    def _log_status(self, current_time):
        if current_time - self.last_status_log_time > cfg.health_check_status_interval:
            time_since_radio = current_time - self.last_radio_activity if self.last_radio_activity > 0 else -1
            
            mqtt_connected = False
            time_since_mqtt = -1
            if self.mqtt_handler:
                mqtt_connected = getattr(self.mqtt_handler, 'connected', False)
                mqtt_active = getattr(self.mqtt_handler, 'last_activity', 0)
                if isinstance(mqtt_active, (int, float)) and mqtt_active > 0:
                    time_since_mqtt = current_time - mqtt_active
            
            logger.info("📊 === MQTT Proxy Status ===")
            logger.info("  MQTT Connected: %s", mqtt_connected)
            logger.info("  Radio Activity: %s ago", f"{int(time_since_radio)}s" if time_since_radio >= 0 else "never")
            logger.info("  MQTT Activity:  %s ago", f"{int(time_since_mqtt)}s" if time_since_mqtt >= 0 else "never")
            self.last_status_log_time = current_time

    def _update_heartbeat(self, current_time, health_ok, reasons):
        try:
            if health_ok:
                with open("/tmp/healthy", "w") as f:
                    f.write(str(current_time))
            else:
                if os.path.exists("/tmp/healthy"):
                    os.remove("/tmp/healthy")
                # Best-effort: publish an explicit degraded presence before exiting.
                # The MQTT LWT only triggers for unclean disconnects; for a controlled exit,
                # we publish our own terminal/degraded status.
                if self.mqtt_handler:
                    try:
                        self.mqtt_handler.publish_presence(
                            "broken",
                            detail={"reasons": list(reasons or [])},
                        )
                    except Exception:
                        pass
                logger.error("❌ Health check FAILED: %s. Exiting...", ", ".join(reasons))
                sys.exit(1)
        except Exception as e:
            pass

    def _cleanup(self):
        if self.mqtt_handler:
            self.mqtt_handler.stop()
        if self.iface:
            try:
                self.iface.close()
            except: pass
        if getattr(self, 'message_queue', None):
            self.message_queue.stop()

    def handle_sigint(self, sig, frame):
        logger.info("🛑 Received Ctrl+C, shutting down...")
        self.running = False
        self._cleanup()

if __name__ == "__main__":
    # If the user explicitly asks for help on the main script, show full usage
    # We do a quick check here before the main proxy loops start.
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {__version__}")
    parser.add_argument('--version', action='version', version=f"{APP_NAME} {__version__}")
    parser.add_argument("--interface", type=str, help="Interface type: 'tcp' or 'serial' (default: tcp)")
    parser.add_argument("--tcp-host", type=str, help="TCP hostname or IP address (default: localhost)")
    parser.add_argument("--tcp-port", type=int, help="TCP port number (default: 4403)")
    parser.add_argument("--serial-port", type=str, help="Serial device path (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--log-level", type=str, help="Logging level (e.g. INFO, DEBUG)")
    parser.add_argument("--verbose", "--verbode", action="store_true", dest="verbose", help="Enable verbose console output")
    # We don't need to save the args here, config.py already parsed them using parse_known_args
    parser.parse_known_args()

    app = MQTTProxy()
    app.start()
