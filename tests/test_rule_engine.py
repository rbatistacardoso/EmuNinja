"""Tests for the rule engine.

This module contains tests for the rule engine implementation.
"""

import os
import tempfile
import unittest
from pathlib import Path

import yaml

from src.rules.rule_engine import YamlRule, YamlRuleEngine


class TestYamlRule(unittest.TestCase):
    """Test cases for the YamlRule class."""

    def test_exact_match(self):
        """Test exact string matching."""
        rule = YamlRule({"match": "TEST", "response": "RESPONSE"})
        self.assertTrue(rule.matches(b"TEST"))
        self.assertFalse(rule.matches(b"TEST2"))
        self.assertFalse(rule.matches(b"test"))  # Case sensitive

    def test_regex_match(self):
        """Test regex pattern matching."""
        rule = YamlRule({"match": "regex:^TEST\\d+$", "response": "RESPONSE"})
        self.assertTrue(rule.matches(b"TEST123"))
        self.assertFalse(rule.matches(b"TEST"))
        self.assertFalse(rule.matches(b"test123"))  # Case sensitive

    def test_properties(self):
        """Test rule properties."""
        rule = YamlRule(
            {"match": "TEST", "response": "RESPONSE", "delay_ms": 100, "tx_end": "\r\n"}
        )
        self.assertEqual(rule.response, "RESPONSE")
        self.assertEqual(rule.delay_ms, 100)
        self.assertEqual(rule.tx_end, "\r\n")

    def test_default_values(self):
        """Test default values for optional properties."""
        rule = YamlRule({"match": "TEST"})
        self.assertEqual(rule.response, "")
        self.assertEqual(rule.delay_ms, 0)
        self.assertIsNone(rule.tx_end)


class TestYamlRuleEngine(unittest.TestCase):
    """Test cases for the YamlRuleEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary rules file
        self.rules_file = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
        self.rules_path = Path(self.rules_file.name)

        # Write test rules to the file
        rules = [
            {"match": "PING", "response": "PONG"},
            {"match": "regex:^ID\\?$", "response": "TEST-DEVICE"},
            {"match": "STATUS?", "response": "OK", "delay_ms": 50},
        ]
        yaml.dump(rules, self.rules_file)
        self.rules_file.close()

        # Create the rule engine
        self.engine = YamlRuleEngine(self.rules_path)

    def tearDown(self):
        """Tear down test fixtures."""
        os.unlink(self.rules_path)

    async def test_get_response(self):
        """Test finding matching rules."""
        # Test exact match
        rule = await self.engine.get_response(b"PING")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.response, "PONG")

        # Test regex match
        rule = await self.engine.get_response(b"ID?")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.response, "TEST-DEVICE")

        # Test match with delay
        rule = await self.engine.get_response(b"STATUS?")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.response, "OK")
        self.assertEqual(rule.delay_ms, 50)

        # Test no match
        rule = await self.engine.get_response(b"UNKNOWN")
        self.assertIsNone(rule)

    def test_reload(self):
        """Test reloading rules from the file."""
        # Modify the rules file
        new_rules = [
            {"match": "PING", "response": "PONG2"},
            {"match": "NEW", "response": "COMMAND"},
        ]
        with open(self.rules_path, "w") as f:
            yaml.dump(new_rules, f)

        # Reload the rules
        self.engine.reload()

        # Check that the rules were updated
        self.assertEqual(len(self.engine.rules), 2)
        self.assertEqual(self.engine.rules[0].response, "PONG2")
        self.assertEqual(self.engine.rules[1].response, "COMMAND")


if __name__ == "__main__":
    unittest.main()
