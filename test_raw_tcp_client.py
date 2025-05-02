import socket
import asyncio
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
from pymodbus.pdu import ExceptionResponse

# --- Raw TCP Configuration ---
H_RAW = "127.0.0.1"  # The server's hostname or IP address
P_RAW = 5000  # The port used by the Raw TCP Server Extra
ENCODING_RAW = "utf-8"  # Matching the encoding in config.yaml

# --- Modbus TCP Configuration ---
H_MODBUS = "127.0.0.1"  # Use 127.0.0.1 to connect locally
P_MODBUS = 502  # Default Modbus TCP port, matching modbus_tcp_server.yaml
UNIT_ID_MODBUS = 1  # Unit ID matching modbus_tcp_server.yaml


def run_raw_client_test():
    """Connects to the Raw TCP server and sends a PING."""
    print("\n--- Testing Raw TCP Server ---")
    print(f"Attempting to connect to Raw TCP server at {H_RAW}:{P_RAW}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Add a timeout
            s.connect((H_RAW, P_RAW))
            print("Connected to Raw TCP server!")

            message = "PING"
            print(f"Sending: {message}")
            s.sendall(message.encode(ENCODING_RAW))

            data = s.recv(1024)
            if not data:
                print("Raw TCP server closed the connection unexpectedly.")
            else:
                response = data.decode(ENCODING_RAW)
                print(f"Received: {response}")
                if response == "PONG":
                    print("Raw TCP Test: SUCCESS")
                else:
                    print(f"Raw TCP Test: FAILED (Expected PONG, got {response})")

    except ConnectionRefusedError:
        print(
            f"Raw TCP Connection refused. Is the 'Raw TCP Server Extra' running on {H_RAW}:{P_RAW}?"
        )
    except socket.timeout:
        print("Raw TCP Connection timed out.")
    except socket.error as e:
        print(f"Raw TCP Socket error: {e}")
    finally:
        print("Raw TCP connection test finished.")


async def run_modbus_tests():
    """Connects to the Modbus TCP server and runs various tests."""
    print("\n--- Testing Modbus TCP Server --- (Requires pymodbus)")
    print(f"Attempting to connect to Modbus TCP server at {H_MODBUS}:{P_MODBUS}...")
    client = AsyncModbusTcpClient(H_MODBUS, port=P_MODBUS)

    try:
        await client.connect()
    except ConnectionException as e:
        print(f"Modbus Connection failed: {e}")
        print("Is the 'Modbus TCP Server' device enabled and running?")
        return

    if not client.connected:
        print("Failed to connect to the Modbus server.")
        return

    print("Successfully connected to the Modbus server.")

    success_count = 0
    fail_count = 0

    async def run_test(description, test_func, *args):
        nonlocal success_count, fail_count
        print(f"\n{description}...")
        try:
            result = await test_func(*args)
            if result:
                success_count += 1
                print("  Result: SUCCESS")
            else:
                fail_count += 1
                print("  Result: FAILED")
        except Exception as e:
            fail_count += 1
            print(f"  Result: ERROR ({e})")

    # --- Test Read Operations ---
    async def test_read_coils():
        rr = await client.read_coils(0, 9, unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Error: {rr}")
            return False
        expected = [True, False, False, False, False, False, False, False, True]
        print(f"  Read: {rr.bits[:9]}")
        return rr.bits[:9] == expected

    async def test_read_discrete_inputs():
        rr = await client.read_discrete_inputs(0, 3, unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Error: {rr}")
            return False
        expected = [True, False, True]
        print(f"  Read: {rr.bits[:3]}")
        return rr.bits[:3] == expected

    async def test_read_holding_registers():
        rr = await client.read_holding_registers(0, 11, unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Error: {rr}")
            return False
        print(f"  Read (0-1): {rr.registers[0:2]}, (10): {rr.registers[10]}")
        return (
            rr.registers[0] == 1234
            and rr.registers[1] == 5678
            and rr.registers[10] == 1122
        )

    async def test_read_input_registers():
        rr = await client.read_input_registers(0, 3, unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Error: {rr}")
            return False
        expected = [1000, 2000, 3000]
        print(f"  Read: {rr.registers}")
        return rr.registers == expected

    # --- Test Write Operations ---
    async def test_write_single_coil():
        addr, val = 1, True
        rq = await client.write_coil(addr, val, unit=UNIT_ID_MODBUS)
        if isinstance(rq, (ModbusIOException, ExceptionResponse)):
            print(f"  Write Error: {rq}")
            return False
        rr = await client.read_coils(addr, 1, unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Verification Read Error: {rr}")
            return False
        print(f"  Wrote {val} to Addr {addr}. Verified: {rr.bits[0]}")
        return rr.bits[0] == val

    async def test_write_single_register():
        addr, val = 1, 9999
        rq = await client.write_register(addr, val, unit=UNIT_ID_MODBUS)
        if isinstance(rq, (ModbusIOException, ExceptionResponse)):
            print(f"  Write Error: {rq}")
            return False
        rr = await client.read_holding_registers(addr, 1, unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Verification Read Error: {rr}")
            return False
        print(f"  Wrote {val} to Addr {addr}. Verified: {rr.registers[0]}")
        return rr.registers[0] == val

    async def test_write_multiple_coils():
        addr, vals = 2, [True, False]
        rq = await client.write_coils(addr, vals, unit=UNIT_ID_MODBUS)
        if isinstance(rq, (ModbusIOException, ExceptionResponse)):
            print(f"  Write Error: {rq}")
            return False
        rr = await client.read_coils(addr, len(vals), unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Verification Read Error: {rr}")
            return False
        print(f"  Wrote {vals} to Addr {addr}. Verified: {rr.bits[:len(vals)]}")
        return rr.bits[: len(vals)] == vals

    async def test_write_multiple_registers():
        addr, vals = 3, [1111, 2222]
        rq = await client.write_registers(addr, vals, unit=UNIT_ID_MODBUS)
        if isinstance(rq, (ModbusIOException, ExceptionResponse)):
            print(f"  Write Error: {rq}")
            return False
        rr = await client.read_holding_registers(addr, len(vals), unit=UNIT_ID_MODBUS)
        if isinstance(rr, (ModbusIOException, ExceptionResponse)):
            print(f"  Verification Read Error: {rr}")
            return False
        print(f"  Wrote {vals} to Addr {addr}. Verified: {rr.registers}")
        return rr.registers == vals

    try:
        print("\n--- Running Modbus Tests ---")
        await run_test("Reading Coils", test_read_coils)
        await run_test("Reading Discrete Inputs", test_read_discrete_inputs)
        await run_test("Reading Holding Registers", test_read_holding_registers)
        await run_test("Reading Input Registers", test_read_input_registers)
        await run_test("Writing Single Coil", test_write_single_coil)
        await run_test("Writing Single Register", test_write_single_register)
        await run_test("Writing Multiple Coils", test_write_multiple_coils)
        await run_test("Writing Multiple Registers", test_write_multiple_registers)

    except ModbusIOException as e:
        print(f"Modbus IO Error during tests: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during Modbus tests: {e}")
    finally:
        # Ensure the client connection is closed
        if client.connected:
            client.close()
            print("\nModbus connection closed.")
        print(
            f"--- Modbus Test Summary: SUCCESS={success_count}, FAILED={fail_count} ---"
        )


async def main():
    print("Starting EmuNinja Client Test Script...")
    print("Ensure the EmuNinja emulator is running with required devices enabled.")
    # Run Raw TCP Test first (synchronous)
    run_raw_client_test()
    # Run Modbus TCP Tests (asynchronous)
    await run_modbus_tests()
    print("\nTest script finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest script interrupted by user.")
    except ImportError:
        print("\nError: PyModbus library not found.")
        print("Please install it: pip install pymodbus")
        print("(Skipping Modbus tests)")
        # Optionally run just the raw test if pymodbus isn't installed
        print("\n--- Running Raw TCP Test Only ---")
        run_raw_client_test()
        print("\nTest script finished (Modbus skipped).")
