import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


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
