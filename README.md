# EmuNinja - Device Terminal Equipment Emulator

EmuNinja is a flexible, rule-driven device emulator designed to simulate device responses for testing applications that communicate with hardware devices. It supports multiple transport protocols and configurable response rules.

## Features

- **Multiple Transport Protocols**: Supports both serial port and TCP/IP communication
- **Rule-Driven Responses**: Define device behavior using simple YAML configuration files
- **Regex Pattern Matching**: Match incoming commands using exact strings or regular expressions
- **Configurable Terminators**: Set custom terminators for both received and transmitted messages
- **Artificial Latency**: Simulate real-world device response times with configurable delays
- **Comprehensive Logging**: Detailed logging of all communication for debugging and analysis
- **Extensible Architecture**: Well-defined interfaces make it easy to add new transport types or rule sources

## Installation

### Prerequisites

- Python 3.7 or higher
- Required packages:
  - pyserial (for serial port communication)
  - pyyaml (for rule configuration)

### Install Dependencies

```bash
pip install pyserial pyyaml
```

## Usage

### Basic Usage

```bash
python src/main.py --transport serial --port COM3 --baud 9600 --rules examples/rules.yml --rx-end "\r\n" --tx-end "\r\n"
```

### TCP Mode

```bash
python src/main.py --transport tcp --host 0.0.0.0 --tcp-port 5000 --rules examples/rules.yml --rx-end "\n" --tx-end "\n"
```

### Command Line Options

- `--transport`: Transport type (`serial` or `tcp`)
- `--port`: Serial port name (e.g., COM3 or /dev/ttyUSB0)
- `--baud`: Serial baud rate (default: 9600)
- `--host`: TCP host address (default: 127.0.0.1)
- `--tcp-port`: TCP port (default: 6000)
- `--rules`: Path to YAML rule file
- `--rx-end`: Terminator for received messages (default: \r\n)
- `--tx-end`: Default terminator for transmitted messages (default: \r\n)
- `--debug`: Enable debug logging

## Rule Configuration

Rules are defined in YAML files. Each rule specifies a pattern to match, a response to send, and optional parameters.

### Example Rule File

```yaml
# Basic ping command
- match: "PING"
  response: "PONG"
  delay_ms: 0

# Device identification command
- match: "regex:^ID\\?$"
  response: "EmuNinja-v1.0"
  tx_end: "\r\n"

# Status command
- match: "STATUS?"
  response: "OK"
```

### Rule Properties

- `match`: The pattern to match (string or regex pattern)
- `response`: The response to send
- `delay_ms`: Optional delay in milliseconds before sending the response
- `tx_end`: Optional custom terminator for this specific response

### Regex Patterns

To use a regular expression pattern, prefix the pattern with `regex:`:

```yaml
- match: "regex:^SET\\s+([A-Z]+)\\s+([0-9]+)$"
  response: "OK"
```

## Project Structure

- `src/`: Source code
  - `interfaces/`: Interface definitions
  - `transports/`: Transport implementations
  - `rules/`: Rule engine implementation
  - `emulator/`: Emulator implementation
  - `main.py`: Main entry point
- `tests/`: Test files
- `examples/`: Example rule files

## Development

### Running Tests

```bash
python -m unittest discover tests
```

### Adding a New Transport

1. Create a new class that implements the `Transport` interface
2. Add the new transport to the `build_transport` function in `src/main.py`

### Adding a New Rule Source

1. Create a new class that implements the `RuleEngine` interface
2. Update the main entry point to use the new rule engine

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
