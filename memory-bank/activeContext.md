# Active Context: EmuNinja (Skeleton Created)

## 1. Current Focus

- **Project Scaffolding:** The initial project directory structure and class diagram have been created based on the agreed-upon design.
- **Preparation for Implementation:** Ready to start filling in core components, communication interfaces, and protocol handlers.

## 2. Recent Changes

- Created core Memory Bank files (`projectbrief.md`, `productContext.md`, `systemPatterns.md`, `techContext.md`, `activeContext.md`, `progress.md`).
- Established project directory structure: `emuninja/`, `emuninja/core/`, `emuninja/interfaces/`, `emuninja/protocols/`, `emuninja/utils/`, `tests/`, `docs/`.
- Created skeleton Python files with basic class/interface definitions for:
  - `core/emulator.py` (EmulatorManager, DeviceInstance)
  - `core/rules.py` (RuleEngine)
  - `interfaces/base.py` (CommunicationInterface)
  - `interfaces/serial_interface.py` (SerialInterface skeleton)
- Completed `SerialInterface` implementation with proper docstrings and async I/O.
- Refactored `TcpServerInterface` (`interfaces/tcp_interface.py`) for simplicity, professionalism, and type correctness (removed comments, simplified logic).

## 4. Active Decisions & Considerations

- **Architecture:** Proceeding with the modular, layered design (Interfaces, Core, Protocols) using Strategy/Factory patterns.
- **Technology:** Python 3.x with `asyncio`, `pyserial-asyncio`, `PyYAML`, `logging`.
- **Configuration:** YAML format confirmed. Structure defined in previous discussion.
- **Modbus Implementation:** Decide whether to use `pymodbus` or implement Modbus logic manually for finer emulation control.

## 5. Key Learnings & Insights

- The core challenge remains the flexible abstraction for diverse communication protocols.
- Need to handle asynchronous operations carefully, especially error handling and resource cleanup in interfaces.

## Current Implementation Focus

### Core Components

- **EmulatorManager**: Manages device instances and lifecycle
- **DeviceInstance**: Handles individual device configuration and communication
- **RuleEngine**: Processes rules and manages device state
- **CommunicationInterface**: Base class for all communication interfaces
- **ProtocolHandler**: Base class for all protocol handlers

### Active Interfaces

- **SerialInterface**: Fully implemented with terminator support
- **TcpServerInterface**: In development

### Active Protocols

- **RawProtocolHandler**: Basic implementation complete
- **ScpiProtocolHandler**: In development
- **ModbusProtocolHandler**: Planned

## Technical Stack

- Python 3.8+
- asyncio for asynchronous operations
- pyserial for serial communication
- loguru for logging
- PyYAML for configuration
- pytest for testing

## Current Challenges

1. Ensuring reliable serial communication
2. Managing asynchronous operations
3. Handling device state
4. Implementing protocol-specific features
5. Maintaining clean architecture

## Development Environment

- Windows/Linux support
- VS Code with Python extensions
- Git for version control
- GitHub for repository hosting
