import asyncio
import socket

SERVER_HOSTNAME = "127.0.0.1"
SERVER_PORT = 5000
ENCODING = "utf-8"


def run_raw_client_test():
    """Connects to the Raw TCP server and sends a PING."""
    print("\n--- Testing Raw TCP Server ---")
    print(
        f"Attempting to connect to Raw TCP server at {SERVER_HOSTNAME}:{SERVER_PORT}..."
    )
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Add a timeout
            s.connect((SERVER_HOSTNAME, SERVER_PORT))
            print("Connected to Raw TCP server!")

            message = "PING"
            print(f"Sending: {message}")
            s.sendall(message.encode(ENCODING))

            data = s.recv(1024)
            if not data:
                print("Raw TCP server closed the connection unexpectedly.")
            else:
                response = data.decode(ENCODING)
                print(f"Received: {response}")
                if response == "PONG":
                    print("Raw TCP Test: SUCCESS")
                else:
                    print(f"Raw TCP Test: FAILED (Expected PONG, got {response})")

    except ConnectionRefusedError:
        print(
            f"Raw TCP Connection refused. Is the 'Raw TCP Server Extra' running on {SERVER_HOSTNAME}:{SERVER_PORT}?"
        )
    except socket.timeout:
        print("Raw TCP Connection timed out.")
    except socket.error as e:
        print(f"Raw TCP Socket error: {e}")
    finally:
        print("Raw TCP connection test finished.")


async def main():
    print("Starting EmuNinja Client Test Script...")
    print("Ensure the EmuNinja emulator is running with required devices enabled.")
    # Run Raw TCP Test first (synchronous)
    run_raw_client_test()


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
