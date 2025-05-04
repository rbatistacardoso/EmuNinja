import asyncio
import glob
import logging
import os
from typing import Any, Dict, List, Optional

# Import the actual interfaces and protocols
from ..interfaces.base import CommunicationInterface
from ..interfaces.serial_interface import SerialInterface
from ..interfaces.tcp_interface import TcpServerInterface
from ..protocols.base import ProtocolHandler
from ..protocols.modbus_tcp_handler import ModbusTcpProtocolHandler
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
            if hasattr(self.protocol, "start"):
                await self.protocol.start()
            else:
                self._task = asyncio.create_task(
                    self.interface.start(self.protocol.handle_data)
                )
        except Exception as e:
            self.logger.error(f"Failed to start device {self.name}: {e}")
            raise

    async def stop(self):
        """Stops the device emulation task."""
        self.logger.info(f"Stopping device instance: {self.name}")
        if hasattr(self.protocol, "stop"):
            await self.protocol.stop()
        else:
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            await self.interface.stop()


class EmulatorManager:
    """Manages the lifecycle of multiple DeviceInstances."""

    def __init__(self, devices_dir: str):
        self.devices_dir = devices_dir
        self.devices: Dict[str, DeviceInstance] = {}
        self.logger = logging.getLogger("emuninja.manager")

    def load_configs(self):
        """Loads and validates all device configuration files from the devices directory."""
        if not os.path.exists(self.devices_dir):
            raise FileNotFoundError(f"Devices directory not found: {self.devices_dir}")

        device_configs = []
        for config_file in glob.glob(os.path.join(self.devices_dir, "*.yaml")):
            try:
                device_config = load_config_from_yaml(config_file)
                device_configs.append(device_config)
                self.logger.info(f"Loaded device configuration from: {config_file}")
            except Exception as e:
                self.logger.error(f"Failed to load config from {config_file}: {e}")
                raise

        return device_configs

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

    def _create_protocol(
        self, config: Dict[str, Any], interface_config: Dict[str, Any]
    ) -> ProtocolHandler:
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
            return ScpiProtocolHandler(config, rule_engine, interface_config)
        elif protocol_type == "modbus_tcp":
            return ModbusTcpProtocolHandler(config, rule_engine, interface_config)
        else:
            raise ValueError(f"Unsupported protocol type: {protocol_type}")

    def _create_device_instance(self, device_config: Dict[str, Any]) -> DeviceInstance:
        """Creates a single DeviceInstance from its configuration."""
        name = device_config.get("name", "UnnamedDevice")
        self.logger.info(f"Creating device: {name}")

        try:
            interface_config = device_config.get("interface", {})
            interface = self._create_interface(interface_config)
            protocol = self._create_protocol(
                device_config.get("protocol", {}), interface_config
            )
            return DeviceInstance(name, device_config, interface, protocol)
        except Exception as e:
            self.logger.error(f"Error creating device {name}: {e}")
            raise

    async def start_all(self):
        """Loads configs and starts all configured and enabled device instances."""
        device_configs = self.load_configs()
        self.devices = {}
        start_tasks: List[asyncio.Task[None]] = []
        loaded_device_count = 0

        for device_conf in device_configs:
            loaded_device_count += 1
            device_name = device_conf.get("name", "Unknown")
            is_enabled = device_conf.get("enabled", True)

            if not isinstance(is_enabled, bool):
                self.logger.warning(
                    f"Device '{device_name}': 'enabled' flag is not a boolean ({is_enabled}). Assuming true."
                )
                is_enabled = True

            if not is_enabled:
                self.logger.info(f"Skipping disabled device: {device_name}")
                continue

            try:
                instance = self._create_device_instance(device_conf)
                self.devices[instance.name] = instance
                start_tasks.append(asyncio.create_task(instance.start()))
            except Exception as e:
                self.logger.error(
                    f"Error creating or starting enabled device '{device_name}': {e}"
                )

        if not device_configs:
            self.logger.warning(
                "No device configuration files found in the devices directory."
            )
        elif not start_tasks and loaded_device_count > 0:
            self.logger.warning("No devices were enabled or started successfully.")
        elif start_tasks:
            await asyncio.gather(*start_tasks, return_exceptions=True)
            self.logger.info(
                f"Successfully attempted to start {len(start_tasks)} enabled devices."
            )

    async def stop_all(self):
        """Stops all running device instances."""
        self.logger.info("Stopping all devices...")
        stop_tasks = [instance.stop() for instance in self.devices.values()]
        if stop_tasks:
            await asyncio.gather(*stop_tasks)
        self.devices = {}
        self.logger.info("All devices stopped.")

    def get_active_device_count(self) -> int:
        """Returns the number of active device instances."""
        return len(self.devices)
