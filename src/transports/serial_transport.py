"""Serial transport implementation for device emulator.

This module provides a serial port transport implementation using pyserial.
"""

import asyncio
import logging
from typing import Optional

from src.interfaces.transport import Transport

log = logging.getLogger("dte-emulator.serial")


class SerialTransport(Transport):
    """pyserial-based transport implementation.

    This transport uses pyserial to communicate over a serial port, with
    async operations implemented via thread offloading.
    """

    def __init__(self, port: str, baud: int = 9600, timeout: float = 1.0):
        """Initialize a new serial transport.

        Args:
            port: The serial port name (e.g., 'COM3' or '/dev/ttyUSB0').
            baud: The baud rate to use.
            timeout: Read timeout in seconds.

        Raises:
            ImportError: If pyserial is not installed.
            ValueError: If the port parameters are invalid.
        """
        try:
            import serial  # lazy import
        except ImportError as e:
            raise ImportError("pyserial is required for SerialTransport") from e

        self._serial_mod = serial
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        self.loop = asyncio.get_event_loop()
        self._executor = None

    async def open(self) -> None:
        """Open the serial port.

        Raises:
            RuntimeError: If the port cannot be opened.
        """
        if not self.ser.is_open:
            await self.loop.run_in_executor(None, self.ser.open)
        log.info("Serial port %s opened", self.ser.port)

    async def close(self) -> None:
        """Close the serial port."""
        if self.ser.is_open:
            await self.loop.run_in_executor(None, self.ser.close)
        log.info("Serial port %s closed", self.ser.port)

    async def read_until_terminator(self, terminator: bytes) -> bytes:
        """Read data until a terminator sequence is encountered.

        Args:
            terminator: The byte sequence that marks the end of a message.

        Returns:
            The data read including the terminator.

        Raises:
            RuntimeError: If reading fails.
        """

        def _read():
            return self.ser.read_until(terminator)

        data = await self.loop.run_in_executor(None, _read)
        log.debug("Read from serial: %r", data)
        return data

    async def write(self, data: bytes) -> None:
        """Write data to the serial port.

        Args:
            data: The byte sequence to write.

        Raises:
            RuntimeError: If writing fails.
        """
        await self.loop.run_in_executor(None, self.ser.write, data)
        log.debug("Wrote to serial: %r", data)
