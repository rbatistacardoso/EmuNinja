from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Awaitable, Optional

# Type alias for the callback function that handles received data
# It takes bytes (received data) and returns an Awaitable (async function)
# that optionally returns bytes (response data).
DataHandlerCallback = Callable[[bytes], Awaitable[Optional[bytes]]]


class CommunicationInterface(ABC):
    """Abstract base class for all communication interfaces (Serial, TCP, etc.)."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the interface with its specific configuration.

        Args:
            config: Dictionary containing interface-specific parameters
                    (e.g., port, baudrate for serial; host, port for TCP).
        """
        self.config = config
        # Add logging setup here later
        print(f"Initializing {self.__class__.__name__} with config: {config}")

    @abstractmethod
    async def start(self, data_handler: DataHandlerCallback):
        """
        Starts the interface listener.

        This method should begin listening for incoming connections or data.
        When data is received, it must call the provided `data_handler`
        callback function, passing the received bytes. If the handler
        returns response bytes, the interface should send them back.

        Args:
            data_handler: An async callable that processes received data
                          and returns optional response data.
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Stops the interface listener and cleans up resources.
        """
        pass

    @abstractmethod
    async def send(self, data: bytes):
        """
        Sends data through the interface.

        Note: This might be primarily used by TCP server interfaces to send
        data back to a specific client, or potentially for unsolicited messages
        in some protocols. The primary response mechanism is often returning
        data from the data_handler callback.

        Args:
            data: The bytes to send.
        """
        pass
