import importlib.util
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock


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
        "msh/EU_868/proxy/send/direct/!13c2288b",
        payload,
    )

    assert command["want_ack"] is True
    assert command["client_ref"] == "msg-123"
    assert command["command_topic"] == "msh/EU_868/proxy/send/direct/!13c2288b"


def test_ack_tracking_publishes_sent_and_ack():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
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
        "msh/EU_868/proxy/send/direct/!13c2288b",
        payload,
        False,
    )

    assert 4321 in proxy.pending_acks
    sent_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "sent"]
    assert len(sent_statuses) == 2

    proxy.on_meshtastic_ack(4321)

    ack_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "ack"]
    assert len(ack_statuses) == 2
    assert 4321 not in proxy.pending_acks


def test_ack_tracking_times_out_after_one_minute():
    proxy = MQTTProxy()
    proxy.mqtt_handler = DummyMqttHandler()
    proxy.iface = MagicMock()
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
        "msh/EU_868/proxy/send/group/0",
        payload,
        False,
    )

    proxy._expire_pending_acks(proxy.pending_acks[5555]["created_at"] + 61)

    timeout_statuses = [item for item in proxy.mqtt_handler.published if item[1]["status"] == "timeout"]
    assert len(timeout_statuses) == 2
    assert 5555 not in proxy.pending_acks
