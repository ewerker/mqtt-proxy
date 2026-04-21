import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.node_list import NodeListPublisher


class DummyMqttHandler:
    def __init__(self):
        self.mqtt_root = "msh/EU_868"
        self.prefixed_node_id = "!49b65bc8"
        self.connected = True
        self.published = []

    def publish_json(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))
        return True


def test_publish_snapshot_contains_all_and_index_topics():
    cfg = SimpleNamespace(
        mqtt_node_list_enabled=True,
        mqtt_node_list_interval_seconds=3600,
        mqtt_node_list_retain=True,
    )
    iface = SimpleNamespace(
        nodes={
            "!49b65bc8": {
                "num": 0x49B65BC8,
                "user": {"id": "!49b65bc8", "longName": "Gateway", "shortName": "GW"},
                "position": {"latitude": 51.1, "longitude": 12.4},
                "lastHeard": 200,
            },
            "!13c2288b": {
                "num": 0x13C2288B,
                "user": {"id": "!13c2288b", "longName": "Remote Node", "shortName": "RN"},
                "position": {"latitude": 51.2, "longitude": 12.5},
                "lastHeard": 100,
                "deviceMetrics": {"batteryLevel": 87},
            },
        }
    )
    mqtt_handler = DummyMqttHandler()
    publisher = NodeListPublisher(cfg, lambda: iface, lambda: mqtt_handler)

    assert publisher.publish_if_due(force=True, current_time=1234) is True
    assert len(mqtt_handler.published) == 2

    topics = [item[0] for item in mqtt_handler.published]
    assert "msh/EU_868/proxy/nodes/!49b65bc8/all" in topics
    assert "msh/EU_868/proxy/nodes/!49b65bc8/index" in topics

    all_payload = next(payload for topic, payload, _ in mqtt_handler.published if topic.endswith("/all"))
    index_payload = next(payload for topic, payload, _ in mqtt_handler.published if topic.endswith("/index"))

    assert all_payload["node_count"] == 2
    assert all_payload["gateway_id"] == "!49b65bc8"
    assert all_payload["nodes"][0]["node_id"] == "!49b65bc8"
    assert all_payload["nodes"][1]["battery_level"] == 87

    assert index_payload["nodes"][0]["label"] == "Gateway"
    assert index_payload["nodes"][1]["node_id"] == "!13c2288b"


def test_publish_if_due_respects_interval():
    cfg = SimpleNamespace(
        mqtt_node_list_enabled=True,
        mqtt_node_list_interval_seconds=3600,
        mqtt_node_list_retain=True,
    )
    iface = SimpleNamespace(nodes={})
    mqtt_handler = DummyMqttHandler()
    publisher = NodeListPublisher(cfg, lambda: iface, lambda: mqtt_handler)

    assert publisher.publish_if_due(force=True, current_time=1000) is True
    assert publisher.publish_if_due(current_time=1200) is False
    assert publisher.publish_if_due(current_time=5000) is True


def test_publish_if_due_waits_for_mqtt_connection():
    cfg = SimpleNamespace(
        mqtt_node_list_enabled=True,
        mqtt_node_list_interval_seconds=3600,
        mqtt_node_list_retain=True,
    )
    iface = SimpleNamespace(nodes={})
    mqtt_handler = DummyMqttHandler()
    mqtt_handler.connected = False
    publisher = NodeListPublisher(cfg, lambda: iface, lambda: mqtt_handler)

    assert publisher.publish_if_due(force=True, current_time=1000) is False
    assert mqtt_handler.published == []
