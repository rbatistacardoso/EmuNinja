"""Rule interface for device emulator.

This module defines the interfaces for rules and rule engines used by the emulator.
"""

from abc import ABC, abstractmethod
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class Rule(Protocol):
    """Protocol defining the interface for a rule.

    A rule defines how to match an incoming message and what response to send.
    """

    @property
    def response(self) -> str:
        """Get the response string for this rule."""
        ...

    @property
    def delay_ms(self) -> int:
        """Get the delay in milliseconds before sending the response."""
        ...

    @property
    def tx_end(self) -> Optional[str]:
        """Get the custom terminator for this rule's response, if any."""
        ...

    def matches(self, msg: bytes) -> bool:
        """Check if this rule matches the given message.

        Args:
            msg: The message to check against this rule.

        Returns:
            True if the rule matches, False otherwise.
        """
        ...


class RuleEngine(ABC):
    """Abstract rule engine interface.

    A rule engine is responsible for loading and managing rules, and finding
    the appropriate rule for a given message.
    """

    @abstractmethod
    def reload(self) -> None:
        """Reload rules from the source.

        This method should be called to refresh the rules when the source
        has changed.
        """
        ...

    @abstractmethod
    async def get_response(self, msg: bytes) -> Optional[Rule]:
        """Find a rule that matches the given message.

        Args:
            msg: The message to find a matching rule for.

        Returns:
            The matching rule, or None if no rule matches.
        """
        ...
