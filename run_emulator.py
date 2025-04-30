import asyncio
import argparse
import signal
import sys

# Need to import the manager - adjust path if needed when structure is final
# from emuninja.core.emulator import EmulatorManager


# Placeholder class until imports work
class EmulatorManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        print(f"Placeholder EmulatorManager initialized with config: {config_path}")

    async def start_all(self):
        print("Placeholder EmulatorManager: Starting all...")
        await asyncio.sleep(1)
        print("Placeholder EmulatorManager: Started.")

    async def stop_all(self):
        print("Placeholder EmulatorManager: Stopping all...")
        await asyncio.sleep(0.1)
        print("Placeholder EmulatorManager: Stopped.")


async def main():
    parser = argparse.ArgumentParser(
        description="EmuNinja - Industrial Device Emulator"
    )
    parser.add_argument(
        "config_file",
        type=str,
        help="Path to the YAML configuration file defining devices and rules.",
        # Default for easier testing?
        nargs="?",
        default="config.yaml",
    )
    args = parser.parse_args()

    print(f"Using configuration file: {args.config_file}")
    manager = EmulatorManager(config_path=args.config_file)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        print("Stop signal received, shutting down...")
        stop_event.set()

    # Register signal handlers for graceful shutdown
    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    else:
        # Windows specific signal handling (less reliable for Ctrl+C in console)
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

    try:
        await manager.start_all()
        print("Emulator started. Press Ctrl+C to stop.")
        await stop_event.wait()  # Keep running until stop signal
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config_file}' not found.")
        # No need to stop manager if start failed due to missing config
        return  # Exit early
    except Exception as e:
        print(f"An unexpected error occurred during startup: {e}")
        # Attempt cleanup even if startup failed partially
    finally:
        print("Shutting down emulator manager...")
        await manager.stop_all()
        print("Emulator finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught in __main__, exiting.")
