"""Meshtastic Interface Handler for MQTT Proxy."""
# Copyright (c) 2026 LN4CY
# This software is licensed under the MIT License. See LICENSE file for details.

import time
import logging
import re
from meshtastic import mesh_pb2
from meshtastic.tcp_interface import TCPInterface
from meshtastic.serial_interface import SerialInterface
from serial.tools import list_ports
from google.protobuf.message import DecodeError

logger = logging.getLogger("mqtt-proxy.handlers.meshtastic")

AUTO_SERIAL_VALUES = {"", "auto", "detect", "autodetect"}
MESHTASTIC_USB_KEYWORDS = (
    "meshtastic",
    "tracker",
    "seeed",
    "sensecap",
    "tinyusb",
    "nrf",
    "rp2040",
    "esp32",
)
EXCLUDED_SERIAL_KEYWORDS = (
    "bluetooth",
    "debug-console",
    "wlan-debug",
)
PREFERRED_USB_VIDS = {
    0x2886,  # Seeed Studio
    0x239A,  # Adafruit / TinyUSB boards
    0x2E8A,  # Raspberry Pi RP2040
    0x10C4,  # Silicon Labs CP210x
    0x1A86,  # WCH CH34x/CH910x
}
PREFERRED_SERIAL_PREFIXES = (
    "/dev/cu.usbmodem",
    "/dev/cu.usbserial",
    "/dev/cu.wchusbserial",
    "/dev/cu.SLAB_USBtoUART",
    "COM",
)


class MQTTProxyMixin:
    """
    Mixin class that provides common _handleFromRadio() logic for all interface types.
    This intercepts mqttClientProxyMessage from the node and publishes to MQTT.
    It also suppresses DecodeErrors from the upstream stream handler.
    """

    def _handleFromRadio(self, fromRadio):
        """Intercept mqttClientProxyMessage from the node and publish it to MQTT."""
        decoded = None
        try:
            if hasattr(self, "proxy") and self.proxy:
                self.proxy.last_radio_activity = time.time()

            if isinstance(fromRadio, bytes):
                try:
                    decoded = mesh_pb2.FromRadio()
                    decoded.ParseFromString(fromRadio)
                except Exception as e:
                    logger.debug("Failed to parse FromRadio bytes: %s", e)
            else:
                decoded = fromRadio

            if decoded and decoded.HasField("mqttClientProxyMessage"):
                mqtt_msg = decoded.mqttClientProxyMessage
                logger.info(
                    "Node->MQTT: Topic=%s Size=%d bytes Retained=%s",
                    mqtt_msg.topic,
                    len(mqtt_msg.data),
                    mqtt_msg.retained,
                )

                if hasattr(self, "proxy") and self.proxy and self.proxy.mqtt_handler:
                    try:
                        sender_id = None
                        packet_id = None

                        if decoded.packet:
                            try:
                                sender_val = getattr(decoded.packet, "from", 0)
                                sender_id = f"{sender_val:08x}"
                            except Exception:
                                pass

                            if decoded.packet.id:
                                packet_id = decoded.packet.id

                        if (
                            sender_id
                            and packet_id
                            and hasattr(self.proxy, "deduplicator")
                            and self.proxy.deduplicator
                        ):
                            self.proxy.deduplicator.mark_seen(sender_id, packet_id)
                    except Exception as e:
                        logger.warning("Failed to track node/packet: %s", e)

                    channel_name = self.proxy._extract_channel_from_topic(mqtt_msg.topic)
                    if channel_name and not self.proxy._is_channel_uplink_enabled(channel_name):
                        logger.info(
                            "Dropping Node->MQTT message (uplink_enabled=False for channel '%s'): %s",
                            channel_name,
                            mqtt_msg.topic,
                        )
                        return

                    self.proxy.mqtt_handler.publish(
                        mqtt_msg.topic,
                        mqtt_msg.data,
                        retain=mqtt_msg.retained,
                    )

        except Exception as e:
            logger.debug("Error in MQTT proxy interception: %s", e)

        try:
            super()._handleFromRadio(fromRadio)
        except DecodeError as e:
            logger.warning("Protobuf Decode Error (suppressed): %s", e)
        except Exception as e:
            logger.error("Error in StreamInterface processing: %s", e)


