import re
from typing import Dict, Any, List, Optional, Tuple


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
                          Example rule: {'request': '*IDN?', 'response': 'Device XYZ', 'match_type': 'exact', 'delay': 0.1}
            registers_config: Optional configuration for register-based protocols like Modbus.
                              Example: {'holding': {40001: 123}, 'input': {30001: 1}}
        """
        self.registers = registers_config if registers_config else {}

        # Pre-process rules: compile regex patterns for better performance
        self._compiled_rules: List[Dict[str, Any]] = []
        for rule in rules_config:
            compiled_rule = rule.copy()
            if rule.get("match_type") == "regex":
                try:
                    # Ensure request pattern is treated as string for regex
                    pattern_str = str(rule.get("request", ""))
                    compiled_rule["_compiled_regex"] = re.compile(pattern_str)
                except (re.error, TypeError) as e:
                    print(
                        f"Warning: Invalid regex '{rule.get('request')}': {e}"
                    )  # Replace with logging
                    compiled_rule["_compiled_regex"] = None  # Mark as invalid
            self._compiled_rules.append(compiled_rule)

        print(f"RuleEngine initialized with {len(self._compiled_rules)} rules")

    def find_response(self, parsed_request: Any) -> Optional[Tuple[Any, float]]:
        """
        Finds a matching response for the given parsed request.

        Args:
            parsed_request: The request data, parsed by the ProtocolHandler.
                           Could be a string, bytes, or protocol-specific object.

        Returns:
            Tuple of (response_value, delay_seconds) if match found, else None.
        """
        for rule in self._compiled_rules:
            match_type = rule.get("match_type", "exact")
            request_value = rule.get("request")

            try:
                if match_type == "exact":
                    if request_value == parsed_request:
                        return rule.get("response"), float(rule.get("delay", 0.0))

                elif match_type == "prefix":
                    if isinstance(parsed_request, (str, bytes)) and isinstance(
                        request_value, (str, bytes)
                    ):
                        if parsed_request.startswith(request_value):  # type: ignore
                            return rule.get("response"), float(rule.get("delay", 0.0))

                elif match_type == "regex" and rule.get("_compiled_regex"):
                    # Handle both string and bytes matching
                    if isinstance(parsed_request, bytes):
                        try:
                            request_str = parsed_request.decode(
                                "utf-8", errors="ignore"
                            )
                            if rule["_compiled_regex"].match(request_str):
                                return rule.get("response"), float(
                                    rule.get("delay", 0.0)
                                )
                        except UnicodeError:
                            continue
                    elif isinstance(parsed_request, str):
                        if rule["_compiled_regex"].match(parsed_request):
                            return rule.get("response"), float(rule.get("delay", 0.0))

            except Exception as e:
                print(f"Error evaluating rule {rule}: {e}")  # Replace with logging

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
            print(
                f"Warning: Invalid register type '{register_type}'"
            )  # Replace with logging
            return None

        if address < 0 or count <= 0:
            print(
                f"Warning: Invalid address/count: {address}/{count}"
            )  # Replace with logging
            return None

        registers = self.registers[register_type]
        values: List[int] = []
        for offset in range(count):
            current_addr = address + offset
            if current_addr in registers:
                values.append(registers[current_addr])
            else:
                # Fill with zero for missing registers
                values.append(0)
                print(
                    f"Warning: Unknown register {register_type}:{current_addr}"
                )  # Replace with logging

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
            print(
                f"Warning: Invalid register type '{register_type}'"
            )  # Replace with logging
            return False

        if address < 0:
            print(f"Warning: Invalid address: {address}")  # Replace with logging
            return False

        self.registers[register_type][address] = value
        return True
