#!/usr/bin/env python3
"""EmuNinja - Device Terminal Equipment Emulator.

This is the main entry point for the EmuNinja application.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from src.emulator import DTEEmulator
from src.rules.rule_engine import YamlRuleEngine
from src.transports.serial_transport import SerialTransport
from src.transports.tcp_transport import TCPTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("emuninja.log"),
    ],
)
log = logging.getLogger("emuninja")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Command line arguments. If None, sys.argv[1:] is used.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="EmuNinja - Device Terminal Equipment Emulator"
    )

    # Transport selection
    parser.add_argument(
        "--transport",
        choices=["serial", "tcp"],
        required=True,
        help="Transport type to use",
    )

    # Serial transport options
    serial_group = parser.add_argument_group("Serial Transport Options")
    serial_group.add_argument(
        "--port",
        help="Serial port (e.g., COM3 or /dev/ttyUSB0)",
    )
    serial_group.add_argument(
        "--baud",
        type=int,
        default=9600,
        help="Serial baud rate (default: 9600)",
    )

    # TCP transport options
    tcp_group = parser.add_argument_group("TCP Transport Options")
    tcp_group.add_argument(
        "--host",
        default="127.0.0.1",
        help="TCP host address (default: 127.0.0.1)",
    )
    tcp_group.add_argument(
        "--tcp-port",
        type=int,
        default=6000,
        help="TCP port (default: 6000)",
    )

    # Common options
    parser.add_argument(
        "--rules",
        type=Path,
        required=True,
        help="Path to YAML rule file",
    )
    parser.add_argument(
        "--rx-end",
        default="\r\n",
        help="Terminator for received messages (default: \\r\\n)",
    )
    parser.add_argument(
        "--tx-end",
        default="\r\n",
        help="Default terminator for transmitted messages (default: \\r\\n)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args(argv)


def build_transport(args: argparse.Namespace):
    """Build a transport based on command line arguments.

    Args:
        args: Parsed command line arguments.

    Returns:
        A transport instance.

    Raises:
        ValueError: If the transport type is invalid or required options are missing.
    """
    if args.transport == "serial":
        if not args.port:
            raise ValueError("--port is required for serial transport")
        return SerialTransport(args.port, args.baud)
    elif args.transport == "tcp":
        return TCPTransport(args.host, args.tcp_port)
    else:
        raise ValueError(f"Unsupported transport: {args.transport}")


def main(argv: Optional[List[str]] = None) -> int:
    """Run the emulator.

    Args:
        argv: Command line arguments. If None, sys.argv[1:] is used.

    Returns:
        Exit code.
    """
    try:
        # Parse command line arguments
        args = parse_args(argv or sys.argv[1:])

        # Configure logging level
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            log.debug("Debug logging enabled")

        # Build transport
        transport = build_transport(args)

        # Create rule engine
        rule_engine = YamlRuleEngine(args.rules)

        # Create emulator
        emulator = DTEEmulator(
            transport,
            rule_engine,
            args.rx_end.encode(),
            args.tx_end.encode(),
        )

        # Run emulator
        log.info("Starting EmuNinja")
        asyncio.run(emulator.run())
        log.info("EmuNinja stopped")
        return 0
    except KeyboardInterrupt:
        log.info("EmuNinja interrupted by user")
        return 0
    except Exception as e:
        log.error("Error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
