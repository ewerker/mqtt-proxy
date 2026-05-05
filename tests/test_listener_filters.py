import os
import sys
from types import SimpleNamespace
import logging

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


class DummyChannel:
    def __init__(self, name="", role=1):
        self.role = role
        self.settings = SimpleNamespace(name=name)


class DummyInterface:
    def __init__(self):
        self.localNode = SimpleNamespace(
            channels=[
                DummyChannel(""),
                DummyChannel("RichtGroup"),
            ]
        )
        self.nodes = {}


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
        "mqtt_listener_retain": True,
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

    assert len(mqtt_handler.published) == 4
    published_topics = [topic for topic, _, _ in mqtt_handler.published]
    assert "msh/EU_868/proxy/rx/!49b65bc8/group/0" in published_topics


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

    assert len(mqtt_handler.published) == 2
    published_topics = [topic for topic, _, _ in mqtt_handler.published]
    assert "msh/EU_868/proxy/rx/!49b65bc8/scope/group" in published_topics
    assert "msh/EU_868/proxy/rx/!49b65bc8/group/0" in published_topics


def test_listener_publishes_group_channel_topic_when_channel_index_known():
    cfg = make_config(
        mqtt_listener_publish_all=False,
        mqtt_listener_publish_port=False,
        mqtt_listener_publish_scope=True,
    )
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: DummyInterface(), lambda: mqtt_handler)
    packet = make_packet()
    packet["channel"] = 1

    listener.handle_receive(packet)

    published_topics = [topic for topic, _, _ in mqtt_handler.published]
    assert "msh/EU_868/proxy/rx/!49b65bc8/scope/group" in published_topics
    assert "msh/EU_868/proxy/rx/!49b65bc8/group/1" in published_topics


def test_listener_publishes_dm_sender_topic():
    cfg = make_config(
        mqtt_listener_publish_all=False,
        mqtt_listener_publish_port=False,
        mqtt_listener_publish_scope=True,
    )
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: DummyInterface(), lambda: mqtt_handler)

    listener.handle_receive(make_packet(to_id="!49b65bc8"))

    published_topics = [topic for topic, _, _ in mqtt_handler.published]
    assert "msh/EU_868/proxy/rx/!49b65bc8/scope/dm" in published_topics
    assert "msh/EU_868/proxy/rx/!49b65bc8/direct/!13c2288b" in published_topics


def test_listener_sets_retain_flag_by_config():
    cfg = make_config(mqtt_listener_retain=True)
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: None, lambda: mqtt_handler)

    listener.handle_receive(make_packet())

    assert all(retain is True for _, _, retain in mqtt_handler.published)


def test_listener_adds_channel_index_and_name_from_packet_channel():
    cfg = make_config(mqtt_listener_include_raw=False)
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: DummyInterface(), lambda: mqtt_handler)
    packet = make_packet()
    packet["channel"] = 1

    listener.handle_receive(packet)

    payload = mqtt_handler.published[0][1]
    assert payload["channel"] == 1
    assert payload["channel_index"] == 1
    assert payload["channel_name"] == "RichtGroup"


def test_listener_can_resolve_channel_index_from_channel_name():
    cfg = make_config(mqtt_listener_include_raw=False)
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: DummyInterface(), lambda: mqtt_handler)
    packet = make_packet()
    packet["channel"] = "LongFast"

    listener.handle_receive(packet)

    payload = mqtt_handler.published[0][1]
    assert payload["channel"] == "LongFast"
    assert payload["channel_index"] == 0
    assert payload["channel_name"] == "LongFast"


def test_listener_defaults_group_packets_without_channel_to_longfast():
    cfg = make_config(mqtt_listener_include_raw=False)
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: DummyInterface(), lambda: mqtt_handler)

    listener.handle_receive(make_packet())

    payload = mqtt_handler.published[0][1]
    assert payload["channel"] is None
    assert payload["channel_index"] == 0
    assert payload["channel_name"] == "LongFast"


def test_listener_verbose_logs_rx_text(caplog):
    cfg = make_config(verbose=True)
    mqtt_handler = DummyMqttHandler()
    listener = ReceiveMirrorListener(cfg, lambda: DummyInterface(), lambda: mqtt_handler)
    packet = make_packet()
    packet["channel"] = 1

    with caplog.at_level(logging.INFO):
        listener.handle_receive(packet)

    assert "RX GROUP !13c2288b -> ^all ch=1(RichtGroup) port=TEXT_MESSAGE_APP packet=123 text=Hallo Test" in caplog.text
    assert "TX MQTT RXJSON !49b65bc8 -> broker topic=msh/EU_868/proxy/rx/!49b65bc8/all retain=True packet=123 text=Hallo Test" in caplog.text
