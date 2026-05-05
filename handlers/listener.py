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


def text_preview(text: Optional[str], limit: int = 120) -> str:
    """Return a compact one-line preview for console logging."""
    value = str(text or "").replace("\r", " ").replace("\n", " ").strip()
    if len(value) > limit:
        return f"{value[:limit - 1]}…"
    return value


def channel_name_from_index(interface, channel_index: Optional[int]) -> Optional[str]:
    """Resolve a human-readable channel name from the local node config."""
    if channel_index is None or not interface:
        return None

    local_node = getattr(interface, "localNode", None)
    channels = getattr(local_node, "channels", None)
    if not channels:
        return None

    if channel_index < 0 or channel_index >= len(channels):
        return None

    channel = channels[channel_index]
    name = getattr(getattr(channel, "settings", None), "name", "") or ""
    if name:
        return str(name)

    if channel_index == 0:
        return "LongFast"
    return f"CH{channel_index}"


def channel_index_from_name(interface, channel_name: Optional[str]) -> Optional[int]:
    """Resolve a channel index from a human-readable channel name."""
    if not channel_name or not interface:
        return None

    local_node = getattr(interface, "localNode", None)
    channels = getattr(local_node, "channels", None)
    if not channels:
        return None

    search_name = str(channel_name).strip().lower()
    if not search_name:
        return None

    for index, channel in enumerate(channels):
        role = getattr(channel, "role", None)
        if role == 0:
            continue

        resolved_name = getattr(getattr(channel, "settings", None), "name", "") or ""
        if not resolved_name:
            resolved_name = "LongFast" if index == 0 else f"CH{index}"

        if str(resolved_name).strip().lower() == search_name:
            return index

    return None


def normalize_channel_index(value: Any) -> Optional[int]:
    """Normalize channel index values from packet dicts into an int."""
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float) and value.is_integer():
        return int(value)

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)

    return None


def resolve_channel_metadata(interface, packet: Dict[str, Any], packet_copy: Dict[str, Any]) -> tuple[Optional[int], Optional[str], Any]:
    """Resolve best-effort channel metadata for mirrored RX packets."""
    decoded = packet_copy.get("decoded") or {}
    raw_packet = packet.get("raw") if isinstance(packet, dict) else None
    raw_decoded = raw_packet.get("decoded") if isinstance(raw_packet, dict) else None
    to_id = str(packet_copy.get("toId") or packet_copy.get("to") or "")

    candidate_values = [
        packet_copy.get("channelIndex"),
        packet_copy.get("channel_index"),
        packet_copy.get("channel"),
        decoded.get("channelIndex"),
        decoded.get("channel_index"),
        decoded.get("channel"),
    ]

    if isinstance(raw_packet, dict):
        candidate_values.extend(
            [
                raw_packet.get("channelIndex"),
                raw_packet.get("channel_index"),
                raw_packet.get("channel"),
            ]
        )
    if isinstance(raw_decoded, dict):
        candidate_values.extend(
            [
                raw_decoded.get("channelIndex"),
                raw_decoded.get("channel_index"),
                raw_decoded.get("channel"),
            ]
        )

    channel_index = None
    channel_name = None
    legacy_channel_value = packet_copy.get("channel")

    for candidate in candidate_values:
        normalized_index = normalize_channel_index(candidate)
        if normalized_index is not None:
            channel_index = normalized_index
            break

        if channel_name is None and isinstance(candidate, str) and candidate.strip():
            channel_name = candidate.strip()

    if channel_name and channel_index is None:
        channel_index = channel_index_from_name(interface, channel_name)

    if channel_index is not None:
        resolved_name = channel_name_from_index(interface, channel_index)
        if resolved_name:
            channel_name = resolved_name

    # Meshtastic often omits the channel field for default/public group traffic.
    # For group packets without any channel metadata, treat them as channel 0.
    if channel_index is None and to_id == "^all":
        channel_index = 0
        resolved_name = channel_name_from_index(interface, channel_index)
        if resolved_name:
            channel_name = resolved_name

    return channel_index, channel_name, legacy_channel_value


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
        retain = bool(getattr(self.config, "mqtt_listener_retain", True))
        scope = record["scope"]

        scope_label = "DM" if scope == "dm" else "GROUP"
        if record["channel_index"] is not None and record["channel_name"]:
            channel_label = f"{record['channel_index']}({record['channel_name']})"
        elif record["channel_index"] is not None:
            channel_label = str(record["channel_index"])
        elif record["channel_name"]:
            channel_label = record["channel_name"]
        elif record["channel"] is not None:
            channel_label = str(record["channel"])
        else:
            channel_label = "-"
        logger.info(
            "RX %s %s -> %s ch=%s port=%s packet=%s text=%s",
            scope_label,
            record["from_id"],
            record["to_id"] or "^all",
            channel_label,
            record["portnum"],
            record["packet_id"] if record["packet_id"] is not None else "-",
            text_preview(record["text"]),
        )

        if getattr(self.config, "mqtt_listener_publish_all", True):
            self._publish_record(mqtt_handler, f"{base_topic}/all", record, retain)

        if getattr(self.config, "mqtt_listener_publish_port", True):
            self._publish_record(mqtt_handler, f"{base_topic}/port/{record['portnum']}", record, retain)

        if getattr(self.config, "mqtt_listener_publish_scope", True):
            self._publish_record(mqtt_handler, f"{base_topic}/scope/{scope}", record, retain)

        if scope == "group" and record.get("channel_index") is not None:
            self._publish_record(
                mqtt_handler,
                f"{base_topic}/group/{record['channel_index']}",
                record,
                retain,
            )
        elif scope == "dm" and record.get("from_id"):
            self._publish_record(
                mqtt_handler,
                f"{base_topic}/direct/{record['from_id']}",
                record,
                retain,
            )

    def _publish_record(self, mqtt_handler, topic: str, record: Dict[str, Any], retain: bool) -> None:
        """Publish a mirrored RX record and optionally log the outgoing MQTT dataset."""
        logger.info(
            "TX MQTT RXJSON %s -> broker topic=%s retain=%s packet=%s text=%s",
            record.get("gateway_id") or "!unknown",
            topic,
            retain,
            record.get("packet_id") if record.get("packet_id") is not None else "-",
            text_preview(record.get("text")),
        )
        mqtt_handler.publish_json(topic, record, retain=retain)

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
        channel_index, channel_name, legacy_channel_value = resolve_channel_metadata(interface, packet, packet_copy)
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
            "channel": legacy_channel_value,
            "channel_index": channel_index,
            "channel_name": channel_name,
        }
        if getattr(self.config, "mqtt_listener_include_raw", True):
            record["packet"] = packet_copy
        return record
