import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.meshtastic import MQTTProxyMixin, RawSerialInterface, create_interface, resolve_serial_port
from meshtastic import mesh_pb2
from google.protobuf.message import DecodeError

class MockProxy:
    def __init__(self):
        self.mqtt_handler = MagicMock()
        self.last_radio_activity = 0
        self.deduplicator = MagicMock()
        self.myNodeNum = 0x12345678

    def _extract_channel_from_topic(self, topic):
        return "LongFast"

    def _is_channel_uplink_enabled(self, channel_name):
        return True

class ParentInterface:
    def _handleFromRadio(self, fr):
        pass

class MixinTestHelper(MQTTProxyMixin, ParentInterface):
    """Helper class for testing MQTTProxyMixin. Not a test class itself."""
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.last_radio_activity = 0
        if proxy:
            self.myNodeNum = proxy.myNodeNum
        else:
            self.myNodeNum = 0
            
    # No need to override _handleFromRadio here, we want the mixin's version

def test_handle_from_radio_bytes():
    proxy = MockProxy()
    mixin = MixinTestHelper(proxy)
    
    # Create FromRadio bytes with mqttClientProxyMessage
    from_radio = mesh_pb2.FromRadio()
    from_radio.mqttClientProxyMessage.topic = "test"
    from_radio.mqttClientProxyMessage.data = b"abc"
    from_radio_bytes = from_radio.SerializeToString()
    
    # Call directly
    mixin._handleFromRadio(from_radio_bytes)
        
    proxy.mqtt_handler.publish.assert_called_with("test", b"abc", retain=False)
    # The mixin updates proxy.last_radio_activity, not mixin.last_radio_activity
    assert proxy.last_radio_activity > 0

def test_handle_from_radio_malformed_bytes():
    mixin = MixinTestHelper(None)
    # Should not crash
    MQTTProxyMixin._handleFromRadio(mixin, b"invalid garbage")

def test_routing_packets_no_longer_emit_custom_ack_events():
    proxy = MockProxy()
    mixin = MixinTestHelper(proxy)

    with patch('pubsub.pub.sendMessage') as mock_pub:
        MQTTProxyMixin._handleFromRadio(mixin, mesh_pb2.FromRadio())
        mock_pub.assert_not_called()

def test_handle_from_radio_super_crash_handling():
    mixin = MixinTestHelper(None)
    
    # Simulate super() throwing DecodeError
    class Parent:
        def _handleFromRadio(self, fr):
            raise DecodeError("Bad proto")
            
    class Mixed(MQTTProxyMixin, Parent):
        pass
        
    m = Mixed()
    # Should swallow DecodeError
    try:
        m._handleFromRadio(mesh_pb2.FromRadio())
    except:
        pytest.fail("Should not raise exception")
    
    # Simulate other Exception
    class ParentErr:
        def _handleFromRadio(self, fr):
            raise Exception("Real error")
            
    class MixedErr(MQTTProxyMixin, ParentErr):
        pass
        
    merr = MixedErr()
    # Should log error and not crash
    try:
        merr._handleFromRadio(mesh_pb2.FromRadio())
    except:
        pytest.fail("Should not raise exception")

def test_create_interface_serial():
    config = MagicMock()
    config.interface_type = "serial"
    config.serial_port = "COM3"
    
    with patch('handlers.meshtastic.RawSerialInterface') as mock_serial:
        create_interface(config, None)
        mock_serial.assert_called_with("COM3", proxy=None)

def test_create_interface_serial_auto_detects_meshtastic_port():
    config = MagicMock()
    config.interface_type = "serial"
    config.serial_port = "auto"

    port = MagicMock()
    port.device = "/dev/cu.usbmodem101"
    port.name = "cu.usbmodem101"
    port.description = "TRACKER L1"
    port.manufacturer = "Seeed Studio"
    port.product = "TRACKER L1"
    port.hwid = "USB VID:PID=2886:1668"

    with patch('handlers.meshtastic.list_ports.comports', return_value=[port]):
        with patch('handlers.meshtastic.RawSerialInterface') as mock_serial:
            create_interface(config, None)
            mock_serial.assert_called_with("/dev/cu.usbmodem101", proxy=None)

def test_resolve_serial_port_auto_reports_visible_ports():
    port = MagicMock()
    port.device = "/dev/cu.Bluetooth-Incoming-Port"
    port.name = "cu.Bluetooth-Incoming-Port"
    port.description = "n/a"
    port.manufacturer = ""
    port.product = ""
    port.hwid = ""

    with patch('handlers.meshtastic.list_ports.comports', return_value=[port]):
        with pytest.raises(ValueError, match="/dev/cu.Bluetooth-Incoming-Port"):
            resolve_serial_port("auto")

def test_resolve_serial_port_auto_detects_windows_com_by_usb_vid():
    port = MagicMock()
    port.device = "COM7"
    port.name = "COM7"
    port.description = "USB Serial Device"
    port.manufacturer = "Microsoft"
    port.product = "USB Serial Device"
    port.hwid = "USB VID:PID=2886:1668 SER=D342D42CC71FBF89"
    port.vid = 0x2886

    with patch('handlers.meshtastic.list_ports.comports', return_value=[port]):
        assert resolve_serial_port("auto") == "COM7"

def test_resolve_serial_port_auto_detects_only_available_port():
    port = MagicMock()
    port.device = "COM9"
    port.name = "COM9"
    port.description = "USB Serial Device"
    port.manufacturer = ""
    port.product = ""
    port.hwid = ""
    port.vid = None

    with patch('handlers.meshtastic.list_ports.comports', return_value=[port]):
        assert resolve_serial_port("auto") == "COM9"

def test_create_interface_invalid():
    config = MagicMock()
    config.interface_type = "unknown"
    
    with pytest.raises(ValueError, match="Unknown interface type"):
        create_interface(config, None)
