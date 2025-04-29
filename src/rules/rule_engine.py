"""Rule engine implementation for device emulator.

This module provides the implementation of the rule engine and rule classes.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Pattern, Union

import yaml

from src.interfaces.rule import Rule, RuleEngine

log = logging.getLogger("dte-emulator.rules")


class YamlRule(Rule):
    """Rule implementation based on YAML configuration.

    This class implements the Rule protocol for rules loaded from YAML files.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize a rule from a configuration dictionary.

        Args:
            config: Dictionary containing rule configuration.
                Must contain a 'match' key with a string value.
                May contain 'response', 'delay_ms', and 'tx_end' keys.

        Raises:
            ValueError: If the configuration is invalid.
        """
        if not isinstance(config, dict):
            raise ValueError("Rule configuration must be a dictionary")

        if "match" not in config:
            raise ValueError("Rule must have a 'match' key")

        self._config = config
        self._match_str: str = config["match"]

        # Precompile regex patterns for better performance
        if self._match_str.startswith("regex:"):
            pattern = self._match_str[len("regex:") :]
            self._compiled: Union[Pattern, bytes] = re.compile(pattern.encode())
            self._is_regex = True
        else:
            self._compiled = self._match_str.encode()
            self._is_regex = False

    @property
    def response(self) -> str:
        """Get the response string for this rule."""
        return self._config.get("response", "")

    @property
    def delay_ms(self) -> int:
        """Get the delay in milliseconds before sending the response."""
        return int(self._config.get("delay_ms", 0))

    @property
    def tx_end(self) -> Optional[str]:
        """Get the custom terminator for this rule's response, if any."""
        return self._config.get("tx_end")

    def matches(self, msg: bytes) -> bool:
        """Check if this rule matches the given message.

        Args:
            msg: The message to check against this rule.

        Returns:
            True if the rule matches, False otherwise.
        """
        if self._is_regex:
            return bool(self._compiled.fullmatch(msg))  # type: ignore
        return msg.rstrip() == self._compiled.rstrip()  # type: ignore


class YamlRuleEngine(RuleEngine):
    """Rule engine implementation that loads rules from YAML files.

    This class implements the RuleEngine interface for rules stored in YAML files.
    """

    def __init__(self, path: Path):
        """Initialize a rule engine with rules from a YAML file.

        Args:
            path: Path to the YAML file containing rules.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the file contains invalid YAML.
            ValueError: If the file contains invalid rule configurations.
        """
        self.path = path
        self.rules: List[YamlRule] = []
        self.reload()

    def reload(self) -> None:
        """Reload rules from the YAML file.

        This method should be called to refresh the rules when the file
        has changed.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the file contains invalid YAML.
            ValueError: If the file contains invalid rule configurations.
        """
        try:
            with open(self.path, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, list):
                raise ValueError(f"Rules file {self.path} must contain a list of rules")

            self.rules = [YamlRule(item) for item in data]
            log.info("Loaded %d rules from %s", len(self.rules), self.path)
        except FileNotFoundError:
            log.error("Rules file not found: %s", self.path)
            raise
        except yaml.YAMLError as e:
            log.error("Invalid YAML in rules file %s: %s", self.path, e)
            raise
        except ValueError as e:
            log.error("Invalid rule configuration in %s: %s", self.path, e)
            raise

    async def get_response(self, msg: bytes) -> Optional[Rule]:
        """Find a rule that matches the given message.

        Args:
            msg: The message to find a matching rule for.

        Returns:
            The matching rule, or None if no rule matches.
        """
        for rule in self.rules:
            if rule.matches(msg):
                return rule
        return None
