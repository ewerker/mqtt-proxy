import importlib.util
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from handlers.mqtt import MQTTHandler


MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mqtt-proxy.py")
SPEC = importlib.util.spec_from_file_location("mqtt_proxy_module", MODULE_PATH)
MQTT_PROXY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MQTT_PROXY_MODULE)
MQTTProxy = MQTT_PROXY_MODULE.MQTTProxy


@patch("paho.mqtt.client.Client")
def test_mqtt_connect_subscribes_plaintext_commands(mock_client_cls):
    config = Config()
    handler = MQTTHandler(config, "1234abcd")

    node_cfg = MagicMock()
    node_cfg.enabled = True
    node_cfg.address = "1.2.3.4"
    node_cfg.port = 1883
    node_cfg.root = "msh"

    handler.configure(node_cfg)
    client = handler.client

    handler._on_connect(client, None, None, 0)

    client.subscribe.assert_any_call("msh/2/e/#")
    client.subscribe.assert_any_call("msh/proxy/send/#")


def test_parse_plaintext_group_command():
    proxy = MQTTProxy()
    proxy.mqtt_handler = SimpleNamespace(mqtt_root="msh/EU_868")

    command = proxy._parse_plaintext_command(
        "msh/EU_868/proxy/send/group/0",
        b"Hallo Gruppe 0",
    )

    assert command["mode"] == "group"
    assert command["channel_index"] == 0
    assert command["text"] == "Hallo Gruppe 0"
    assert command["want_ack"] is False


def test_parse_plaintext_direct_command_json():
    proxy = MQTTProxy()
    proxy.mqtt_handler = SimpleNamespace(mqtt_root="msh/EU_868")

    payload = json.dumps(
        {"text": "Hallo direkt", "channel": 2, "want_ack": True, "hop_limit": 4}
    ).encode("utf-8")
    command = proxy._parse_plaintext_command(
        "msh/EU_868/proxy/send/direct/!13c2288b",
        payload,
    )

    assert command["mode"] == "direct"
    assert command["destination_id"] == "!13c2288b"
    assert command["text"] == "Hallo direkt"
    assert command["channel_index"] == 2
    assert command["want_ack"] is True
    assert command["hop_limit"] == 4


def test_group_plaintext_command_sends_without_queueing():
    proxy = MQTTProxy()
    proxy.mqtt_handler = SimpleNamespace(mqtt_root="msh/EU_868")
    proxy.iface = MagicMock()
    proxy.message_queue = MagicMock()

    proxy.on_mqtt_message_to_radio(
        "msh/EU_868/proxy/send/group/1",
        b"Test Kanal 1",
        False,
    )

    proxy.iface.sendText.assert_called_once_with(
        "Test Kanal 1",
        destinationId="^all",
        wantAck=False,
        channelIndex=1,
        hopLimit=None,
    )
    proxy.message_queue.put.assert_not_called()
