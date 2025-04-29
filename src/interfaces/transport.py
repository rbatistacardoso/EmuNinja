"""Transport interface for device emulator.

This module defines the abstract Transport interface that all transport
implementations must follow.
"""

from abc import ABC, abstractmethod


class Transport(ABC):
    """Abstract communication channel interface.

    This interface defines the methods that all transport implementations
    must implement to provide a consistent communication interface for
    the emulator.
    """

    @abstractmethod
    async def open(self) -> None:
        """Open the transport connection.

        This method should establish the connection to the underlying
        communication channel.

        Raises:
            RuntimeError: If the connection cannot be established.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the transport connection.

        This method should properly close the connection to the underlying
        communication channel.
        """
        ...

    @abstractmethod
    async def read_until_terminator(self, terminator: bytes) -> bytes:
        """Read data until a terminator sequence is encountered.

        Args:
            terminator: The byte sequence that marks the end of a message.

        Returns:
            The data read including the terminator.

        Raises:
            RuntimeError: If the transport is not open or if reading fails.
        """
        ...

    @abstractmethod
    async def write(self, data: bytes) -> None:
        """Write data to the transport.

        Args:
            data: The byte sequence to write.

        Raises:
            RuntimeError: If the transport is not open or if writing fails.
        """
        ...
