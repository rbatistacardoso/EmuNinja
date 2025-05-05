import asyncio
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
from pymodbus.pdu import ExceptionResponse

# --- Configuration ---
HOST = "127.0.0.1"  # Use 127.0.0.1 to connect locally
PORT = 502  # Default Modbus TCP port, matching modbus_tcp_server.yaml
UNIT_ID = 1  # Unit ID matching modbus_tcp_server.yaml


async def run_modbus_tests():
    """Connects to the Modbus TCP server and runs various tests."""
    print(f"Attempting to connect to Modbus TCP server at {HOST}:{PORT}...")
    client = AsyncModbusTcpClient(HOST, port=PORT)

    try:
        await client.connect()
    except ConnectionException as e:
        print(f"Connection failed: {e}")
        return

    if not client.connected:
        print("Failed to connect to the server.")
        return

    print("Successfully connected to the server.")

    try:
        # --- Test Reads (Based on modbus_tcp_server.yaml initial values) ---
        print("\n--- Testing Read Operations ---")

        # 1. Read Coils (Addresses: 0, 1, 8)
        print("Reading Coils (Addr: 0, Count: 9)...")
        rr = await client.read_coils(0, 9)
        if isinstance(rr, ExceptionResponse):
            print(f"  Error reading coils: {rr}")
        elif isinstance(rr, ModbusIOException):
            print(f"  Modbus IO Error reading coils: {rr}")
        else:
            # Expected: [True, False, False, False, False, False, False, False, True]
            print(f"  Coils Read: {rr.bits[:9]}")

        # 2. Read Discrete Inputs (Addresses: 0, 1, 2)
        print("Reading Discrete Inputs (Addr: 0, Count: 3)...")
        rr = await client.read_discrete_inputs(0, 3, unit=UNIT_ID)
        if isinstance(rr, ExceptionResponse):
            print(f"  Error reading discrete inputs: {rr}")
        elif isinstance(rr, ModbusIOException):
            print(f"  Modbus IO Error reading discrete inputs: {rr}")
        else:
            # Expected: [True, False, True]
            print(f"  Discrete Inputs Read: {rr.bits[:3]}")

        # 3. Read Holding Registers (Addresses: 0, 1, 10)
        print("Reading Holding Registers (Addr: 0, Count: 11)...")
        rr = await client.read_holding_registers(0, 11, unit=UNIT_ID)
        if isinstance(rr, ExceptionResponse):
            print(f"  Error reading holding registers: {rr}")
        elif isinstance(rr, ModbusIOException):
            print(f"  Modbus IO Error reading holding registers: {rr}")
        else:
            # Expected: [1234, 5678, 0, ..., 0, 1122]
            print(f"  Holding Registers Read (0-1): {rr.registers[0:2]}")
            print(f"  Holding Register Read (10): {rr.registers[10]}")

        # 4. Read Input Registers (Addresses: 0, 1, 2)
        print("Reading Input Registers (Addr: 0, Count: 3)...")
        rr = await client.read_input_registers(0, 3, unit=UNIT_ID)
        if isinstance(rr, ExceptionResponse):
            print(f"  Error reading input registers: {rr}")
        elif isinstance(rr, ModbusIOException):
            print(f"  Modbus IO Error reading input registers: {rr}")
        else:
            # Expected: [1000, 2000, 3000]
            print(f"  Input Registers Read: {rr.registers}")

        # --- Test Writes ---
        print("\n--- Testing Write Operations ---")

        # 5. Write Single Coil (Address 1 to True)
        print("Writing Single Coil (Addr: 1, Value: True)...")
        addr_to_write = 1
        value_to_write = True
        rq = await client.write_coil(addr_to_write, value_to_write, unit=UNIT_ID)
        if isinstance(rq, ExceptionResponse):
            print(f"  Error writing coil: {rq}")
        elif isinstance(rq, ModbusIOException):
            print(f"  Modbus IO Error writing coil: {rq}")
        else:
            print(f"  Write Coil Success: Address={rq.address}, Value={rq.value}")
            # Verify write
            rr = await client.read_coils(addr_to_write, 1, unit=UNIT_ID)
            if not isinstance(rr, (ModbusIOException, ExceptionResponse)):
                print(f"  Verification Read Coil (Addr: {addr_to_write}): {rr.bits[0]}")

        # 6. Write Single Register (Address 1 to 9999)
        print("Writing Single Register (Addr: 1, Value: 9999)...")
        addr_to_write = 1
        value_to_write = 9999
        rq = await client.write_register(addr_to_write, value_to_write, unit=UNIT_ID)
        if isinstance(rq, ExceptionResponse):
            print(f"  Error writing register: {rq}")
        elif isinstance(rq, ModbusIOException):
            print(f"  Modbus IO Error writing register: {rq}")
        else:
            print(f"  Write Register Success: Address={rq.address}, Value={rq.value}")
            # Verify write
            rr = await client.read_holding_registers(addr_to_write, 1, unit=UNIT_ID)
            if not isinstance(rr, (ModbusIOException, ExceptionResponse)):
                print(
                    f"  Verification Read Register (Addr: {addr_to_write}): {rr.registers[0]}"
                )

        # 7. Write Multiple Coils (Address 2, 3 to True, False)
        print("Writing Multiple Coils (Addr: 2, Values: [True, False])...")
        addr_to_write = 2
        values_to_write = [True, False]
        rq = await client.write_coils(addr_to_write, values_to_write, unit=UNIT_ID)
        if isinstance(rq, ExceptionResponse):
            print(f"  Error writing multiple coils: {rq}")
        elif isinstance(rq, ModbusIOException):
            print(f"  Modbus IO Error writing multiple coils: {rq}")
        else:
            print(
                f"  Write Multiple Coils Success: Address={rq.address}, Count={rq.count}"
            )
            # Verify write
            rr = await client.read_coils(
                addr_to_write, len(values_to_write), unit=UNIT_ID
            )
            if not isinstance(rr, (ModbusIOException, ExceptionResponse)):
                print(
                    f"  Verification Read Coils (Addr: {addr_to_write}): {rr.bits[:len(values_to_write)]}"
                )

        # 8. Write Multiple Registers (Address 3, 4 to 1111, 2222)
        print("Writing Multiple Registers (Addr: 3, Values: [1111, 2222])...")
        addr_to_write = 3
        values_to_write = [1111, 2222]
        rq = await client.write_registers(addr_to_write, values_to_write, unit=UNIT_ID)
        if isinstance(rq, ExceptionResponse):
            print(f"  Error writing multiple registers: {rq}")
        elif isinstance(rq, ModbusIOException):
            print(f"  Modbus IO Error writing multiple registers: {rq}")
        else:
            print(
                f"  Write Multiple Registers Success: Address={rq.address}, Count={rq.count}"
            )
            # Verify write
            rr = await client.read_holding_registers(
                addr_to_write, len(values_to_write), unit=UNIT_ID
            )
            if not isinstance(rr, (ModbusIOException, ExceptionResponse)):
                print(
                    f"  Verification Read Registers (Addr: {addr_to_write}): {rr.registers}"
                )

    except ModbusIOException as e:
        print(f"Modbus IO Error during tests: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure the client connection is closed
        if client.connected:
            client.close()
            print("\nConnection closed.")


if __name__ == "__main__":
    print("Starting Modbus TCP Client Test Script...")
    print("Ensure the EmuNinja emulator with the Modbus TCP server enabled is running.")
    try:
        asyncio.run(run_modbus_tests())
    except KeyboardInterrupt:
        print("\nTest script interrupted by user.")
    print("Test script finished.")
