import asyncio
import sys
import yaml
from typing import Dict, Any, Optional
import serial
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    "serial_test.log",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    rotation="1 day",
    retention="7 days",
    compression="zip",
)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)


class SerialTester:
    """Tests serial device communication based on YAML configuration."""

    def __init__(self, config_path: str, port: str = "COM1", timeout: float = 0.5):
        """
        Initialize the serial tester.

        Parameters
        ----------
        config_path : str
            Path to the YAML configuration file
        port : str
            Serial port to connect to (default: COM1)
        timeout : float
            Read timeout in seconds (default: 0.5)
        """
        self.config_path = config_path
        self.port = port
        self.timeout = timeout
        self.config: Dict[str, Any] = {}
        self.serial: Optional[serial.Serial] = None
        self.terminator: bytes = b"\r\n"

    def load_config(self) -> None:
        """Load and validate the YAML configuration."""
        try:
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")

            # Validate required fields
            if "protocol" not in self.config:
                raise ValueError("Configuration missing 'protocol' section")
            if "rules" not in self.config["protocol"]:
                raise ValueError("Configuration missing 'rules' in protocol section")

            # Load terminator from config
            protocol_config = self.config.get("protocol", {})
            term = protocol_config.get("terminator", "\r\n")
            if isinstance(term, str):
                self.terminator = term.encode("utf-8")
            elif isinstance(term, (bytes, bytearray)):
                self.terminator = bytes(term)
            else:
                raise ValueError(
                    f"Invalid terminator type: {type(term)}, expected str or bytes"
                )
            logger.info(f"Using terminator: {self.terminator!r}")

            logger.debug(f"Configuration: {self.config}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def connect(self) -> None:
        """Connect to the serial port."""
        try:
            # Get serial parameters from config
            interface_config = self.config.get("interface", {})
            baudrate = interface_config.get("baudrate", 9600)
            bytesize = interface_config.get("bytesize", 8)
            parity = interface_config.get("parity", "N")
            stopbits = interface_config.get("stopbits", 1)

            # Create serial connection
            self.serial = serial.Serial(
                port=self.port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=self.timeout,
            )
            logger.info(f"Connected to {self.port} at {baudrate} baud")
        except Exception as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            raise

    def send_command(self, command: str) -> str:
        """
        Send a command and wait for response.

        Parameters
        ----------
        command : str
            Command to send

        Returns
        -------
        str
            Response received from the device
        """
        if not self.serial:
            raise RuntimeError("Serial port not connected")

        try:
            # Send command with terminator
            logger.debug(f"Sending command: {command}")
            self.serial.write(command.encode() + self.terminator)

            # Read until terminator is found
            response = b""
            while True:
                char = self.serial.read(1)
                if not char:
                    break
                response += char
                if response.endswith(self.terminator):
                    break

            # Remove terminator and decode
            response = response[: -len(self.terminator)].decode().strip()
            logger.debug(f"Received response: {response}")

            return response
        except Exception as e:
            logger.error(f"Error during command execution: {e}")
            raise

    def test_rules(self) -> None:
        """Test all rules defined in the configuration."""
        if not self.serial:
            raise RuntimeError("Serial port not connected")

        rules = self.config["protocol"]["rules"]

        for i, rule in enumerate(rules, 1):
            try:
                command = rule["receive"]["value"]
                expected_response = rule["respond"]["value"].strip()

                logger.info(f"Testing rule {i}: {command} -> {expected_response}")

                response = self.send_command(command)

                if response == expected_response:
                    logger.success(f"Rule {i} passed: {command} -> {response}")
                else:
                    logger.error(
                        f"Rule {i} failed: Expected '{expected_response}', got '{response}'"
                    )

            except Exception as e:
                logger.error(f"Error testing rule {i}: {e}")

    def close(self) -> None:
        """Close the serial connection."""
        if self.serial:
            self.serial.close()
            logger.info(f"Closed connection to {self.port}")


async def main():
    """Main function to run the serial test."""
    tester = None
    try:
        # Create tester instance
        config_path = "devices/serial_raw_device.yaml"
        tester = SerialTester(config_path, port="COM1")

        # Load configuration
        tester.load_config()

        # Connect to serial port
        tester.connect()

        # Test all rules
        tester.test_rules()

    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        # Ensure connection is closed
        if tester:
            tester.close()


if __name__ == "__main__":
    asyncio.run(main())
