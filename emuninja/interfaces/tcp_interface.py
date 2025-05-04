import asyncio
import logging
from typing import Any, Awaitable, Dict, List, Optional, Set

from .base import CommunicationInterface, DataHandlerCallback

logger = logging.getLogger(__name__)


class TcpServerInterface(CommunicationInterface):
    """
    Manages TCP server communication using asyncio streams.

    Sets up a TCP server, handles client connections concurrently,
    and delegates data processing to a callback.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the TCP server interface.

        Args:
            config: Configuration dictionary containing 'host' (str) and 'port' (int).

        Raises:
            ValueError: If 'host' or 'port' is missing in the config.
        """
        super().__init__(config)
        self.host: Optional[str] = config.get("host")
        self.port: Optional[int] = config.get("port")
        if not self.host or not self.port:
            msg = "TCP interface config missing 'host' or 'port'"
            logger.error(msg + f". Config provided: {config}")
            raise ValueError(msg)

        self._server: Optional[asyncio.AbstractServer] = None
        self._writers: Set[asyncio.StreamWriter] = set()
        self._server_task: Optional[asyncio.Task[None]] = None
        # Specify the Task type argument as None since the coroutine returns None
        self._client_handler_tasks: Set[asyncio.Task[None]] = set()

        logger.debug(f"TCP Interface initialized for {self.host}:{self.port}")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        data_handler: DataHandlerCallback,
    ) -> None:
        """
        Coroutine to handle communication with a single connected client.
        """
        peername = writer.get_extra_info("peername", "Unknown Client")
        logger.info(f"Client connected: {peername}")
        self._writers.add(writer)

        try:
            while True:
                try:
                    data = await reader.read(1024)
                except ConnectionError as e:
                    logger.warning(f"Connection error reading from {peername}: {e}")
                    break

                if not data:
                    logger.info(f"Client disconnected: {peername} (EOF received)")
                    break

                logger.debug(f"Received {len(data)} bytes from {peername}: {data!r}")

                try:
                    response = await data_handler(data)
                    if response:
                        logger.debug(
                            f"Sending {len(response)} bytes to {peername}: {response!r}"
                        )
                        writer.write(response)
                        await writer.drain()
                except Exception as e:
                    logger.error(
                        f"Error in data_handler for {peername}: {e}", exc_info=True
                    )

        except asyncio.CancelledError:
            logger.info(f"Client handler cancelled for {peername}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error handling client {peername}: {e}", exc_info=True
            )
        finally:
            logger.debug(f"Cleaning up connection for {peername}")
            self._writers.discard(writer)
            if not writer.is_closing():
                try:
                    writer.close()
                    await asyncio.wait_for(writer.wait_closed(), timeout=5.0)
                except (asyncio.TimeoutError, ConnectionError, Exception) as e:
                    logger.warning(f"Error/Timeout closing writer for {peername}: {e}")
            logger.info(f"Client handler finished for {peername}")

    def _create_client_handler_task(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        data_handler: DataHandlerCallback,
    ):
        """Creates and tracks the task for handling a client."""
        # Specify the Task type argument as None
        task: asyncio.Task[None] = asyncio.create_task(
            self._handle_client(reader, writer, data_handler),
            name=f"TCPClientHandler-{writer.get_extra_info('peername', 'Unknown')}",
        )
        self._client_handler_tasks.add(task)
        task.add_done_callback(
            self._client_handler_tasks.discard
        )  # Auto-remove when done

    async def start(self, data_handler: DataHandlerCallback) -> None:
        """
        Starts the TCP server and begins listening for connections.

        Args:
            data_handler: The async callback function for processing data.

        Raises:
            RuntimeError: If the server is already running.
            OSError: If the address/port is already in use.
        """
        if self._server is not None:
            logger.warning(
                f"Start called but server on {self.host}:{self.port} is already running."
            )
            return

        logger.info(f"Starting TCP server on {self.host}:{self.port}")
        try:
            # Define the callback as a nested function for clearer type handling
            def client_connected_cb(
                reader: asyncio.StreamReader, writer: asyncio.StreamWriter
            ):
                self._create_client_handler_task(reader, writer, data_handler)

            self._server = await asyncio.start_server(
                client_connected_cb, self.host, self.port
            )

            self._server_task = asyncio.create_task(
                self._server.serve_forever(), name=f"TCPServer-{self.host}:{self.port}"
            )

            addr = ", ".join(str(sock.getsockname()) for sock in self._server.sockets)
            logger.info(f"Server listening on {addr}")

        except OSError as e:
            logger.error(
                f"Failed to start server on {self.host}:{self.port}: {e}", exc_info=True
            )
            self._server = None
            self._server_task = None
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error starting server on {self.host}:{self.port}: {e}",
                exc_info=True,
            )
            self._server = None
            self._server_task = None
            raise

    async def stop(self) -> None:
        """
        Stops the TCP server and closes active connections gracefully.
        """
        if self._server is None and self._server_task is None:
            logger.info(
                f"Stop called but server on {self.host}:{self.port} was not running."
            )
            return

        logger.info(f"Stopping server on {self.host}:{self.port}...")

        # 1. Stop accepting new connections
        if self._server:
            try:
                self._server.close()
                await asyncio.wait_for(self._server.wait_closed(), timeout=5.0)
                logger.debug(f"Server socket {self.host}:{self.port} closed.")
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(
                    f"Error/Timeout closing server socket {self.host}:{self.port}: {e}"
                )
            finally:
                self._server = None

        # 2. Cancel active client handler tasks
        if self._client_handler_tasks:
            logger.info(
                f"Cancelling {len(self._client_handler_tasks)} active client handler task(s)..."
            )
            # Create a copy before iterating
            tasks_to_cancel = list(self._client_handler_tasks)
            for task in tasks_to_cancel:
                task.cancel()
            # Wait for tasks to finish cancellation
            # No need to capture results here, just wait for completion/exceptions
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            logger.debug("Finished waiting for client tasks cancellation.")
            # Tasks remove themselves via done_callback, but clear just in case
            self._client_handler_tasks.clear()

        # 3. Close remaining writers (should be handled by task cancellation, but as a fallback)
        if self._writers:
            logger.debug(f"Closing {len(self._writers)} remaining writer streams...")
            writers_to_close = list(self._writers)  # Create copy
            self._writers.clear()  # Clear original set
            # Type hint for list of awaitables returning None or raising
            close_tasks: List[Awaitable[None]] = []
            for writer in writers_to_close:
                # Removed unused peername variable
                if not writer.is_closing():
                    writer.close()
                    close_tasks.append(
                        asyncio.wait_for(
                            writer.wait_closed(), timeout=2.0
                        )  # Shorter timeout here
                    )
            if close_tasks:
                # Gather tasks that wait for writer close (return None or raise BaseException)
                # Assign to _ to indicate result is unused but provide type hint
                _: list[None | BaseException] = await asyncio.gather(
                    *close_tasks, return_exceptions=True
                )
                logger.debug("Finished closing remaining writer streams.")

        # 4. Cancel the main server task
        if self._server_task and not self._server_task.done():
            logger.debug(f"Cancelling main server task for {self.host}:{self.port}")
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                logger.debug(
                    f"Main server task cancelled successfully for {self.host}:{self.port}"
                )
            except Exception as e:
                logger.error(
                    f"Error waiting for main server task cancellation: {e}",
                    exc_info=True,
                )
            finally:
                self._server_task = None

        logger.info(f"Server on {self.host}:{self.port} stopped.")

    async def send(self, data: bytes) -> None:
        """
        Sends data to all currently connected clients (broadcast).

        Note: Use with caution, typically responses are sent per-client.

        Args:
            data: The bytes to send to all connected clients.
        """
        if not self._writers:
            logger.warning(f"Send ({self.host}:{self.port}): No clients connected.")
            return

        logger.debug(
            f"Broadcasting {len(data)} bytes to {len(self._writers)} clients on {self.host}:{self.port}"
        )
        # Type hint for list of awaitables returning bool or raising
        send_tasks: List[Awaitable[bool]] = []
        writers_copy = list(self._writers)  # Copy for safe iteration

        for writer in writers_copy:
            if not writer.is_closing():
                peername = writer.get_extra_info("peername", "Unknown")

                async def send_to_writer(w: asyncio.StreamWriter, d: bytes, pn: str):
                    try:
                        w.write(d)
                        await w.drain()
                        return True
                    except (ConnectionError, Exception) as e:
                        logger.warning(
                            f"Send ({self.host}:{self.port}): Failed sending to {pn}: {e}"
                        )
                        # Attempt to close writer if send fails
                        if not w.is_closing():
                            w.close()
                        return False

                send_tasks.append(send_to_writer(writer, data, peername))
            else:
                logger.debug(
                    f"Send ({self.host}:{self.port}): Skipping closing writer for {writer.get_extra_info('peername', 'Unknown')}"
                )

        # Gather tasks that send data (return bool or raise BaseException)
        results: list[bool | BaseException] = await asyncio.gather(
            *send_tasks, return_exceptions=True
        )
        # Filter out exceptions and count True results for success
        success_count = sum(1 for r in results if isinstance(r, bool) and r is True)
        # Use len(results) which has the correct type hint now
        logger.info(
            f"Broadcast ({self.host}:{self.port}) complete: {success_count}/{len(results)} successful."
        )
