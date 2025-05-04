import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class RuleMatch:
    """Represents a matched rule."""

    response: Any
    delay: float


class RuleEngine:
    """Handles matching requests to configured rules and retrieving responses."""

    def __init__(
        self,
        rules_config: List[Dict[str, Any]],
        registers_config: Optional[Dict[str, Dict[int, Any]]] = None,
    ):
        """
        Initializes the RuleEngine.

        Args:
            rules_config: A list of dictionaries, each defining a request-response rule.
                          Example rule: {'receive': {'type': 'exact', 'value': '*IDN?'},
                                       'respond': {'type': 'exact', 'value': 'Device XYZ'}}
            registers_config: Optional configuration for register-based protocols like Modbus.
                              Example: {'holding': {40001: 123}, 'input': {30001: 1}}
        """
        self.registers = registers_config if registers_config else {}
        self._compiled_rules: List[Dict[str, Any]] = []

        for rule in rules_config:
            compiled_rule = rule.copy()
            if rule.get("receive", {}).get("type") == "regex":
                try:
                    pattern_str = str(rule["receive"]["value"])
                    compiled_rule["_compiled_regex"] = re.compile(pattern_str)
                except (re.error, TypeError) as e:
                    print(f"Warning: Invalid regex '{rule['receive']['value']}': {e}")
                    compiled_rule["_compiled_regex"] = None
            self._compiled_rules.append(compiled_rule)

    def find_response(self, parsed_request: Any) -> Optional[RuleMatch]:
        """
        Finds a matching response and delay for the given parsed request.

        Args:
            parsed_request: The request data, parsed by the ProtocolHandler.
                           Could be a string, bytes, or protocol-specific object.

        Returns:
            A RuleMatch object containing the response value and delay if found, else None.
        """
        for rule in self._compiled_rules:
            receive_rule = rule.get("receive", {})
            if not receive_rule:
                continue

            match_type = receive_rule.get("type")
            request_value = receive_rule.get("value")
            response_rule = rule.get("respond", {})
            response_value = response_rule.get("value")
            delay = float(rule.get("delay", 0.0))

            match_found = False
            try:
                if match_type == "exact":
                    if request_value == parsed_request:
                        match_found = True

                elif match_type == "prefix":
                    if isinstance(parsed_request, (str, bytes)) and isinstance(
                        request_value, (str, bytes)
                    ):
                        if isinstance(parsed_request, str) and isinstance(
                            request_value, str
                        ):
                            if parsed_request.startswith(request_value):
                                match_found = True
                        elif isinstance(parsed_request, bytes) and isinstance(
                            request_value, bytes
                        ):
                            if parsed_request.startswith(request_value):
                                match_found = True

                elif match_type == "regex":
                    compiled_regex = rule.get("_compiled_regex")
                    if compiled_regex:
                        request_str = None
                        if isinstance(parsed_request, bytes):
                            try:
                                request_str = parsed_request.decode(
                                    "utf-8", errors="ignore"
                                )
                            except UnicodeError:
                                pass
                        elif isinstance(parsed_request, str):
                            request_str = parsed_request

                        if request_str is not None and compiled_regex.match(
                            request_str
                        ):
                            match_found = True

                if match_found:
                    return RuleMatch(response=response_value, delay=delay)

            except Exception as e:
                print(f"Error evaluating rule {rule}: {e}")

        return None

    def read_registers(
        self, register_type: str, address: int, count: int
    ) -> Optional[List[int]]:
        """
        Reads values from the configured register map.

        Args:
            register_type: The register type (e.g., 'holding', 'input')
            address: The starting register address
            count: Number of registers to read

        Returns:
            List of integer register values if successful, None if error
        """
        if register_type not in self.registers:
            print(f"Warning: Invalid register type '{register_type}'")
            return None

        if address < 0 or count <= 0:
            print(f"Warning: Invalid address/count: {address}/{count}")
            return None

        registers = self.registers[register_type]
        values: List[int] = []
        for offset in range(count):
            current_addr = address + offset
            if current_addr in registers:
                values.append(registers[current_addr])
            else:
                values.append(0)
                print(f"Warning: Unknown register {register_type}:{current_addr}")

        return values

    def write_register(self, register_type: str, address: int, value: Any) -> bool:
        """
        Writes a value to the configured register map.

        Args:
            register_type: The register type (e.g., 'holding')
            address: The register address
            value: The value to write

        Returns:
            True if successful, False if error
        """
        if register_type not in self.registers:
            print(f"Warning: Invalid register type '{register_type}'")
            return False

        if address < 0:
            print(f"Warning: Invalid address: {address}")
            return False

        self.registers[register_type][address] = value
        return True
