from typing import Dict, Any, Optional, Union, cast
from dataclasses import dataclass
import asyncio
import logging

# PyModbus Imports - Ensure pymodbus is installed
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer

from .base import (
    ProtocolHandler,
    RuleEngine,
)

# Type aliases for better readability
ModbusRegisterValue = Union[int, bool]
ModbusRegisterConfig = Dict[int, ModbusRegisterValue]
ModbusRegistersConfig = Dict[str, ModbusRegisterConfig]

logger = logging.getLogger(__name__)


@dataclass
class ModbusResponseFrame:
    """Represents a complete Modbus TCP response frame."""

    transaction_id: int
    protocol_id: int
    length: int
    unit_id: int
    pdu: bytes

    def to_bytes(self) -> bytes:
        """Convert the frame to bytes."""
        return (
            self.transaction_id.to_bytes(2, "big")
            + self.protocol_id.to_bytes(2, "big")
            + self.length.to_bytes(2, "big")
            + self.unit_id.to_bytes(1, "big")
            + self.pdu
        )


class ModbusTcpProtocolHandler(ProtocolHandler):
    """
    Handles Modbus TCP communication using PyModbus within the EmuNinja framework.
    Parses requests, interacts with the datastore, and builds responses.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        rule_engine: RuleEngine,
        interface_config: Dict[str, Any],
    ) -> None:
        super().__init__(config, rule_engine)
        self.unit_id: int = config.get("unit_id", 1)
        self.host: str = interface_config.get("host", "127.0.0.1")
        self.port: int = interface_config.get("port", 502)
        self._server_task: Optional[asyncio.Task] = None
        # Use rule_engine primarily to access the pre-parsed register config
        self.context: ModbusServerContext = self._create_context(rule_engine.registers)
        self.identity: ModbusDeviceIdentification = self._create_identity()
        # self.decoder: ServerDecoder = ServerDecoder() # Removed - likely handled by StartAsyncTcpServer
        logger.info(
            f"ModbusTcpHandler initialized for unit ID {self.unit_id} on {self.host}:{self.port}"
        )

    def _create_context(
        self, registers_config: ModbusRegistersConfig
    ) -> ModbusServerContext:
        """Creates a Modbus server context with configured registers."""
        store: ModbusSlaveContext = ModbusSlaveContext(
            di=self._parse_registers(registers_config, "discrete_inputs"),
            co=self._parse_registers(registers_config, "coils"),
            hr=self._parse_registers(registers_config, "holding_registers"),
            ir=self._parse_registers(registers_config, "input_registers"),
        )
        return ModbusServerContext(slaves={self.unit_id: store}, single=False)

    def _parse_registers(
        self, registers_config: ModbusRegistersConfig, register_type: str
    ) -> Dict[int, ModbusRegisterValue]:
        """Helper to parse register values from the config structure."""
        parsed: Dict[int, ModbusRegisterValue] = {}
        # Config stores registers as { addr: [value, description] }
        for addr, data in registers_config.get(register_type, {}).items():
            if isinstance(data, list) and len(data) > 0:
                parsed[addr] = data[0]  # Extract only the value
            else:
                # Fallback or warning for unexpected format
                logger.warning(
                    f"Unexpected format for {register_type} at address {addr}: {data}. Using 0/False."
                )
                parsed[addr] = (
                    0
                    if register_type in ["holding_registers", "input_registers"]
                    else False
                )
        return parsed

    def _create_identity(self) -> ModbusDeviceIdentification:
        """Creates Modbus device identification information."""
        identity: ModbusDeviceIdentification = ModbusDeviceIdentification()
        identity.VendorName = "EmuNinja"
        identity.ProductCode = "EMU-MODBUS"
        identity.VendorUrl = (
            "https://github.com/yourusername/EmuNinja"  # TODO: Update URL?
        )
        identity.ProductName = "Modbus TCP Server"
        identity.ModelName = "Emulator"
        identity.MajorMinorRevision = "1.0.0"
        return identity

    async def start(self):
        """Starts the Modbus TCP server."""
        logger.info(f"Starting Modbus TCP server on {self.host}:{self.port}")
        try:
            self._server_task = asyncio.create_task(
                StartAsyncTcpServer(
                    self.context, identity=self.identity, address=(self.host, self.port)
                )
            )
        except Exception as e:
            logger.error(f"Failed to start Modbus TCP server: {e}")
            raise

    async def stop(self):
        """Stops the Modbus TCP server."""
        logger.info(f"Stopping Modbus TCP server on {self.host}:{self.port}")
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Modbus TCP server stopped on {self.host}:{self.port}")

    # Removed _create_discrete_inputs, _create_coils, etc. - logic moved to _parse_registers
    # Removed start, stop methods - handled by TcpServerInterface
    # Removed _handle_custom_command, _reset_registers - focusing on standard Modbus

    # Removed handle_data method - pymodbus handles the data processing loop internally
