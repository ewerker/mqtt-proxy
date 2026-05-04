import importlib.util
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock
import logging


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mqtt-proxy.py")
SPEC = importlib.util.spec_from_file_location("mqtt_proxy_ack_module", MODULE_PATH)
MQTT_PROXY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MQTT_PROXY_MODULE)
MQTTProxy = MQTT_PROXY_MODULE.MQTTProxy


class DummyMqttHandler:
    def __init__(self):
        self.mqtt_root = "msh/EU_868"
        self.published = []

    def publish_json(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))
        return True


def test_parse_plaintext_command_keeps_client_ref():
    proxy = MQTTProxy()
    proxy.mqtt_handler = SimpleNamespace(mqtt_root="msh/EU_868")

    payload = json.dumps(
        {
            "text": "Hallo direkt",
            "channel": 0,
            "want_ack": True,
            "client_ref": "msg-123",
        }
    ).encode("utf-8")

    command = proxy._parse_plaintext_command(
        "msh/EU_868/proxy/send/!unknown/direct/!13c2288b",
        payload,
    )

    assert command["want_ack"] is True
    assert command["client_ref"] == "msg-123"
    assert command["command_topic"] == "msh/EU_868/proxy/send/!unknown/direct/!13c2288b"


def test_want_ack_without_client_ref_skips_ack_path():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
    proxy.iface.localNode.nodeNum = 0x49B65BC8
    proxy.message_queue = MagicMock()
    proxy.iface.sendText.return_value = SimpleNamespace(id=9999)

    payload = json.dumps(
        {
            "text": "Hallo direkt",
            "channel": 0,
            "want_ack": True,
        }
    ).encode("utf-8")

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b",
        payload,
        False,
    )

    proxy.iface.sendText.assert_called_once_with(
        "Hallo direkt",
        destinationId="!13c2288b",
        wantAck=False,
        onResponse=None,
        channelIndex=0,
        hopLimit=None,
    )
    assert proxy.pending_acks == {}
    assert proxy.mqtt_handler.published == []


def test_ack_tracking_publishes_sent_and_ack():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
    proxy.iface.localNode.nodeNum = 0x49B65BC8
    proxy.message_queue = MagicMock()
    proxy.iface.sendText.return_value = SimpleNamespace(id=4321)

    payload = json.dumps(
        {
            "text": "Hallo direkt",
            "channel": 0,
            "want_ack": True,
            "client_ref": "ack-test-1",
        }
    ).encode("utf-8")

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b",
        payload,
        False,
    )

    assert 4321 in proxy.pending_acks
    sent_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "sent"]
    assert len(sent_statuses) == 1
    assert sent_statuses[0][0] == "msh/EU_868/proxy/ack/!49b65bc8/ack-test-1"
    assert sent_statuses[0][2] is True

    proxy.onAckNak(
        {
            "from": 0x13C2288B,
            "decoded": {
                "requestId": 4321,
                "routing": {"errorReason": "NONE"},
            },
        }
    )

    ack_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "ack"]
    assert len(ack_statuses) == 1
    assert ack_statuses[0][0] == "msh/EU_868/proxy/ack/!49b65bc8/ack-test-1"
    assert ack_statuses[0][2] is True
    assert 4321 not in proxy.pending_acks


def test_ack_tracking_logs_visible_console_status(caplog):
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
    proxy.iface.localNode = SimpleNamespace(nodeNum=0x49B65BC8, nodeId="!49b65bc8")
    proxy.iface.sendText.return_value = SimpleNamespace(id=4321)

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b",
        json.dumps(
            {
                "text": "Hallo ACK",
                "channel": 0,
                "want_ack": True,
                "client_ref": "ack-log-1",
            }
        ).encode("utf-8"),
        False,
    )

    with caplog.at_level(logging.INFO):
        proxy.onAckNak(
            {
                "from": 0x13C2288B,
                "decoded": {
                    "requestId": 4321,
                    "routing": {"errorReason": "NONE"},
                },
            }
        )

    assert "TX ACK mode=DIRECT to=!13c2288b ch=0 packet=4321 ref=ack-log-1 source=response_handler text=Hallo ACK" in caplog.text


