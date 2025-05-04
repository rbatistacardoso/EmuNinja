import asyncio  # Added import
from typing import Any, Dict, Optional

from loguru import logger  # Import loguru

from .base import ProtocolHandler, RuleEngine
from ..core.rules import RuleMatch  # Import RuleMatch


class RawProtocolHandler(ProtocolHandler):
    """
    A simple protocol handler that treats requests and responses as raw byte streams.
    It directly uses the RuleEngine to find a matching response for the exact
    byte sequence received.
    """

    def __init__(self, config: Dict[str, Any], rule_engine: RuleEngine):
        super().__init__(config, rule_engine)
        self.encoding = config.get("encoding", "utf-8")
        self.terminator = config.get("terminator", b"\n")

    async def handle_data(self, received_data: bytes) -> Optional[bytes]:
        """
        Handles raw data by finding a matching rule, applying delay, and returning the response.
        """
        logger.debug(f"RawHandler received {len(received_data)} bytes.")
        decoded_data_str: Optional[str] = None
        try:
            decoded_data_str = received_data.decode(self.encoding)
            logger.trace(
                f"RawHandler received raw bytes: {received_data!r}, decoded: {decoded_data_str!r}"
            )
        except UnicodeDecodeError as e:
            logger.warning(
                f"RawHandler: Cannot decode received bytes using {self.encoding}: {e}"
            )
            # Optionally try matching raw bytes if decoding fails?
            # For now, return None if we can't decode to the expected string format.
            return None

        # Directly pass the decoded string to the rule engine
        logger.debug(
            f"RawHandler calling rule_engine.find_response with: {decoded_data_str!r}"
        )
        match: Optional[RuleMatch] = self.rule_engine.find_response(decoded_data_str)

        if match:
            logger.debug(
                f"RawHandler found match: response={match.response!r}, delay={match.delay}s"
            )

            # Apply delay if specified
            if match.delay > 0:
                logger.debug(f"RawHandler applying delay: {match.delay}s")
                await asyncio.sleep(match.delay)

            # Prepare the response bytes
            response_value = match.response
            response_bytes: Optional[bytes] = None
            if isinstance(response_value, str):
                response_bytes = response_value.encode(self.encoding)
            elif isinstance(response_value, bytes):
                response_bytes = (
                    response_value  # Assume bytes response is already correct
                )
            elif response_value is not None:
                # Attempt to convert other types to string then encode
                try:
                    response_bytes = str(response_value).encode(self.encoding)
                except Exception as e:
                    logger.error(
                        f"RawHandler: Failed to encode response {response_value!r}: {e}"
                    )
                    # Return None on encoding error
                    return None
            # else: response_value is None

            if response_bytes is not None:
                logger.debug(
                    f"RawHandler sending {len(response_bytes)} bytes response."
                )
                return response_bytes
            else:
                # This handles the case where response_value was None or encoding failed
                logger.warning(
                    f"RawHandler: Matched rule resulted in no valid response bytes for request {decoded_data_str!r} (response value was: {match.response!r})"
                )
                return None
        else:
            logger.debug(
                f"RawHandler: No matching rule found for: {decoded_data_str!r}"
            )
            return None
