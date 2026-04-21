"""Periodic MQTT publisher for Meshtastic node list snapshots."""
# Copyright (c) 2026 LN4CY
# This software is licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from handlers.listener import sanitize_value

logger = logging.getLogger("mqtt-proxy.handlers.node_list")


class NodeListPublisher:
    """Publish the current Meshtastic node database to retained MQTT JSON topics."""

    def __init__(self, config, get_interface, get_mqtt_handler):
        self.config = config
        self.get_interface = get_interface
        self.get_mqtt_handler = get_mqtt_handler
        self.last_publish_time = 0.0

    def publish_if_due(self, force: bool = False, current_time: float | None = None) -> bool:
        """Publish the node list if enabled and the configured interval has elapsed."""
        if not getattr(self.config, "mqtt_node_list_enabled", True):
            return False

        mqtt_handler = self.get_mqtt_handler()
        iface = self.get_interface()
        if not mqtt_handler or not iface:
            return False

        now = current_time if current_time is not None else time.time()
        interval = max(1, int(getattr(self.config, "mqtt_node_list_interval_seconds", 3600)))
        if not force and self.last_publish_time and now - self.last_publish_time < interval:
            return False

        try:
            self._publish_snapshot(mqtt_handler, iface, now)
            self.last_publish_time = now
            return True
        except Exception as e:
            logger.warning("Failed to publish node list snapshot: %s", e)
            return False

    def _publish_snapshot(self, mqtt_handler, iface, now: float) -> None:
        """Publish full and compact node list snapshots."""
        gateway_id = getattr(mqtt_handler, "prefixed_node_id", "!unknown")
        root_topic = getattr(mqtt_handler, "mqtt_root", "msh")
        nodes = self._collect_nodes(iface, gateway_id)

        snapshot = {
            "generated_at": int(now),
            "gateway_id": gateway_id,
            "node_count": len(nodes),
            "interval_seconds": int(getattr(self.config, "mqtt_node_list_interval_seconds", 3600)),
            "nodes": nodes,
        }

        summary = {
            "generated_at": int(now),
            "gateway_id": gateway_id,
            "node_count": len(nodes),
            "nodes": [self._compact_node(node) for node in nodes],
        }

        base_topic = f"{root_topic}/proxy/nodes/{gateway_id}"
        retain = bool(getattr(self.config, "mqtt_node_list_retain", True))

        logger.info("Publishing node list snapshot with %s nodes", len(nodes))
        mqtt_handler.publish_json(f"{base_topic}/all", snapshot, retain=retain)
        mqtt_handler.publish_json(f"{base_topic}/index", summary, retain=retain)

    def _collect_nodes(self, iface, gateway_id: str) -> List[Dict[str, Any]]:
        """Collect and normalize nodes from the Meshtastic interface database."""
        nodes_db = getattr(iface, "nodes", {}) or {}
        records = []

        for raw_node_id, raw_node in nodes_db.items():
            node = sanitize_value(raw_node)
            node_id = self._normalize_node_id(raw_node_id, node)
            user = node.get("user", {}) if isinstance(node, dict) else {}
            position = node.get("position", {}) if isinstance(node, dict) else {}

            record = {
                "node_id": node_id,
                "node_num": node.get("num"),
                "label": user.get("longName") or user.get("shortName") or node_id,
                "long_name": user.get("longName"),
                "short_name": user.get("shortName"),
                "hw_model": user.get("hwModel"),
                "is_gateway": node_id == gateway_id,
                "last_heard": node.get("lastHeard"),
                "snr": node.get("snr"),
                "channel": node.get("channel"),
                "battery_level": self._extract_battery_level(node),
                "latitude": position.get("latitude"),
                "longitude": position.get("longitude"),
                "altitude": position.get("altitude"),
                "raw": node,
            }
            records.append(record)

        records.sort(
            key=lambda item: (
                item["last_heard"] is None,
                -(item["last_heard"] or 0),
                item["label"] or "",
            )
        )
        return records

    def _compact_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Compact representation for selector UIs."""
        return {
            "node_id": node["node_id"],
            "node_num": node["node_num"],
            "label": node["label"],
            "long_name": node["long_name"],
            "short_name": node["short_name"],
            "last_heard": node["last_heard"],
            "battery_level": node["battery_level"],
            "latitude": node["latitude"],
            "longitude": node["longitude"],
        }

    def _normalize_node_id(self, raw_node_id: Any, node: Dict[str, Any]) -> str:
        """Normalize node ids to the Meshtastic !xxxxxxxx form."""
        if isinstance(raw_node_id, str):
            return raw_node_id if raw_node_id.startswith("!") else f"!{raw_node_id}"

        user = node.get("user", {}) if isinstance(node, dict) else {}
        user_id = user.get("id")
        if isinstance(user_id, str) and user_id:
            return user_id if user_id.startswith("!") else f"!{user_id}"

        node_num = node.get("num") if isinstance(node, dict) else None
        if isinstance(node_num, int):
            return f"!{node_num:08x}"

        return "!unknown"

    def _extract_battery_level(self, node: Dict[str, Any]) -> Any:
        """Extract the most useful battery level field if present."""
        device_metrics = (
            node.get("deviceMetrics")
            or node.get("device_metrics")
            or node.get("telemetry", {}).get("deviceMetrics", {})
            or node.get("telemetry", {}).get("device_metrics", {})
        )

        if isinstance(device_metrics, dict):
            if "batteryLevel" in device_metrics:
                return device_metrics.get("batteryLevel")
            if "battery_level" in device_metrics:
                return device_metrics.get("battery_level")

        return None
