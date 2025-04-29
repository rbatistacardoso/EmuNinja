"""Emulator interface for device emulator.

This module defines the interface for emulators used in the system.
"""

from abc import ABC, abstractmethod


class Emulator(ABC):
    """Abstract emulator interface.

    An emulator is responsible for handling communication with a client,
    processing incoming messages, and sending appropriate responses.
    """

    @abstractmethod
    async def serve_once(self) -> None:
        """Process a single request-response cycle.

        This method should read a message from the transport, find a matching
        rule, and send the appropriate response.

        Raises:
            RuntimeError: If an error occurs during processing.
        """
        ...

    @abstractmethod
    async def run(self) -> None:
        """Run the emulator continuously.

        This method should open the transport, continuously process
        request-response cycles, and properly close the transport when done.

        The method should handle interruptions gracefully (e.g., KeyboardInterrupt).
        """
        ...
