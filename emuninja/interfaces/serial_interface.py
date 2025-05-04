import asyncio
import sys
from typing import Any, Dict, Optional

from loguru import logger

try:
    import serial
except ImportError:
    logger.error("pyserial is not installed. Please install it: pip install pyserial")
    sys.exit(1)

from .base import CommunicationInterface, DataHandlerCallback


class SerialInterface(CommunicationInterface):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.port_name = config.get("port")
        if not self.port_name:
            raise ValueError("Serial interface config missing 'port'")

        protocol_config = config.get("protocol", {})
        term = protocol_config.get("terminator", "\r\n")
        if isinstance(term, str):
            self._terminator = term.encode("utf-8")
        elif isinstance(term, (bytes, bytearray)):
            self._terminator = bytes(term)
        else:
            raise ValueError(
                f"Invalid terminator type: {type(term)}, expected str or bytes"
            )
        logger.info(f"Using terminator: {self._terminator!r}")

        self._serial_params = {
            k: v for k, v in self.config.items() if k not in ["port", "type"]
        }
        self._serial_params.setdefault("timeout", 0.1)

        self._serial_port: Optional[serial.Serial] = None
        self._listen_task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._reconnect_delay = 5

    async def _listen(self, data_handler: DataHandlerCallback) -> None:
        logger.info(f"Serial listener started on {self.port_name}")
        buffer = b""
        while not self._stop_event.is_set():
            try:
                if not self._serial_port or not self._serial_port.is_open:
                    logger.warning(
                        f"Serial port {self.port_name} is not open or available. Attempting to reconnect..."
                    )
                    await self._close_port()
                    if not await self._open_port():
                        logger.error(
                            f"Reconnect failed for {self.port_name}. Waiting {self._reconnect_delay}s..."
                        )
                        await asyncio.sleep(self._reconnect_delay)
                        continue
                    logger.info(f"Successfully reconnected to {self.port_name}")

                if self._serial_port:
                    data = await asyncio.to_thread(self._serial_port.read_all)
                else:
                    logger.warning("Serial port is None, skipping read.")
                    await asyncio.sleep(0.05)
                    continue

                if data:
                    buffer += data
                    logger.debug(f"Buffer updated: {buffer!r}")

                    if self._terminator in buffer:
                        message, buffer = buffer.split(self._terminator, 1)
                        logger.debug(f"Complete message received: {message!r}")
                        response = await data_handler(message)
                        if response:
                            await self.send(response)
                else:
                    await asyncio.sleep(0.05)

            except serial.SerialException as e:
                logger.error(
                    f"Serial error on {self.port_name}: {e}. Attempting to reconnect..."
                )
                await self._close_port()
                await asyncio.sleep(self._reconnect_delay)
            except asyncio.CancelledError:
                logger.info(f"Serial listener cancelled for {self.port_name}")
                break
            except Exception as e:
                logger.error(
                    f"Unexpected error in serial listener for {self.port_name}: {e}"
                )
                await self._close_port()
                await asyncio.sleep(self._reconnect_delay)

        logger.info(f"Serial listener stopped for {self.port_name}")

    async def _open_port(self) -> bool:
        if self._serial_port and self._serial_port.is_open:
            return True
        try:
            logger.info(
                f"Attempting to open serial port {self.port_name} with params {self._serial_params}..."
            )
            self._serial_port = await asyncio.to_thread(
                serial.Serial, port=self.port_name, **self._serial_params
            )
            if self._serial_port and self._serial_port.is_open:
                logger.info(f"Serial port {self.port_name} opened successfully.")
                await asyncio.to_thread(self._serial_port.reset_input_buffer)
                await asyncio.to_thread(self._serial_port.reset_output_buffer)
                return True
            logger.error(
                f"Serial port {self.port_name} failed to open (is_open is false after construction)."
            )
            self._serial_port = None
            return False
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self.port_name}: {e}")
            self._serial_port = None
            return False
        except Exception as e:
            logger.error(f"Unexpected error opening serial port {self.port_name}: {e}")
            self._serial_port = None
            return False

    async def _close_port(self) -> None:
        port_to_close = self._serial_port
        self._serial_port = None

        if port_to_close and port_to_close.is_open:
            try:
                logger.info(f"Closing serial port {self.port_name}...")
                await asyncio.to_thread(port_to_close.close)
                logger.info(f"Serial port {self.port_name} closed.")
            except Exception as e:
                logger.error(f"Error closing serial port {self.port_name}: {e}")

    async def start(self, data_handler: DataHandlerCallback) -> None:
        self._stop_event.clear()
        if await self._open_port():
            self._listen_task = asyncio.create_task(self._listen(data_handler))
        else:
            logger.error(
                f"Could not start SerialInterface, port {self.port_name} failed to open initially."
            )
            raise ConnectionError(
                f"Failed to open serial port {self.port_name} on start"
            )

    async def stop(self) -> None:
        logger.info(f"Stopping serial interface for {self.port_name}...")
        self._stop_event.set()

        listen_task = self._listen_task
        self._listen_task = None

        if listen_task and not listen_task.done():
            try:
                await asyncio.wait_for(listen_task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Serial listener task for {self.port_name} did not stop gracefully, cancelling."
                )
                listen_task.cancel()
                try:
                    await listen_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(
                        f"Error waiting for cancelled listener task {self.port_name} to stop: {e}"
                    )
            except Exception as e:
                logger.error(
                    f"Error waiting for listener task {self.port_name} to stop gracefully: {e}"
                )

        await self._close_port()
        logger.info(f"Serial interface for {self.port_name} stopped.")

    async def send(self, data: bytes) -> None:
        port_to_write = self._serial_port
        if port_to_write and port_to_write.is_open:
            try:
                # Append terminator to the message
                message_with_terminator = data + self._terminator
                bytes_written = await asyncio.to_thread(
                    port_to_write.write, message_with_terminator
                )
                await asyncio.to_thread(port_to_write.flush)
                logger.debug(
                    f"Sent {bytes_written} bytes via serial {self.port_name}: {message_with_terminator!r}"
                )
            except serial.SerialTimeoutException as e:
                logger.error(f"Timeout sending data via serial {self.port_name}: {e}")
                await self._close_port()
            except serial.SerialException as e:
                logger.error(
                    f"Serial error sending data via serial {self.port_name}: {e}"
                )
                await self._close_port()
            except Exception as e:
                logger.error(
                    f"Unexpected error sending data via serial {self.port_name}: {e}"
                )
                await self._close_port()
        else:
            logger.warning(
                f"Cannot send data, serial port {self.port_name} is not open or available"
            )
