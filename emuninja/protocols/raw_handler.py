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
        # Could add config for things like expected terminators if needed later

    async def handle_data(self, received_data: bytes) -> Optional[bytes]:
        """
        Handles raw data by looking for an exact match in the RuleEngine.
        """
        print(f"RawHandler received {len(received_data)} bytes.")
        # Directly pass the raw bytes to the rule engine
        response = self.rule_engine.find_response(received_data)

        if response:
            print(f"RawHandler sending {len(response)} bytes response.")
            # Apply any configured delay here later
            # delay = self.rule_engine.get_delay_for_request(received_data)
            # if delay: await asyncio.sleep(delay)
            return response
        else:
            print("RawHandler: No matching rule found.")
            return None
