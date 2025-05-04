# EmuNinja

A flexible and extensible device emulator framework for testing and development.

## Features

- Multiple communication interfaces:
  - Serial (RS232/RS485)
  - TCP Server
- Protocol support:
  - Raw (custom protocols)
  - SCPI (Standard Commands for Programmable Instruments)
  - Modbus RTU/TCP
- YAML-based device configuration
- Asynchronous operation
- Extensible architecture
- Comprehensive logging

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/EmuNinja.git
cd EmuNinja
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Configure your devices in the `devices/` directory using YAML files
2. Run the emulator:

```bash
python run_emulator.py
```

## Project Structure

```
EmuNinja/
├── emuninja/              # Core package
│   ├── core/             # Core functionality
│   ├── interfaces/       # Communication interfaces
│   ├── protocols/        # Protocol handlers
│   └── utils/            # Utility functions
├── devices/              # Device configurations
├── docs/                 # Documentation
├── memory-bank/          # Project documentation and context
└── tests/                # Test files
```

## Development Status

⚠️ **Alpha/Unstable** - This is an early development version. Features and APIs may change.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
