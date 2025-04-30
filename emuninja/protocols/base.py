from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


# Forward declaration
class RuleEngine:
    pass


class ProtocolHandler(ABC):
    """Abstract base class for protocol handlers (SCPI, Modbus, Raw, etc.)."""

    def __init__(self, config: Dict[str, Any], rule_engine: "RuleEngine"):
        """
        Initializes the protocol handler.

        Args:
            config: Dictionary containing protocol-specific parameters
                    (e.g., Modbus unit ID, SCPI command terminators).
            rule_engine: The RuleEngine instance used to find responses.
        """
        self.config = config
        self.rule_engine = rule_engine
        # Add logging setup here later
        print(f"Initializing {self.__class__.__name__} with config: {config}")

    @abstractmethod
    async def handle_data(self, received_data: bytes) -> Optional[bytes]:
        """
        Processes received data according to the specific protocol rules.

        This method should parse the `received_data`, potentially manage
        protocol state, use the `rule_engine` to determine the appropriate
        action or response based on the parsed command/request, and format
        the response according to the protocol.

        Args:
            received_data: The raw bytes received from the communication interface.

        Returns:
            The raw bytes of the response to be sent back, or None if no
            response should be sent for this data.
        """
        pass
