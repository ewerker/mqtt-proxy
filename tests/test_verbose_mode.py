import os
import sys
import importlib.util

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mqtt-proxy.py")
SPEC = importlib.util.spec_from_file_location("mqtt_proxy_runtime_notice_module", MODULE_PATH)
MQTT_PROXY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MQTT_PROXY_MODULE)


def test_verbose_flag_enables_debug_log_level(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("VERBOSE", raising=False)
    monkeypatch.setattr(sys, "argv", ["mqtt-proxy.py", "--verbose"])

    cfg = Config()

    assert cfg.verbose is True
    assert cfg.log_level_str == "DEBUG"


def test_verbode_alias_is_accepted(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("VERBOSE", raising=False)
    monkeypatch.setattr(sys, "argv", ["mqtt-proxy.py", "--verbode"])

    cfg = Config()

    assert cfg.verbose is True
    assert cfg.log_level_str == "DEBUG"


def test_build_runtime_notice_formats_stage_and_fields():
    message = MQTT_PROXY_MODULE.build_runtime_notice(
        "START",
        app="Meshtastic MQTT Proxy Fork",
        version="beta-0.8",
        log_level="WARNING",
    )

    assert message == "START | app=Meshtastic MQTT Proxy Fork | version=beta-0.8 | log_level=WARNING"
