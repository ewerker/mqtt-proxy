"""Receive listener that mirrors Meshtastic packets to dedicated MQTT JSON topics."""
# Copyright (c) 2026 LN4CY
# This software is licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message


logger = logging.getLogger("mqtt-proxy.handlers.listener")


def extract_text(packet: Dict[str, Any]) -> Optional[str]:
    """Extract a text payload from a Meshtastic receive packet dict."""
    decoded = packet.get("decoded") or {}
    text = decoded.get("text")
    if text:
        return str(text)

    data = decoded.get("data")
    if isinstance(data, dict):
        data_text = data.get("text")
        if data_text:
            return str(data_text)

    return None


def is_direct_message(packet: Dict[str, Any]) -> bool:
    """Return True when the packet targets the local node instead of broadcast."""
    to_id = str(packet.get("toId") or "")
    return bool(to_id) and to_id != "^all"


def is_text_message(packet: Dict[str, Any]) -> bool:
    """Return True for text-like message ports."""
    decoded = packet.get("decoded") or {}
    portnum = str(decoded.get("portnum") or "UNKNOWN_APP").upper()
    return portnum in {"TEXT_MESSAGE_APP", "TEXT_MESSAGE_COMPRESSED_APP"} or bool(extract_text(packet))


def sender_label(interface, sender_id: str) -> str:
    """Resolve a sender label using the current node database."""
    if not interface:
        return sender_id

    node = getattr(interface, "nodes", {}).get(sender_id, {})
    user = node.get("user", {})
    long_name = user.get("longName")
    short_name = user.get("shortName")
    return long_name or short_name or sender_id


def sanitize_value(value: Any) -> Any:
    """Convert Meshtastic/pubsub payloads into JSON-safe Python data."""
    if isinstance(value, Message):
        return sanitize_value(MessageToDict(value, preserving_proto_field_name=True))

    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [sanitize_value(item) for item in value]

    if isinstance(value, (bytes, bytearray)):
        return value.hex()

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


class ReceiveMirrorListener:
    """Mirror Meshtastic receive events to MQTT topics using stable library events."""

    def __init__(self, config, get_interface, get_mqtt_handler):
        self.config = config
        self.get_interface = get_interface
        self.get_mqtt_handler = get_mqtt_handler

    def handle_receive(self, packet: Dict[str, Any]) -> None:
        """Filter and publish a receive packet to MQTT."""
        if not getattr(self.config, "mqtt_listener_enabled", False):
            return

        mqtt_handler = self.get_mqtt_handler()
        if not mqtt_handler:
            return

        if not self._matches_filters(packet):
            return

        record = self._build_record(packet)
        base_topic = f"{mqtt_handler.mqtt_root}/proxy/rx/{mqtt_handler.prefixed_node_id}"
        record["gateway_id"] = mqtt_handler.prefixed_node_id

        if getattr(self.config, "verbose", False):
            logger.info(
                "RX %s %s -> %s port=%s text=%s",
                record["scope"].upper(),
                record["from_id"],
                record["to_id"] or "^all",
                record["portnum"],
                (record["text"] or "")[:120],
            )

        mqtt_handler.publish_json(f"{base_topic}/all", record)
        mqtt_handler.publish_json(f"{base_topic}/port/{record['portnum']}", record)

        scope = record["scope"]
        mqtt_handler.publish_json(f"{base_topic}/scope/{scope}", record)

    def _matches_filters(self, packet: Dict[str, Any]) -> bool:
        decoded = packet.get("decoded") or {}
        portnum = str(decoded.get("portnum") or "UNKNOWN_APP").upper()

        allowed_ports = getattr(self.config, "mqtt_listener_ports", set())
        if allowed_ports and portnum not in allowed_ports:
            return False

        excluded_ports = getattr(self.config, "mqtt_listener_exclude_ports", set())
        if excluded_ports and portnum in excluded_ports:
            return False

        if getattr(self.config, "mqtt_listener_dm_only", False) and not is_direct_message(packet):
            return False

        if getattr(self.config, "mqtt_listener_group_only", False) and is_direct_message(packet):
            return False

        if getattr(self.config, "mqtt_listener_text_only", False) and not is_text_message(packet):
            return False

        return True

    def _build_record(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        interface = self.get_interface()
        packet_copy = sanitize_value(dict(packet))
        packet_copy.pop("raw", None)
        decoded = dict(packet_copy.get("decoded") or {})
        packet_copy["decoded"] = decoded

        from_id = packet_copy.get("fromId")
        if not from_id:
            sender_val = packet_copy.get("from", 0)
            from_id = f"!{int(sender_val):08x}" if sender_val else "!unknown"

        to_id = str(packet_copy.get("toId") or packet_copy.get("to") or "")
        text = extract_text(packet_copy)
        scope = "dm" if is_direct_message(packet_copy) else "group"
        portnum = str(decoded.get("portnum") or "UNKNOWN_APP").upper()

        record = {
            "mirrored_at": int(time.time()),
            "from_id": from_id,
            "from_label": sender_label(interface, from_id),
            "to_id": to_id,
            "scope": scope,
            "portnum": portnum,
            "text": text,
            "packet_id": packet_copy.get("id"),
            "rx_snr": packet_copy.get("rxSnr"),
            "rx_rssi": packet_copy.get("rxRssi"),
            "hop_limit": packet_copy.get("hopLimit"),
            "channel": packet_copy.get("channel"),
        }
        if getattr(self.config, "mqtt_listener_include_raw", True):
            record["packet"] = packet_copy
        return record
