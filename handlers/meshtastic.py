"""Meshtastic Interface Handler for MQTT Proxy."""
# Copyright (c) 2026 LN4CY
# This software is licensed under the MIT License. See LICENSE file for details.

import time
import logging
from meshtastic import mesh_pb2
from meshtastic.tcp_interface import TCPInterface
from meshtastic.serial_interface import SerialInterface
from google.protobuf.message import DecodeError

logger = logging.getLogger("mqtt-proxy.handlers.meshtastic")


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
        logger.info("Creating Serial interface (%s)...", config.serial_port)
        return RawSerialInterface(
            config.serial_port,
            proxy=proxy_instance,
        )
    raise ValueError(f"Unknown interface type: {config.interface_type}")
