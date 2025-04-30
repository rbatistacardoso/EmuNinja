import asyncio
from typing import Dict, Any, Optional, List
import logging

# Import the actual interfaces and protocols
from ..interfaces.base import CommunicationInterface
from ..interfaces.serial_interface import SerialInterface
from ..interfaces.tcp_interface import TcpServerInterface
from ..protocols.base import ProtocolHandler
from ..protocols.raw_handler import RawProtocolHandler
from ..protocols.scpi_handler import ScpiProtocolHandler
from ..utils.config import load_config_from_yaml
from .rules import RuleEngine


class DeviceInstance:
    """Represents a single running emulated device."""

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        interface: CommunicationInterface,
        protocol: ProtocolHandler,
    ):
        self.name = name
        self.config = config
        self.interface = interface
        self.protocol = protocol
        self._task: Optional[asyncio.Task[None]] = None
        self.logger = logging.getLogger(f"emuninja.device.{name}")

    async def start(self):
        """Starts the device emulation task."""
        self.logger.info(f"Starting device instance: {self.name}")
        try:
            self._task = asyncio.create_task(
                self.interface.start(self.protocol.handle_data)
            )
        except Exception as e:
            self.logger.error(f"Failed to start device {self.name}: {e}")
            raise

    async def stop(self):
        """Stops the device emulation task."""
        self.logger.info(f"Stopping device instance: {self.name}")
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.interface.stop()


class EmulatorManager:
    """Manages the lifecycle of multiple DeviceInstances."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.devices: Dict[str, DeviceInstance] = {}
        self.logger = logging.getLogger("emuninja.manager")

    def load_config(self):
        """Loads and validates the configuration file."""
        try:
            self.config = load_config_from_yaml(self.config_path)
            self.logger.info(f"Loaded configuration from: {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise

    def _create_interface(self, config: Dict[str, Any]) -> CommunicationInterface:
        """Creates a communication interface based on config."""
        interface_type = config.get("type")
        if not interface_type:
            raise ValueError("Interface config missing 'type'")

        if interface_type == "serial":
            return SerialInterface(config)
        elif interface_type == "tcp":
            return TcpServerInterface(config)
        else:
            raise ValueError(f"Unsupported interface type: {interface_type}")

    def _create_protocol(self, config: Dict[str, Any]) -> ProtocolHandler:
        """Creates a protocol handler based on config."""
        protocol_type = config.get("type")
        if not protocol_type:
            raise ValueError("Protocol config missing 'type'")

        rules_config = config.get("rules", [])
        registers_config = config.get("registers", {})
        rule_engine = RuleEngine(rules_config, registers_config)

        if protocol_type == "raw":
            return RawProtocolHandler(config, rule_engine)
        elif protocol_type == "scpi":
            return ScpiProtocolHandler(config, rule_engine)
        else:
            raise ValueError(f"Unsupported protocol type: {protocol_type}")

    def _create_device_instance(self, device_config: Dict[str, Any]) -> DeviceInstance:
        """Creates a single DeviceInstance from its configuration."""
        name = device_config.get("name", "UnnamedDevice")
        self.logger.info(f"Creating device: {name}")

        try:
            interface = self._create_interface(device_config.get("interface", {}))
            protocol = self._create_protocol(device_config.get("protocol", {}))
            return DeviceInstance(name, device_config, interface, protocol)
        except Exception as e:
            self.logger.error(f"Error creating device {name}: {e}")
            raise

    async def start_all(self):
        """Loads config and starts all configured device instances."""
        self.load_config()
        self.devices = {}
        start_tasks: List[asyncio.Task[None]] = []
        for device_conf in self.config.get("devices", []):
            try:
                instance = self._create_device_instance(device_conf)
                self.devices[instance.name] = instance
                start_tasks.append(asyncio.create_task(instance.start()))
            except Exception as e:
                self.logger.error(
                    f"Error creating device '{device_conf.get('name', 'Unknown')}': {e}"
                )

        if start_tasks:
            await asyncio.gather(*start_tasks)
        else:
            self.logger.warning("No devices configured to start.")

    async def stop_all(self):
        """Stops all running device instances."""
        self.logger.info("Stopping all devices...")
        stop_tasks = [instance.stop() for instance in self.devices.values()]
        if stop_tasks:
            await asyncio.gather(*stop_tasks)
        self.devices = {}
        self.logger.info("All devices stopped.")
