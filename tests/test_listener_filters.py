import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.listener import ReceiveMirrorListener


class DummyMqttHandler:
    def __init__(self):
        self.mqtt_root = "msh/EU_868"
        self.prefixed_node_id = "!49b65bc8"
        self.published = []

    def publish_json(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))
        return True


def make_packet(portnum="TEXT_MESSAGE_APP", to_id="^all"):
    return {
        "fromId": "!13c2288b",
        "toId": to_id,
        "id": 123,
        "rxSnr": 7.5,
        "rxRssi": -91,
        "decoded": {
            "portnum": portnum,
            "text": "Hallo Test",
        },
    }


def make_config(**overrides):
    base = {
        "mqtt_listener_enabled": True,
        "mqtt_listener_ports": set(),
        "mqtt_listener_exclude_ports": set(),
        "mqtt_listener_dm_only": False,
        "mqtt_listener_group_only": False,
        "mqtt_listener_text_only": False,
        "mqtt_listener_include_raw": True,
        "mqtt_listener_publish_all": True,
        "mqtt_listener_publish_port": True,
        "mqtt_listener_publish_scope": True,
        "verbose": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_listener_excludes_blocklisted_port():
    cfg = make_config(mqtt_listener_exclude_ports={"ROUTING_APP"})
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: None, lambda: mqtt_handler)

    listener.handle_receive(make_packet(portnum="ROUTING_APP"))

    assert mqtt_handler.published == []


def test_listener_allows_allowlisted_port():
    cfg = make_config(mqtt_listener_ports={"POSITION_APP"})
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: None, lambda: mqtt_handler)

    listener.handle_receive(make_packet(portnum="POSITION_APP"))

    assert len(mqtt_handler.published) == 3


def test_listener_omits_raw_packet_when_disabled():
    cfg = make_config(mqtt_listener_include_raw=False)
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: None, lambda: mqtt_handler)

    listener.handle_receive(make_packet())

    payload = mqtt_handler.published[0][1]
    assert "packet" not in payload
    assert payload["portnum"] == "TEXT_MESSAGE_APP"
    assert payload["from_id"] == "!13c2288b"


def test_listener_publish_switches_can_disable_duplicates():
    cfg = make_config(
        mqtt_listener_publish_all=False,
        mqtt_listener_publish_port=False,
        mqtt_listener_publish_scope=True,
    )
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: None, lambda: mqtt_handler)

    listener.handle_receive(make_packet())

    assert len(mqtt_handler.published) == 1
    assert mqtt_handler.published[0][0] == "msh/EU_868/proxy/rx/!49b65bc8/scope/group"
