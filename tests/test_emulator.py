"""Tests for the emulator.

This module contains tests for the emulator implementation.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.emulator.dte_emulator import DTEEmulator
from src.interfaces.rule import Rule
from src.interfaces.transport import Transport


class MockRule(Rule):
    """Mock implementation of Rule for testing."""

    def __init__(self, response="TEST", delay_ms=0, tx_end=None):
        self._response = response
        self._delay_ms = delay_ms
        self._tx_end = tx_end

    @property
    def response(self) -> str:
        return self._response

    @property
    def delay_ms(self) -> int:
        return self._delay_ms

    @property
    def tx_end(self) -> str:
        return self._tx_end

    def matches(self, msg: bytes) -> bool:
        return True


class MockTransport(Transport):
    """Mock implementation of Transport for testing."""

    def __init__(self):
        self.read_data = b""
        self.written_data = []
        self.is_open = False

    async def open(self) -> None:
        self.is_open = True

    async def close(self) -> None:
        self.is_open = False

    async def read_until_terminator(self, terminator: bytes) -> bytes:
        return self.read_data

    async def write(self, data: bytes) -> None:
        self.written_data.append(data)


class MockRuleEngine:
    """Mock implementation of RuleEngine for testing."""

    def __init__(self, rule=None):
        self.rule = rule

    def reload(self) -> None:
        pass

    async def get_response(self, msg: bytes) -> Rule:
        return self.rule


class TestDTEEmulator(unittest.TestCase):
    """Test cases for the DTEEmulator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.transport = MockTransport()
        self.rule_engine = MockRuleEngine()
        self.emulator = DTEEmulator(
            self.transport,
            self.rule_engine,
            rx_end=b"\r\n",
            tx_end=b"\r\n",
        )

    async def test_serve_once_with_matching_rule(self):
        """Test serving a request with a matching rule."""
        # Set up the mock transport to return a message
        self.transport.read_data = b"TEST\r\n"

        # Set up the mock rule engine to return a rule
        self.rule_engine.rule = MockRule(response="RESPONSE", tx_end=None)

        # Call serve_once
        await self.emulator.serve_once()

        # Check that the response was written to the transport
        self.assertEqual(len(self.transport.written_data), 1)
        self.assertEqual(self.transport.written_data[0], b"RESPONSE\r\n")

    async def test_serve_once_with_custom_terminator(self):
        """Test serving a request with a custom terminator."""
        # Set up the mock transport to return a message
        self.transport.read_data = b"TEST\r\n"

        # Set up the mock rule engine to return a rule with a custom terminator
        self.rule_engine.rule = MockRule(response="RESPONSE", tx_end="\n")

        # Call serve_once
        await self.emulator.serve_once()

        # Check that the response was written with the custom terminator
        self.assertEqual(len(self.transport.written_data), 1)
        self.assertEqual(self.transport.written_data[0], b"RESPONSE\n")

    async def test_serve_once_with_delay(self):
        """Test serving a request with a delay."""
        # Set up the mock transport to return a message
        self.transport.read_data = b"TEST\r\n"

        # Set up the mock rule engine to return a rule with a delay
        self.rule_engine.rule = MockRule(response="RESPONSE", delay_ms=100)

        # Mock asyncio.sleep to avoid actually waiting
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Call serve_once
            await self.emulator.serve_once()

            # Check that sleep was called with the correct delay
            mock_sleep.assert_called_once_with(0.1)

        # Check that the response was written to the transport
        self.assertEqual(len(self.transport.written_data), 1)
        self.assertEqual(self.transport.written_data[0], b"RESPONSE\r\n")

    async def test_serve_once_with_no_matching_rule(self):
        """Test serving a request with no matching rule."""
        # Set up the mock transport to return a message
        self.transport.read_data = b"TEST\r\n"

        # Set up the mock rule engine to return no rule
        self.rule_engine.rule = None

        # Call serve_once
        await self.emulator.serve_once()

        # Check that no response was written to the transport
        self.assertEqual(len(self.transport.written_data), 0)

    async def test_run(self):
        """Test running the emulator."""
        # Mock the serve_once method to raise an exception after one call
        self.emulator.serve_once = AsyncMock(
            side_effect=[None, asyncio.CancelledError()]
        )

        # Call run
        await self.emulator.run()

        # Check that serve_once was called
        self.emulator.serve_once.assert_called()

        # Check that the transport was opened and closed
        self.assertTrue(self.transport.is_open)


if __name__ == "__main__":
    unittest.main()