def test_ack_retain_can_be_disabled():
    old_value = MQTT_PROXY_MODULE.cfg.mqtt_ack_retain
    MQTT_PROXY_MODULE.cfg.mqtt_ack_retain = False
    try:
        proxy = MQTTProxy()
        proxy.mqtt_handler = DummyMqttHandler()
        proxy.iface = MagicMock()
        proxy.iface.localNode.nodeNum = 0x49B65BC8
        proxy.message_queue = MagicMock()
        proxy.iface.sendText.return_value = SimpleNamespace(id=8765)

        payload = json.dumps(
            {
                "text": "Hallo direkt",
                "channel": 0,
                "want_ack": True,
                "client_ref": "ack-retain-off-1",
            }
        ).encode("utf-8")

        proxy.on_mqtt_message_to_radio(
            "msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b",
            payload,
            False,
        )

        assert proxy.mqtt_handler.published[0][2] is False
    finally:
        MQTT_PROXY_MODULE.cfg.mqtt_ack_retain = old_value


def test_ack_tracking_classifies_implicit_ack_like_mass_com():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
    proxy.iface.localNode.nodeNum = 0x49B65BC8
    proxy.message_queue = MagicMock()
    proxy.iface.sendText.return_value = SimpleNamespace(id=6789)

    payload = json.dumps(
        {
            "text": "Hallo direkt",
            "channel": 0,
            "want_ack": True,
            "client_ref": "implicit-test-1",
        }
    ).encode("utf-8")

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b",
        payload,
        False,
    )

    proxy.onAckNak(
        {
            "from": 0x49B65BC8,
            "decoded": {
                "requestId": 6789,
                "routing": {"errorReason": "NONE"},
            },
        }
    )

    implicit_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "implicit_ack"]
    assert len(implicit_statuses) == 1
    assert implicit_statuses[0][0] == "msh/EU_868/proxy/ack/!49b65bc8/implicit-test-1"
    assert 6789 not in proxy.pending_acks


def test_ack_tracking_classifies_nak():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
    proxy.iface.localNode.nodeNum = 0x49B65BC8
    proxy.message_queue = MagicMock()
    proxy.iface.sendText.return_value = SimpleNamespace(id=2468)

    payload = json.dumps(
        {
            "text": "Hallo direkt",
            "channel": 0,
            "want_ack": True,
            "client_ref": "nak-test-1",
        }
    ).encode("utf-8")

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b",
        payload,
        False,
    )

    proxy.onAckNak(
        {
            "from": 0x13C2288B,
            "decoded": {
                "requestId": 2468,
                "routing": {"errorReason": "NO_RESPONSE"},
            },
        }
    )

    nak_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "nak"]
    assert len(nak_statuses) == 1
    assert nak_statuses[0][0] == "msh/EU_868/proxy/ack/!49b65bc8/nak-test-1"
    assert 2468 not in proxy.pending_acks


def test_ack_response_packet_is_json_safe():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
    proxy.iface.localNode.nodeNum = 0x49B65BC8
    proxy.message_queue = MagicMock()
    proxy.iface.sendText.return_value = SimpleNamespace(id=1357)

    payload = json.dumps(
        {
            "text": "Hallo direkt",
            "channel": 0,
            "want_ack": True,
            "client_ref": "bytes-test-1",
        }
    ).encode("utf-8")

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/!49b65bc8/direct/!13c2288b",
        payload,
        False,
    )

    proxy.onAckNak(
        {
            "from": 0x13C2288B,
            "decoded": {
                "requestId": 1357,
                "routing": {"errorReason": "NONE"},
                "payload": b"\x01\x02\x03",
            },
        }
    )

    ack_payload = [item[1] for item in proxy.mqtt_handler.published if item[1]["status"] == "ack"][0]
    assert ack_payload["response_packet"]["decoded"]["payload"] == "010203"


def test_ack_tracking_times_out_after_one_minute():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
    proxy.iface.localNode.nodeNum = 0x49B65BC8
    proxy.message_queue = MagicMock()
    proxy.iface.sendText.return_value = SimpleNamespace(id=5555)

    payload = json.dumps(
        {
            "text": "Hallo Gruppe",
            "channel": 0,
            "want_ack": True,
            "client_ref": "ack-timeout-1",
        }
    ).encode("utf-8")

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/!49b65bc8/group/0",
        payload,
        False,
    )

    proxy._expire_pending_acks(proxy.pending_acks[5555]["created_at"] + 61)

    timeout_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "timeout"]
    assert len(timeout_statuses) == 1
    assert timeout_statuses[0][0] == "msh/EU_868/proxy/ack/!49b65bc8/ack-timeout-1"
    assert 5555 not in proxy.pending_acks