class RawTCPInterface(MQTTProxyMixin, TCPInterface):
    """TCP interface with MQTT proxy support and safe error handling."""

    def __init__(self, *args, **kwargs):
        self.proxy = kwargs.pop("proxy", None)
        super().__init__(*args, **kwargs)


class RawSerialInterface(MQTTProxyMixin, SerialInterface):
    """Serial interface with MQTT proxy support and safe error handling."""

    def __init__(self, *args, **kwargs):
        self.proxy = kwargs.pop("proxy", None)
        super().__init__(*args, **kwargs)


def resolve_serial_port(configured_port):
    """Resolve SERIAL_PORT=auto to the most likely Meshtastic USB serial port."""
    port_value = (configured_port or "").strip()
    if port_value.lower() not in AUTO_SERIAL_VALUES:
        return configured_port

    ports = list(list_ports.comports())
    if not ports:
        raise ValueError("SERIAL_PORT=auto requested, but no serial ports were found")

    def port_text(port):
        parts = [
            getattr(port, "device", ""),
            getattr(port, "name", ""),
            getattr(port, "description", ""),
            getattr(port, "manufacturer", ""),
            getattr(port, "product", ""),
            getattr(port, "hwid", ""),
        ]
        return " ".join(str(part).lower() for part in parts if part)

    def has_preferred_usb_id(port):
        vid = getattr(port, "vid", None)
        if vid in PREFERRED_USB_VIDS:
            return True

        hwid = str(getattr(port, "hwid", "")).lower()
        return any(f"vid:pid={vid:04x}:" in hwid for vid in PREFERRED_USB_VIDS)

    def is_excluded_port(port):
        return any(keyword in port_text(port) for keyword in EXCLUDED_SERIAL_KEYWORDS)

    def is_preferred_port_name(device):
        device_str = str(device)
        if re.fullmatch(r"COM\d+", device_str, flags=re.IGNORECASE):
            return True
        return any(device_str.startswith(prefix) for prefix in PREFERRED_SERIAL_PREFIXES if prefix != "COM")

    for port in ports:
        text = port_text(port)
        if any(keyword in text for keyword in MESHTASTIC_USB_KEYWORDS):
            logger.info("Auto-detected Meshtastic serial port: %s (%s)", port.device, port.description)
            return port.device

    for port in ports:
        if has_preferred_usb_id(port):
            logger.info("Auto-detected known USB serial port: %s (%s)", port.device, port.description)
            return port.device

    eligible_ports = [port for port in ports if not is_excluded_port(port)]
    preferred_named_ports = [port for port in eligible_ports if is_preferred_port_name(port.device)]
    if len(preferred_named_ports) == 1:
        port = preferred_named_ports[0]
        logger.info("Auto-detected USB serial port: %s (%s)", port.device, port.description)
        return port.device

    if not preferred_named_ports and len(eligible_ports) == 1:
        port = eligible_ports[0]
        logger.info("Auto-detected only available serial port: %s (%s)", port.device, port.description)
        return port.device

    visible_ports = ", ".join(port.device for port in ports)
    raise ValueError(f"SERIAL_PORT=auto could not identify a Meshtastic USB port. Found: {visible_ports}")


def create_interface(config, proxy_instance):
    """Factory function to create the appropriate interface based on config."""
    if config.interface_type == "tcp":
        logger.info("Creating TCP interface (%s:%s)...", config.tcp_node_host, config.tcp_node_port)
        return RawTCPInterface(
            config.tcp_node_host,
            portNumber=config.tcp_node_port,
            timeout=config.tcp_timeout,
            proxy=proxy_instance,
        )
    if config.interface_type == "serial":
        serial_port = resolve_serial_port(config.serial_port)
        logger.info("Creating Serial interface (%s)...", serial_port)
        return RawSerialInterface(
            serial_port,
            proxy=proxy_instance,
        )
    raise ValueError(f"Unknown interface type: {config.interface_type}")
