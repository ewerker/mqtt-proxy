import importlib.util
import os
import sys
import tempfile
import time


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mqtt-proxy.py")
SPEC = importlib.util.spec_from_file_location("mqtt_proxy_hot_reload_module", MODULE_PATH)
MQTT_PROXY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MQTT_PROXY_MODULE)
MQTTProxy = MQTT_PROXY_MODULE.MQTTProxy
ENV_RELOAD_EXIT_CODE = MQTT_PROXY_MODULE.ENV_RELOAD_EXIT_CODE


def test_env_hot_reload_ignores_unchanged_file():
    proxy = MQTTProxy()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        env_path = tmp.name

    try:
        old_enabled = MQTT_PROXY_MODULE.cfg.env_hot_reload_enabled
        old_interval = MQTT_PROXY_MODULE.cfg.env_hot_reload_interval_seconds
        mtime = os.path.getmtime(env_path)
        proxy.env_file_path = env_path
        proxy.env_hot_reload_last_mtime = mtime
        proxy.env_hot_reload_last_check = 0
        MQTT_PROXY_MODULE.cfg.env_hot_reload_enabled = True
        MQTT_PROXY_MODULE.cfg.env_hot_reload_interval_seconds = 0

        proxy._check_env_hot_reload(time.time())
    finally:
        MQTT_PROXY_MODULE.cfg.env_hot_reload_enabled = old_enabled
        MQTT_PROXY_MODULE.cfg.env_hot_reload_interval_seconds = old_interval
        os.unlink(env_path)


def test_env_hot_reload_restarts_on_changed_file():
    proxy = MQTTProxy()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        env_path = tmp.name

    try:
        old_enabled = MQTT_PROXY_MODULE.cfg.env_hot_reload_enabled
        old_interval = MQTT_PROXY_MODULE.cfg.env_hot_reload_interval_seconds
        proxy.env_file_path = env_path
        proxy.env_hot_reload_last_mtime = os.path.getmtime(env_path)
        proxy.env_hot_reload_last_check = 0
        MQTT_PROXY_MODULE.cfg.env_hot_reload_enabled = True
        MQTT_PROXY_MODULE.cfg.env_hot_reload_interval_seconds = 0

        time.sleep(0.02)
        with open(env_path, "a", encoding="utf-8") as handle:
            handle.write("LOG_LEVEL=DEBUG\n")

        try:
            proxy._check_env_hot_reload(time.time())
            assert False, "Expected SystemExit for changed .env"
        except SystemExit as exc:
            assert exc.code == ENV_RELOAD_EXIT_CODE
    finally:
        MQTT_PROXY_MODULE.cfg.env_hot_reload_enabled = old_enabled
        MQTT_PROXY_MODULE.cfg.env_hot_reload_interval_seconds = old_interval
        os.unlink(env_path)
