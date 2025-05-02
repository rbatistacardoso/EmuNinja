import asyncio
import signal
import sys
import os
import logging

from emuninja.core.emulator import EmulatorManager

# Define the devices directory path relative to the project root
DEVICES_DIR = "devices"


async def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    devices_path = os.path.join(project_root, DEVICES_DIR)
    devices_path = os.path.abspath(devices_path)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("emulator.log"), logging.StreamHandler()],
    )
    logging.info(f"Attempting to use devices directory: {devices_path}")
    manager = EmulatorManager(devices_dir=devices_path)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        print("\nStop signal received, shutting down...")
        stop_event.set()

    # Register signal handlers for graceful shutdown
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except ValueError:
                print(f"Warning: Could not add signal handler for {sig}")
    else:
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        try:
            signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        except AttributeError:
            pass

    try:
        await manager.start_all()
        if manager.get_active_device_count() > 0:
            print(
                f"Emulator started using devices from '{devices_path}'. Press Ctrl+C to stop."
            )
            await stop_event.wait()
        else:
            print("No devices were configured or started successfully. Exiting.")

    except FileNotFoundError:
        print(f"Error: Devices directory '{devices_path}' not found.")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.remove_signal_handler(sig)
                except ValueError:
                    pass

        print("Shutting down emulator manager...")
        await manager.stop_all()
        print("Emulator finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt caught directly in __main__, forcing exit.")
