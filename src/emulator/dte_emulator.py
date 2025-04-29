"""DTE Emulator implementation.

This module provides the implementation of the DTE Emulator.
"""

import asyncio
import logging
from typing import Optional

from src.interfaces.emulator import Emulator
from src.interfaces.rule import Rule, RuleEngine
from src.interfaces.transport import Transport

log = logging.getLogger("dte-emulator.core")


class DTEEmulator(Emulator):
    """Device Terminal Equipment Emulator implementation.

    This class implements the Emulator interface for simulating device responses
    based on predefined rules.
    """

    def __init__(
        self,
        transport: Transport,
        rules: RuleEngine,
        rx_end: bytes = b"\r\n",
        tx_end: bytes = b"\r\n",
    ) -> None:
        """Initialize a new DTE emulator.

        Args:
            transport: The transport to use for communication.
            rules: The rule engine to use for finding matching rules.
            rx_end: The terminator for received messages.
            tx_end: The default terminator for transmitted messages.
        """
        self.transport = transport
        self.rules = rules
        self.rx_end = rx_end
        self.tx_end = tx_end
        log.info("Emulator initialized with %s transport", transport.__class__.__name__)
        log.info("Using rx_end=%r, tx_end=%r", rx_end, tx_end)

    async def serve_once(self) -> None:
        """Process a single request-response cycle.

        This method reads a message from the transport, finds a matching rule,
        and sends the appropriate response.

        Raises:
            RuntimeError: If an error occurs during processing.
        """
        try:
            # Read a message from the transport
            msg = await self.transport.read_until_terminator(self.rx_end)
            log.debug("Received: %r", msg)

            # Find a matching rule
            rule = await self.rules.get_response(msg.rstrip(self.rx_end))

            if rule:
                # Apply artificial delay if specified
                if rule.delay_ms > 0:
                    log.debug("Delaying response by %d ms", rule.delay_ms)
                    await asyncio.sleep(rule.delay_ms / 1000)

                # Determine the terminator to use
                terminator = (rule.tx_end or self.tx_end.decode()).encode()

                # Send the response
                response = rule.response.encode() + terminator
                log.debug("Responding: %r", response)
                await self.transport.write(response)
            else:
                log.warning("No rule for %r", msg)
        except Exception as e:
            log.error("Error in serve_once: %s", e)
            raise RuntimeError(f"Error processing request: {e}") from e

    async def run(self) -> None:
        """Run the emulator continuously.

        This method opens the transport, continuously processes
        request-response cycles, and properly closes the transport when done.

        The method handles interruptions gracefully (e.g., KeyboardInterrupt).
        """
        log.info("Starting emulator")
        try:
            await self.transport.open()
            log.info("Transport opened")

            while True:
                try:
                    await self.serve_once()
                except asyncio.CancelledError:
                    log.info("Emulator operation cancelled")
                    break
                except Exception as e:
                    log.error("Error in emulator loop: %s", e)
                    # Continue running despite errors
        except asyncio.CancelledError:
            log.info("Emulator operation cancelled")
        except KeyboardInterrupt:
            log.info("Emulator interrupted by user")
        except Exception as e:
            log.error("Fatal error in emulator: %s", e)
        finally:
            log.info("Shutting down emulator")
            try:
                await self.transport.close()
                log.info("Transport closed")
            except Exception as e:
                log.error("Error closing transport: %s", e)
