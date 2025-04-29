"""TCP transport implementation for device emulator.

This module provides a TCP transport implementation using asyncio streams.
"""

import asyncio
import logging
from typing import Optional, Tuple

from src.interfaces.transport import Transport

log = logging.getLogger("dte-emulator.tcp")


class TCPTransport(Transport):
    """Asyncio-streams TCP transport implementation.

    This transport uses asyncio streams to communicate over a TCP connection.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6000):
        """Initialize a new TCP transport.

        Args:
            host: The host address to connect to.
            port: The TCP port to connect to.
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def open(self) -> None:
        """Open the TCP connection.

        Raises:
            ConnectionError: If the connection cannot be established.
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            log.info("Connected to TCP %s:%s", self.host, self.port)
        except (ConnectionRefusedError, OSError) as e:
            log.error("Failed to connect to %s:%s: %s", self.host, self.port, e)
            raise ConnectionError(
                f"Failed to connect to {self.host}:{self.port}"
            ) from e

    async def close(self) -> None:
        """Close the TCP connection."""
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception as e:
                log.warning("Error while closing TCP connection: %s", e)
            log.info("TCP connection closed")

    async def read_until_terminator(self, terminator: bytes) -> bytes:
        """Read data until a terminator sequence is encountered.

        Args:
            terminator: The byte sequence that marks the end of a message.

        Returns:
            The data read including the terminator.

        Raises:
            RuntimeError: If the transport is not open or if reading fails.
        """
        if not self.reader:
            raise RuntimeError("Transport not open")

        try:
            data = await self.reader.readuntil(terminator)
            log.debug("Read from TCP: %r", data)
            return data
        except asyncio.IncompleteReadError as e:
            log.warning("Incomplete read from TCP: %s", e)
            return e.partial
        except asyncio.LimitOverrunError as e:
            log.warning("Buffer limit exceeded: %s", e)
            # Skip to the terminator and return what we can
            await self.reader.readuntil(terminator)
            raise RuntimeError("Message too large") from e

    async def write(self, data: bytes) -> None:
        """Write data to the TCP connection.

        Args:
            data: The byte sequence to write.

        Raises:
            RuntimeError: If the transport is not open or if writing fails.
        """
        if not self.writer:
            raise RuntimeError("Transport not open")

        try:
            self.writer.write(data)
            await self.writer.drain()
            log.debug("Wrote to TCP: %r", data)
        except (ConnectionError, BrokenPipeError) as e:
            log.error("TCP write error: %s", e)
            raise RuntimeError("TCP connection lost") from e
