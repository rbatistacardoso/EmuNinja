# EmuNinja Class Diagram (Initial Skeleton)

```mermaid
classDiagram
    direction LR

    class EmulatorManager {
        +str config_path
        +Dict config
        +Dict<DeviceInstance> devices
        +load_config()
        +start_all()*
        +stop_all()*
        -_create_device_instance(device_config: Dict): DeviceInstance
    }

    class DeviceInstance {
        +str name
        +Dict config
        +CommunicationInterface interface
        +ProtocolHandler protocol
        -Task _task
        +start()*
        +stop()*
    }

    class RuleEngine {
        +List<Dict> rules
        +Dict registers
        +find_response(request_data: bytes): Optional<bytes>
        # read_registers(...)
        # write_register(...)
    }

    class CommunicationInterface {
        <<Abstract>>
        +Dict config
        +start(data_handler: Callable)*
        +stop()*
        +send(data: bytes)*
    }

    class SerialInterface {
        +str port
        +int baudrate
        -StreamReader _reader
        -StreamWriter _writer
        -Task _listen_task
        +start(data_handler: Callable)*
        +stop()*
        +send(data: bytes)*
        -_listen(data_handler: Callable)*
    }

    class TcpServerInterface {
        +str host
        +int port
        -AbstractServer _server
        -Set<StreamWriter> _writers
        -Task _listen_task
        +start(data_handler: Callable)*
        +stop()*
        +send(data: bytes)*
        -_handle_client(reader: StreamReader, writer: StreamWriter, data_handler: Callable)*
    }

    class ProtocolHandler {
        <<Abstract>>
        +Dict config
        +RuleEngine rule_engine
        +handle_data(received_data: bytes): Optional<bytes>*
    }

    class RawProtocolHandler {
        +handle_data(received_data: bytes): Optional<bytes>
    }

    class ScpiProtocolHandler {
        +bytes terminator
        +str encoding
        -bytearray _buffer
        +handle_data(received_data: bytes): Optional<bytes>
    }

    class ModbusRtuProtocolHandler {
        +int unit_id
        # ModbusServerContext context
        +handle_data(received_data: bytes): Optional<bytes>
    }

    class ModbusTcpProtocolHandler {
        +int unit_id
        # ModbusServerContext context
        +handle_data(received_data: bytes): Optional<bytes>
    }

    class ConfigUtils {
        <<Utility>>
        +load_config_from_yaml(file_path): Dict*
    }

    EmulatorManager o--> "*" DeviceInstance : manages
    DeviceInstance o--> "1" CommunicationInterface : uses
    DeviceInstance o--> "1" ProtocolHandler : uses
    ProtocolHandler o--> "1" RuleEngine : uses

    CommunicationInterface <|-- SerialInterface
    CommunicationInterface <|-- TcpServerInterface

    ProtocolHandler <|-- RawProtocolHandler
    ProtocolHandler <|-- ScpiProtocolHandler
    ProtocolHandler <|-- ModbusRtuProtocolHandler
    ProtocolHandler <|-- ModbusTcpProtocolHandler

    %% Relationships to Base Types (Implied)
    %% SerialInterface ..> asyncio.StreamReader
    %% SerialInterface ..> asyncio.StreamWriter
    %% TcpServerInterface ..> asyncio.AbstractServer
    %% TcpServerInterface ..> asyncio.StreamWriter

    %% Utility Usage (Conceptual)
    %% EmulatorManager ..> ConfigUtils : uses
```

**Notes:**

*   `*` denotes an `async` method.
*   `Optional~T~` indicates the method might return `T` or `None`.
*   `Dict~K,V~` or `List~T~` show generic types (simplified here).
*   Relationships show composition (`o-->`) and inheritance (`<|--`).
*   Some internal details (like specific asyncio types) and utility usage are simplified or implied.
