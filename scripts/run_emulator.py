import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

from emuninja.core.emulator import EmulatorManager

# Configure loguru with enhanced formatting and colors
logger.remove()  # Remove default handler
logger.add(
    "emulator.log",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    rotation="1 day",
    retention="7 days",
    compression="zip",
)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)


async def main():
    devices_path = Path(__file__).parent / "devices"
    logger.info(f"Using devices directory: {devices_path}")

    manager = EmulatorManager(devices_dir=str(devices_path))
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Stop signal received, shutting down...")
        stop_event.set()

    # Setup signal handlers
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                asyncio.get_running_loop().add_signal_handler(sig, signal_handler)
            except ValueError:
                logger.warning(f"Could not add signal handler for {sig}")
    else:
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        try:
            signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        except AttributeError:
            pass

    try:
        await manager.start_all()
        if manager.get_active_device_count() > 0:
            logger.info(
                f"Emulator started with {manager.get_active_device_count()} devices. Press Ctrl+C to stop."
            )
            await stop_event.wait()
        else:
            logger.warning("No active devices found. Exiting.")
    except FileNotFoundError:
        logger.error(f"Devices directory not found: {devices_path}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    asyncio.get_running_loop().remove_signal_handler(sig)
                except ValueError:
                    pass

        logger.info("Shutting down emulator...")
        await manager.stop_all()
        logger.info("Emulator stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, exiting...")
