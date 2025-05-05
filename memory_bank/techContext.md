# Tech Context: EmuNinja

## 1. Proposed Technology Stack

- **Primary Language:** **Python 3.x**
  - **Rationale:**
    - Excellent ecosystem for network programming (`socket`, `asyncio`), serial communication (`pyserial`), and data handling.
    - Widely used in automation and scientific computing, aligning with the target domain.
    - Good library support for configuration file formats (YAML, JSON).
    - Relatively easy to learn and maintain.
    - Cross-platform compatibility (Windows, Linux, macOS).
- **Core Libraries:**
  - `asyncio`: For handling concurrent TCP connections efficiently. Essential for managing multiple emulated devices or multiple client connections to a single TCP device.
  - `pyserial` (or `pyserial-asyncio`): For serial port communication.
  - `PyYAML` or `ruamel.yaml`: For parsing YAML configuration files. `ruamel.yaml` preserves comments and order, which might be beneficial for user-edited files.
  - `logging` (standard library): For application logging.
- **Testing Framework:**
  - `pytest`: A popular and powerful testing framework for Python.
  - `pytest-asyncio`: For testing `asyncio`-based code.
  - `unittest.mock`: For creating mock objects during unit testing.
- **Potential Libraries for Specific Protocols:**
  - `pymodbus`: For potentially simplifying Modbus RTU/TCP implementation, although building it from scratch using the core libraries is also feasible and might offer more control for emulation purposes.
  - Libraries for SCPI parsing (if complex parsing beyond simple string matching is needed, though often basic string operations suffice).

## 2. Development Setup & Environment

- **Version Control:** Git (Repository hosted on GitHub, GitLab, etc.).
- **Dependency Management:** `pip` with `requirements.txt` or potentially a tool like `Poetry` or `PDM` for more robust dependency management and packaging.
- **Code Formatting/Linting:**
  - `Black`: For automated code formatting.
  - `Flake8` or `Ruff`: For linting (checking code style and potential errors). `Ruff` is significantly faster.
  - `Mypy`: For static type checking (optional but recommended for larger projects).
- **IDE:** VS Code (with Python extensions), PyCharm, or similar.
- **Continuous Integration (CI):** GitHub Actions, GitLab CI, or Jenkins to automate testing, linting, and potentially building/packaging on code commits.

## 3. Technical Constraints & Considerations

- **Cross-Platform:** The core emulator must run reliably on Windows, Linux, and potentially macOS. Library choices should reflect this.
- **Performance:** While not typically a high-performance application, handling multiple concurrent TCP connections efficiently is important (`asyncio` helps here). Serial communication is inherently slower.
- **Error Handling:** Robust error handling is crucial for dealing with communication issues (port unavailable, connection drops, malformed data).
- **Dependencies:** Keep external dependencies minimal and well-justified to simplify deployment and reduce potential conflicts.

## 4. Tool Usage Patterns

- Configuration files (YAML) will be central to defining device behavior.
- Logging will be essential for debugging user configurations and the emulator itself.
- Unit and integration tests will be run frequently during development.
