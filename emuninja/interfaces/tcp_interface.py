import asyncio
from typing import Dict, Any, Optional, Set

from .base import CommunicationInterface, DataHandlerCallback


class TcpServerInterface(CommunicationInterface):
    """Handles communication over a TCP socket server."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the TCP server interface.
        Requires 'port' and 'host' in config.
        """
        super().__init__(config)
        self.host = config.get("host")
        self.port = config.get("port")
        if not self.host or not self.port:
            raise ValueError("TCP interface config missing 'host' or 'port'")

        self._server: Optional[asyncio.AbstractServer] = None
        self._writers: Set[asyncio.StreamWriter] = (
            set()
        )  # Keep track of connected clients
        self._listen_task: Optional[asyncio.Task[None]] = (
            None  # Task for the server itself
        )

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        data_handler: DataHandlerCallback,
    ):
        """Handles communication with a single connected client."""
        self._writers.add(writer)
        peername = writer.get_extra_info("peername")
        print(f"TCP client connected: {peername}")

        while True:
            try:
                data = await reader.read(1024)
                if not data:
                    print(f"TCP client disconnected: {peername}")
                    break

                print(f"Received {len(data)} bytes from {peername}")
                response = await data_handler(data)
                if response:
                    print(f"Sending {len(response)} bytes to {peername}")
                    writer.write(response)
                    await writer.drain()

            except asyncio.CancelledError:
                print(f"Client handler cancelled for {peername}")
                break
            except ConnectionResetError:
                print(f"TCP client connection reset: {peername}")
                break
            except Exception as e:
                print(
                    f"Error handling TCP client {peername}: {e}"
                )  # Replace with logging
                break
            finally:
                # Ensure writer is removed even if loop breaks unexpectedly
                if writer in self._writers:
                    self._writers.remove(writer)
                try:
                    writer.close()
                    if hasattr(writer, "wait_closed"):
                        await writer.wait_closed()
                except Exception as close_e:
                    print(
                        f"Error closing writer for {peername}: {close_e}"
                    )  # Replace with logging

        print(f"TCP client handler finished for {peername}")

    async def start(self, data_handler: DataHandlerCallback):
        """Starts the TCP server and listens for connections."""
        print(f"Starting TCP server on {self.host}:{self.port}...")
        try:
            self._server = await asyncio.start_server(
                lambda r, w: self._handle_client(r, w, data_handler),
                self.host,
                self.port,
            )
            self._listen_task = asyncio.create_task(self._server.serve_forever())
            addr = self._server.sockets[0].getsockname()
            print(f"TCP Server listening on {addr}")

        except Exception as e:
            print(
                f"Failed to start TCP server on {self.host}:{self.port}: {e}"
            )  # Replace with logging
            self._server = None

    async def stop(self):
        """Stops the TCP server and closes all client connections."""
        print(f"Stopping TCP server on {self.host}:{self.port}...")

        # Close the server first to prevent new connections
        if self._server:
            try:
                self._server.close()
                await self._server.wait_closed()
            except Exception as e:
                print(f"Error closing TCP server: {e}")  # Replace with logging
            self._server = None

        # Close all active client connections
        writers_copy = list(self._writers)  # Iterate over a copy
        for writer in writers_copy:
            if (
                writer in self._writers
            ):  # Check if still present (might be removed in _handle_client finally block)
                try:
                    writer.close()
                    if hasattr(writer, "wait_closed"):
                        await writer.wait_closed()
                except Exception as e:
                    print(
                        f"Error closing client writer during stop: {e}"
                    )  # Replace with logging
                finally:
                    if writer in self._writers:
                        self._writers.remove(writer)  # Ensure removal

        # Cancel the main server task if it exists
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self._listen_task = None

        print(f"TCP server on {self.host}:{self.port} stopped.")

    async def send(self, data: bytes):
        """
        Sends data to all connected TCP clients.
        Use with caution - might not be desired behavior for request/response protocols.
        """
        if not self._writers:
            print("TCP Send: No clients connected.")  # Replace with logging
            return

        print(
            f"Broadcasting {len(data)} bytes to {len(self._writers)} TCP clients..."
        )  # Replace with logging
        sent_count = 0
        failed_count = 0
        writers_copy = list(self._writers)  # Iterate over a copy

        for writer in writers_copy:
            # Check if writer is still valid and in the set before sending
            if writer in self._writers and not writer.is_closing():
                try:
                    writer.write(data)
                    await writer.drain()
                    sent_count += 1
                except Exception as e:
                    failed_count += 1
                    print(
                        f"Error sending data to client {writer.get_extra_info('peername')}: {e}"
                    )  # Replace with logging
                    # Optionally remove problematic writers here or let _handle_client handle it
            else:
                # Writer might have been closed/removed concurrently
                failed_count += 1

        print(
            f"TCP Broadcast complete: Sent to {sent_count}, Failed for {failed_count}"
        )  # Replace with logging
