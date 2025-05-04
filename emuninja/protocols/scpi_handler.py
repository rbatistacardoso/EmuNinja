import asyncio
from typing import Dict, Any, Optional, List

from loguru import logger  # Import loguru

from .base import ProtocolHandler
from ..core.rules import RuleEngine, RuleMatch  # Import RuleMatch


class ScpiProtocolHandler(ProtocolHandler):
    """
    Handles SCPI (Standard Commands for Programmable Instruments) communication.
    Assumes commands are newline-terminated ASCII strings.
    """

    def __init__(self, config: Dict[str, Any], rule_engine: RuleEngine):
        super().__init__(config, rule_engine)
        # Use config directly for terminator and encoding
        self.terminator = self.config.get("terminator", "\n").encode("ascii")
        self.encoding = self.config.get("encoding", "ascii")
        self._buffer = bytearray()  # Buffer for partial commands
        logger.info(
            f"SCPIHandler initialized with terminator {self.terminator!r} and encoding {self.encoding}"
        )

    async def handle_data(self, received_data: bytes) -> Optional[bytes]:
        """
        Handles SCPI data, buffering until a terminator is found, finds responses,
        applies delays, and returns combined response bytes.
        """
        self._buffer.extend(received_data)
        logger.trace(
            f"SCPIHandler received {len(received_data)} bytes, buffer size: {len(self._buffer)}"
        )

        response_parts: List[bytes] = []  # Store byte responses
        while True:
            try:
                term_index = self._buffer.find(self.terminator)
                if term_index == -1:
                    logger.trace("SCPIHandler: No complete command in buffer yet.")
                    break  # No complete command in buffer yet

                # Extract the command bytes (including terminator)
                command_bytes = bytes(self._buffer[: term_index + len(self.terminator)])
                self._buffer = self._buffer[
                    term_index + len(self.terminator) :
                ]  # Consume command

                logger.debug(f"SCPIHandler processing command: {command_bytes!r}")

                # Use rule engine to find response for the complete command
                match: Optional[RuleMatch] = self.rule_engine.find_response(
                    command_bytes
                )

                if match:
                    logger.debug(
                        f"SCPIHandler found match: response={match.response!r}, delay={match.delay}s"
                    )

                    # Apply delay if specified
                    if match.delay > 0:
                        logger.debug(f"SCPIHandler applying delay: {match.delay}s")
                        await asyncio.sleep(match.delay)

                    # Encode response if needed
                    response_value = match.response
                    response_bytes: Optional[bytes] = None
                    if isinstance(response_value, str):
                        response_bytes = response_value.encode(self.encoding)
                    elif isinstance(response_value, bytes):
                        response_bytes = response_value
                    elif response_value is not None:
                        try:
                            response_bytes = str(response_value).encode(self.encoding)
                        except Exception as e:
                            logger.error(
                                f"SCPIHandler: Failed to encode response {response_value!r}: {e}"
                            )
                            # Optionally add an error marker to response_parts?
                            # For now, skip adding this response part.
                            continue  # Move to next command in buffer
                    # else: response_value is None, don't append anything

                    if response_bytes is not None:
                        response_parts.append(response_bytes)
                    else:
                        logger.warning(
                            f"SCPIHandler: Matched rule resulted in no valid response bytes for command {command_bytes!r} (response value was: {match.response!r})"
                        )

                else:
                    logger.debug(
                        f"SCPIHandler: No matching rule for command: {command_bytes!r}"
                    )
                    # Optionally send an error response based on SCPI standards?
                    # response_parts.append(b"-100,\"Command error\"\n") # Example error

            except Exception as e:
                logger.error(
                    f"Error processing SCPI command in buffer: {e}", exc_info=True
                )
                # Clear buffer on error to prevent infinite loops?
                self._buffer.clear()
                # Return an error response? Depends on desired behavior.
                # return b"-300,\"Device error\"\n"
                return None  # Stop processing and return None for now

        # Combine response parts if any were generated
        if response_parts:
            # SCPI usually sends one response per command, often separated by newlines.
            # The terminator should ideally be part of the response value in the rule.
            # Joining with empty bytes assumes responses already include terminators.
            full_response = b"".join(response_parts)
            logger.debug(
                f"SCPIHandler sending combined response ({len(full_response)} bytes)"
            )
            return full_response
        else:
            # No complete commands processed or no responses generated
            logger.trace("SCPIHandler: No response parts generated.")
            return None
