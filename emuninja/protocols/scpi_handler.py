import asyncio
from typing import Dict, Any, Optional

from .base import ProtocolHandler, RuleEngine


class ScpiProtocolHandler(ProtocolHandler):
    """
    Handles SCPI (Standard Commands for Programmable Instruments) communication.
    Assumes commands are newline-terminated ASCII strings.
    """

    def __init__(self, config: Dict[str, Any], rule_engine: RuleEngine):
        super().__init__(config, rule_engine)
        self.terminator = config.get("terminator", "\n").encode("ascii")
        self.encoding = config.get("encoding", "ascii")
        self._buffer = bytearray()  # Buffer for partial commands

    async def handle_data(self, received_data: bytes) -> Optional[bytes]:
        """
        Handles SCPI data, buffering until a terminator is found.
        """
        self._buffer.extend(received_data)
        print(
            f"SCPIHandler received {len(received_data)} bytes, buffer size: {len(self._buffer)}"
        )

        # Process commands separated by the terminator
        response_parts = []
        while True:
            try:
                term_index = self._buffer.find(self.terminator)
                if term_index == -1:
                    # No complete command in buffer yet
                    break

                # Extract the command (including terminator for matching?)
                # Or exclude terminator depending on how rules are defined.
                # Let's assume rules include the terminator for now.
                command_bytes = bytes(self._buffer[: term_index + len(self.terminator)])
                self._buffer = self._buffer[
                    term_index + len(self.terminator) :
                ]  # Remove command from buffer

                print(f"SCPIHandler processing command: {command_bytes!r}")

                # Use rule engine to find response for the complete command
                response = self.rule_engine.find_response(command_bytes)

                if response:
                    print(f"SCPIHandler found response: {response!r}")
                    # Apply delay if configured
                    # delay = self.rule_engine.get_delay_for_command(command_bytes)
                    # if delay: await asyncio.sleep(delay)
                    response_parts.append(response)
                else:
                    print(
                        f"SCPIHandler: No matching rule for command: {command_bytes!r}"
                    )
                    # Optionally send an error response based on SCPI standards?
                    # response_parts.append(b"-100,\"Command error\"\n") # Example error

            except Exception as e:
                print(
                    f"Error processing SCPI command in buffer: {e}"
                )  # Replace with logging
                # Clear buffer or handle error appropriately?
                self._buffer.clear()
                # Maybe return an error response
                # return b"-300,\"Device error\"\n"
                return None  # Or raise?

        # Combine responses if multiple commands were processed
        if response_parts:
            # SCPI usually sends one response per command, often separated by newlines
            # Adjust joining logic based on specific device behavior if needed.
            full_response = b"".join(response_parts)
            print(f"SCPIHandler sending combined response ({len(full_response)} bytes)")
            return full_response
        else:
            # No complete commands processed or no responses generated
            return None
