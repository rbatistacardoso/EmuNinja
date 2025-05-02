from typing import Dict, Any, Optional

from .base import ProtocolHandler, RuleEngine


class RawProtocolHandler(ProtocolHandler):
    """
    A simple protocol handler that treats requests and responses as raw byte streams.
    It directly uses the RuleEngine to find a matching response for the exact
    byte sequence received.
    """

    def __init__(self, config: Dict[str, Any], rule_engine: RuleEngine):
        super().__init__(config, rule_engine)
        self.encoding = config.get("encoding", "utf-8")
        # Could add config for things like expected terminators if needed later

    async def handle_data(self, received_data: bytes) -> Optional[bytes]:
        """
        Handles raw data by looking for an exact match in the RuleEngine.
        """
        print(f"RawHandler received {len(received_data)} bytes.")
        try:
            # Add detailed logging
            print(f"RawHandler received raw bytes: {received_data!r}")  # Show raw bytes
            decoded_data = received_data.decode(self.encoding)
            print(
                f"RawHandler decoded data as string: {decoded_data!r}"
            )  # Show decoded string
        except UnicodeDecodeError as e:
            print(f"RawHandler: UnicodeDecodeError: {e}")
            return None

        # Directly pass the decoded string to the rule engine
        print(f"RawHandler calling rule_engine.find_response with: {decoded_data!r}")
        response = self.rule_engine.find_response(decoded_data)
        print(
            f"RawHandler found response: {response!r}"
        )  # Show response representation

        if response:
            print(f"RawHandler sending {len(response)} bytes response.")
            # Apply any configured delay here later
            # delay = self.rule_engine.get_delay_for_request(received_data)
            # if delay: await asyncio.sleep(delay)
            if isinstance(response, str):
                return response.encode(self.encoding)
            else:
                return str(response).encode(self.encoding)
        else:
            print("RawHandler: No matching rule found.")
            return None
