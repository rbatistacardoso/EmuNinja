# emuninja/interfaces/tcp_interface.py

import asyncio
import logging
from typing import Dict, Any, Optional, Set

from .base import CommunicationInterface, DataHandlerCallback

# Set up professional logging
# Get the logger for this specific module (__name__ will be 'emuninja.interfaces.tcp_interface')
logger = logging.getLogger(__name__)


class TcpServerInterface(CommunicationInterface):
    """
    Manages TCP server communication for an emulated device.

    This class sets up a TCP server on a specified host and port. It listens
    for incoming client connections, handles data exchange with each client
    independently using an asyncio StreamReader and StreamWriter, and passes
    received data to a registered callback handler.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the TCP server interface.

        Args:
            config: A dictionary containing configuration parameters.
                    Must include 'host' (str) and 'port' (int).

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
        # Store active writers to manage client connections
        self._writers: Set[asyncio.StreamWriter] = set()
        # Keep track of the main server task to cancel it properly
        self._server_task: Optional[asyncio.Task[None]] = None
        # Lock for modifying the _writers set concurrently (though asyncio is mostly single-threaded,
        # tasks can yield, making modifications safer with a lock if complex interactions arise)
        self._writers_lock = asyncio.Lock()

        logger.debug(f"TCP Interface initialized for {self.host}:{self.port}")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        data_handler: DataHandlerCallback,
    ) -> None:
        """
        Coroutine to handle communication with a single connected client.

        Reads data from the client, passes it to the data_handler,
        sends back the response, and handles connection termination.

        Args:
            reader: The asyncio StreamReader for the client connection.
            writer: The asyncio StreamWriter for the client connection.
            data_handler: The callback function to process incoming data.
        """
        peername = writer.get_extra_info("peername", "Unknown Client")
        logger.info(f"Client connected: {peername}")

        async with self._writers_lock:
            self._writers.add(writer)

        try:
            while True:
                # Read data from the client
                try:
                    # Use read(n) or readexactly(n) if message boundaries are known,
                    # or readuntil(separator) if applicable. read(1024) is common for chunking.
                    data = await reader.read(1024)
                except ConnectionError as e:
                    logger.warning(f"Connection error reading from {peername}: {e}")
                    break # Exit loop on connection error

                if not data:
                    # Client closed the connection cleanly
                    logger.info(f"Client disconnected: {peername} (EOF received)")
                    break

                logger.debug(f"Received {len(data)} bytes from {peername}: {data!r}") # Log received data representation

                # Process data using the provided handler
                try:
                    response = await data_handler(data)
                    if response:
                        logger.debug(f"Sending {len(response)} bytes to {peername}: {response!r}")
                        writer.write(response)
                        await writer.drain() # Ensure data is sent
                except Exception as e:
                    logger.error(f"Error in data_handler for {peername}: {e}", exc_info=True)
                    # Decide if we should close connection on handler error, maybe based on exception type
                    # For now, we continue listening

        except asyncio.CancelledError:
            # Task cancellation is usually part of shutdown
            logger.info(f"Client handler cancelled for {peername}")
            raise # Re-raise CancelledError to allow proper task cleanup
        except Exception as e:
            # Catch any other unexpected errors during the loop
            logger.error(f"Unexpected error handling client {peername}: {e}", exc_info=True)
        finally:
            # --- Cleanup actions ---
            logger.debug(f"Cleaning up connection for {peername}")
            # Remove writer from the active set
            async with self._writers_lock:
                self._writers.discard(writer) # Use discard to avoid KeyError if already removed

            # Close the writer stream
            if not writer.is_closing():
                try:
                    writer.close()
                    # Wait for the underlying connection to close (available in Python 3.7+)
                    # Use timeout to prevent hanging indefinitely
                    await asyncio.wait_for(writer.wait_closed(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for writer to close for {peername}")
                except ConnectionError as e:
                     logger.warning(f"Connection error during writer close for {peername}: {e}")
                except Exception as e:
                    logger.error(f"Error closing writer for {peername}: {e}", exc_info=True)

            logger.info(f"Client handler finished for {peername}")

    async def start(self, data_handler: DataHandlerCallback) -> None:
        """
        Starts the TCP server and begins listening for connections.

        Args:
            data_handler: The asynchronous function to call with received data.

        Raises:
            RuntimeError: If the server is already running.
            OSError: If the address/port is already in use or other socket errors occur.
            Exception: For other unexpected errors during server startup.
        """
        if self._server is not None:
            logger.warning(f"Start called but server on {self.host}:{self.port} is already running.")
            # raise RuntimeError("Server is already running.") # Or just return
            return

        logger.info(f"Starting TCP server on {self.host}:{self.port}")
        try:
            # Define the client connection callback using a lambda
            client_connected_cb = lambda r, w: self._handle_client(r, w, data_handler)

            self._server = await asyncio.start_server(
                client_connected_cb, self.host, self.port
            )

            # Start the server task to accept connections
            # Use serve_forever() which runs until the server is closed
            self._server_task = asyncio.create_task(
                self._server.serve_forever(),
                name=f"TCPServer-{self.host}:{self.port}" # Name task for easier debugging
            )

            # Log the actual address the server is listening on (useful if host='0.0.0.0')
            addr = ", ".join(str(sock.getsockname()) for sock in self._server.sockets)
            logger.info(f"Server listening on {addr}")

        except OSError as e:
            logger.error(f"Failed to start server on {self.host}:{self.port}: {e} (Address likely in use)", exc_info=True)
            self._server = None # Ensure server object is None if start failed
            self._server_task = None
            raise # Re-raise the specific OS error
        except Exception as e:
            logger.error(f"Unexpected error starting server on {self.host}:{self.port}: {e}", exc_info=True)
            self._server = None
            self._server_task = None
            raise # Re-raise other exceptions

    async def stop(self) -> None:
        """
        Stops the TCP server and closes all active client connections gracefully.
        """
        if self._server is None and self._server_task is None:
            logger.info(f"Stop called but server on {self.host}:{self.port} was not running.")
            return

        logger.info(f"Stopping server on {self.host}:{self.port}...")

        # 1. Stop accepting new connections
        if self._server:
            try:
                self._server.close()
                # Wait for the server socket to close
                await asyncio.wait_for(self._server.wait_closed(), timeout=5.0)
                logger.debug(f"Server socket {self.host}:{self.port} closed.")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for server socket {self.host}:{self.port} to close.")
            except Exception as e:
                logger.error(f"Error closing server socket {self.host}:{self.port}: {e}", exc_info=True)
            finally:
                self._server = None

        # 2. Close existing client connections
        # Create a copy to avoid issues if _handle_client modifies the set during iteration
        async with self._writers_lock:
            writers_to_close = list(self._writers)
        if writers_to_close:
             logger.info(f"Closing {len(writers_to_close)} active client connection(s)...")
             close_tasks = []
             for writer in writers_to_close:
                 peername = writer.get_extra_info('peername', 'Unknown Client')
                 if not writer.is_closing():
                     writer.close()
                     # Schedule wait_closed for concurrent execution
                     close_tasks.append(
                         asyncio.wait_for(writer.wait_closed(), timeout=5.0)
                     )
                     logger.debug(f"Initiated close for client {peername}")

             # Wait for all client close operations concurrently
             results = await asyncio.gather(*close_tasks, return_exceptions=True)
             for i, result in enumerate(results):
                  peername = writers_to_close[i].get_extra_info('peername', 'Unknown Client')
                  if isinstance(result, asyncio.TimeoutError):
                      logger.warning(f"Timeout closing connection for client {peername}")
                  elif isinstance(result, Exception):
                      logger.error(f"Error during client close for {peername}: {result}", exc_info=isinstance(result, Exception)) # Log exception details


        # 3. Cancel the main server task
        if self._server_task and not self._server_task.done():
            logger.debug(f"Cancelling main server task for {self.host}:{self.port}")
            self._server_task.cancel()
            try:
                # Wait for the task to acknowledge cancellation
                await self._server_task
            except asyncio.CancelledError:
                logger.debug(f"Main server task cancelled successfully for {self.host}:{self.port}")
            except Exception as e:
                # Should not happen often if cancellation is handled correctly
                logger.error(f"Unexpected error waiting for main server task cancellation: {e}", exc_info=True)
            finally:
                self._server_task = None

        # Clear the writers set after ensuring all are processed
        async with self._writers_lock:
            self._writers.clear()

        logger.info(f"Server on {self.host}:{self.port} stopped.")

    async def send(self, data: bytes) -> None:
        """
        Sends data to all currently connected clients (broadcast).

        Note: This broadcasts data. For request-response protocols, sending
        should typically happen within the _handle_client method in response
        to a specific client's request. Use this method with caution.

        Args:
            data: The bytes to send to all connected clients.
        """
        async with self._writers_lock:
            if not self._writers:
                logger.warning(f"Send ({self.host}:{self.port}): No clients connected.")
                return

            logger.debug(f"Broadcasting {len(data)} bytes to {len(self._writers)} clients on {self.host}:{self.port}")
            # Create a list of tasks to perform sends concurrently
            send_tasks = []
            valid_writers = [] # Keep track of writers we attempt to send to

            for writer in self._writers:
                # Check if writer is usable before attempting to send
                if not writer.is_closing():
                    valid_writers.append(writer)
                    peername = writer.get_extra_info('peername', 'Unknown')
                    # Create a small task for each send operation
                    async def send_to_writer(w: asyncio.StreamWriter, d: bytes, pn: str):
                        try:
                            w.write(d)
                            await w.drain()
                            return None # Indicate success
                        except ConnectionError as e:
                            logger.warning(f"Send ({self.host}:{self.port}): Connection error sending to {pn}: {e}")
                            return e # Return error
                        except Exception as e:
                            logger.error(f"Send ({self.host}:{self.port}): Unexpected error sending to {pn}: {e}", exc_info=True)
                            return e # Return error

                    send_tasks.append(send_to_writer(writer, data, peername))
                else:
                     logger.debug(f"Send ({self.host}:{self.port}): Skipping closing writer for {writer.get_extra_info('peername', 'Unknown')}")


            # Execute all send tasks concurrently and gather results
            results = await asyncio.gather(*send_tasks)

        # Log summary of broadcast
        sent_count = sum(1 for r in results if r is None)
        failed_count = len(results) - sent_count
        if failed_count > 0:
            logger.warning(f"Broadcast ({self.host}:{self.port}) complete: {sent_count} successful, {failed_count} failed.")
        else:
            logger.info(f"Broadcast ({self.host}:{self.port}) complete: {sent_count} successful.")

        # Note: This send method doesn't automatically remove failed writers.
        # The _handle_client method is responsible for cleanup when reads/writes fail there.

# Example of how to set up basic logging if running this file directly for testing
# In a real application, logging should be configured at the entry point (e.g., run_emulator.py)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, # Set to DEBUG to see detailed logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    async def dummy_handler(data: bytes) -> Optional[bytes]:
        """A simple echo handler for testing."""
        logger.info(f"Dummy Handler received: {data!r}")
        await asyncio.sleep(0.1) # Simulate work
        return b"ECHO: " + data

    async def test_server():
        config = {"host": "127.0.0.1", "port": 9999}
        server_interface = TcpServerInterface(config)

        try:
            await server_interface.start(dummy_handler)
            logger.info("Test server started. Connect with 'nc 127.0.0.1 9999' or telnet.")
            # Keep server running for a while
            await asyncio.sleep(60)
            # Test broadcast send
            await server_interface.send(b"Broadcast message from server!\n")
            await asyncio.sleep(5)

        except Exception as e:
            logger.exception(f"Error during test server run: {e}")
        finally:
            logger.info("Stopping test server...")
            await server_interface.stop()
            logger.info("Test server finished.")

    try:
        asyncio.run(test_server())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")