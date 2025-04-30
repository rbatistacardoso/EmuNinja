# Progress: EmuNinja (Skeleton Created)

## 1. Current Status

- **Phase:** Implementation (Skeleton Phase).
- **Overall Progress:** ~10% (Core structure in place and initial interfaces implemented).

## 2. What Works (Structure-wise)

- **Project Directory Structure:** Established (`emuninja/`, `tests/`, `docs/`, etc.).
- **Core Class Skeletons:** Defined in `.py` files:
  - `EmulatorManager`, `DeviceInstance` (`core/emulator.py`)
  - `RuleEngine` (`core/rules.py`)
- **Interface Skeletons & Implementations:**
  - `CommunicationInterface` base class (`interfaces/base.py`)
  - Full `SerialInterface` implementation (`interfaces/serial_interface.py`) using `pyserial-asyncio`

## 3. What's Left to Build (Implementation)

- **Core Engine Logic:**
  - Implement `RuleEngine` matching (exact, prefix, regex) and register access logic.
  - Implement `EmulatorManager` YAML loading/validation (`utils/config.py`) and factory logic for creating concrete interface/protocol instances.
  - Implement `DeviceInstance` `start`/`stop` methods to correctly manage the asyncio tasks for its interface.
- **Communication Interface Logic:**
  - Remove completed SerialInterface bullet
  - Implement `TcpServerInterface` `start`/`stop`/`send`/`_handle_client` using `asyncio` streams and server logic.
- **Protocol Handler Logic:**
  - Implement `RawProtocolHandler` `handle_data`.
  - Implement `ScpiProtocolHandler` `handle_data` (including buffering and terminator logic).
  - Implement `ModbusRtuProtocolHandler` `handle_data` (CRC, PDU parsing, register interaction).
  - Implement `ModbusTcpProtocolHandler` `handle_data` (MBAP parsing, PDU parsing, register interaction).
- **Configuration:**
  - Finalize YAML structure details (e.g., specific keys for serial params, rule types).
  - Create example `config.yaml` file(s`.
- **Logging Service:**
  - Design and implement a shared logging setup (e.g., in `utils/logging.py`) and integrate it into all components.
- **User Interface:**
  - Refine `run_emulator.py` CLI arguments and output.
- **Testing:**
  - Write unit tests (`pytest`) for `RuleEngine`, utilities, and individual handlers/interfaces (using mocks).
  - Write integration tests simulating device communication through the `EmulatorManager`.
- **Packaging & Distribution:**
  - Create `setup.py` or `pyproject.toml`.
  - Write `README.md` with usage instructions.
