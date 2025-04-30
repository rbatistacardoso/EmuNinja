import asyncio
import serial_asyncio
from typing import Dict, Any, Optional

from .base import CommunicationInterface, DataHandlerCallback


class SerialInterface(CommunicationInterface):
    """Handles communication over a serial port."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the serial interface.

        Parameters
        ----------
        config : Dict[str, Any]
            Configuration options for the serial connection.
            Must contain:
            - port: the serial device path.
            - baudrate: serial speed (defaults to 9600).
            Other pyserial parameters (bytesize, parity, stopbits, timeout, etc.) may also be provided.
        """
        super().__init__(config)
        self.port = config.get("port")
        if not self.port:
            raise ValueError("Serial interface config missing 'port'")
        self.baudrate = config.get("baudrate", 9600)
        # Store other serial options (bytesize, parity, stopbits, timeout, etc.)
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._listen_task: Optional[asyncio.Task] = None

    async def _listen(self, data_handler: DataHandlerCallback):
        """
        Internal task to continuously read from the serial port.

        Reads up to 1024 bytes at a time and passes them to the data handler.
        If the handler returns a response, it is sent back over serial.
        """
        print(f"Serial listener started on {self.port}")
        while True:
            try:
                data = await self._reader.read(1024)
                if not data:
                    print(f"Serial connection closed on {self.port}")
                    break
                response = await data_handler(data)
                if response:
                    await self.send(response)
            except asyncio.CancelledError:
                print(f"Serial listener cancelled for {self.port}")
                break
            except Exception as e:
                print(f"Error in serial listener for {self.port}: {e}")
                break
        print(f"Serial listener stopped for {self.port}")

    async def start(self, data_handler: DataHandlerCallback):
        """
        Opens the serial port and starts the listener task.

        Parameters
        ----------
        data_handler : DataHandlerCallback
            Coroutine function that processes incoming data and optionally returns a response to send.
        """
        print(f"Opening serial port {self.port} at {self.baudrate} baud...")
        try:
            # Extract serial parameters from config, excluding 'port' and 'baudrate'
            params = {
                k: v for k, v in self.config.items() if k not in ("port", "baudrate")
            }
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self.port, baudrate=self.baudrate, **params
            )
            self._listen_task = asyncio.create_task(self._listen(data_handler))
            print(f"Serial port {self.port} opened successfully.")
        except Exception as e:
            print(f"Failed to open serial port {self.port}: {e}")
            self._reader = None
            self._writer = None

    async def stop(self):
        """
        Stops the listener task and closes the serial port.
        """
        print(f"Closing serial port {self.port}...")
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self._listen_task = None

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                print(f"Error closing serial port {self.port}: {e}")
        self._writer = None
        self._reader = None
        print(f"Serial port {self.port} closed.")

    async def send(self, data: bytes):
        """
        Sends data over the serial port.

        Parameters
        ----------
        data : bytes
            The raw bytes to send over the serial connection.
        """
        if self._writer and not self._writer.is_closing():
            try:
                self._writer.write(data)
                await self._writer.drain()
                print(f"Sent {len(data)} bytes via serial {self.port}")
            except Exception as e:
                print(f"Error sending data via serial {self.port}: {e}")
        else:
            print(f"Cannot send data, serial writer for {self.port} is not available.")
