from __future__ import annotations

"""DTE Emulator — transport‑agnostic, rule‑driven device simulator.

Dependencies
------------
* pyserial   (SerialTransport)
* pyyaml     (RuleEngine YAML loader)

Install with:
    pip install pyserial pyyaml

Usage (example)
--------------
    python dte_emulator.py \
        --transport serial --port COM3 --baud 9600 \
        --rules rules.yml --rx-end "\r" --tx-end "\r\n"

The same executable can run over TCP/IP:
    python dte_emulator.py \
        --transport tcp --host 0.0.0.0 --port 5000 \
        --rules rules.yml --rx-end "\n" --tx-end "\n"

Rules File Format (YAML)
------------------------
- match: "PING"          # exact byte sequence or regex:/pattern/
  response: "PONG"
  delay_ms: 0            # optional artificial latency
- match: "regex:^ID\\?$" # regex pattern (Python syntax)
  response: "DTE‑EMULATOR‑v1.0"
  tx_end: "\r\n"        # optional terminator override
"""

import argparse
import asyncio
import logging
import re
import socket
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional

import yaml  # type: ignore

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("dte-emulator")

###############################################################################
# Transport abstraction #######################################################
###############################################################################


class Transport(ABC):
    """Abstract communication channel."""

    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def read_until(self, terminator: bytes) -> bytes: ...

    @abstractmethod
    async def write(self, data: bytes) -> None: ...


class SerialTransport(Transport):
    """pyserial‑based transport (async via thread offloading)."""

    def __init__(self, port: str, baud: int = 9600, timeout: float = 1.0):
        try:
            import serial  # lazy import
        except ImportError as e:
            raise RuntimeError("pyserial is required for SerialTransport") from e

        self._serial_mod = serial
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        self.loop = asyncio.get_running_loop()
        self._executor = None

    async def open(self):
        if not self.ser.is_open:
            await self.loop.run_in_executor(None, self.ser.open)
        log.info("Serial port %s opened", self.ser.port)

    async def close(self):
        if self.ser.is_open:
            await self.loop.run_in_executor(None, self.ser.close)
        log.info("Serial port %s closed", self.ser.port)

    async def read_until(self, terminator: bytes) -> bytes:
        def _read():
            return self.ser.read_until(terminator)

        return await self.loop.run_in_executor(None, _read)

    async def write(self, data: bytes):
        await self.loop.run_in_executor(None, self.ser.write, data)


class TCPTransport(Transport):
    """Asyncio‑streams TCP transport."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6000):
        self.host, self.port = host, port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def open(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        log.info("Connected to TCP %s:%s", self.host, self.port)

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            log.info("TCP connection closed")

    async def read_until(self, terminator: bytes) -> bytes:
        if not self.reader:
            raise RuntimeError("Transport not open")
        return await self.reader.readuntil(terminator)

    async def write(self, data: bytes):
        if not self.writer:
            raise RuntimeError("Transport not open")
        self.writer.write(data)
        await self.writer.drain()


###############################################################################
# Rule engine #################################################################
###############################################################################


class Rule:
    def __init__(self, raw: Dict):
        self.raw = raw
        self.match: str = raw["match"]  # exact bytes or regex:^pattern$
        self.response: str = raw.get("response", "")
        self.delay_ms: int = int(raw.get("delay_ms", 0))
        self.tx_end: Optional[str] = raw.get("tx_end")

        if self.match.startswith("regex:"):
            pattern = self.match[len("regex:") :]
            self._compiled = re.compile(pattern.encode())
            self.is_regex = True
        else:
            self._compiled = self.match.encode()
            self.is_regex = False

    def matches(self, msg: bytes) -> bool:
        if self.is_regex:
            return bool(self._compiled.fullmatch(msg))
        return msg.rstrip() == self._compiled.rstrip()


class RuleEngine:
    def __init__(self, path: Path):
        self.path = path
        self.rules: List[Rule] = []
        self.reload()

    def reload(self):
        data = yaml.safe_load(self.path.read_text())
        self.rules = [Rule(item) for item in data]
        log.info("Loaded %d rules from %s", len(self.rules), self.path)

    async def get_response(self, msg: bytes) -> Optional[Rule]:
        for rule in self.rules:
            if rule.matches(msg):
                return rule
        return None


###############################################################################
# Emulator ####################################################################
###############################################################################


class DTEEmulator:
    def __init__(
        self,
        transport: Transport,
        rules: RuleEngine,
        rx_end: bytes = b"\r\n",
        tx_end: bytes = b"\r\n",
    ) -> None:
        self.transport = transport
        self.rules = rules
        self.rx_end = rx_end
        self.tx_end = tx_end

    async def serve_once(self):
        msg = await self.transport.read_until(self.rx_end)
        log.debug("Received: %r", msg)
        rule = await self.rules.get_response(msg.rstrip(self.rx_end))
        if rule:
            await asyncio.sleep(rule.delay_ms / 1000)
            response = rule.response.encode() + (
                (rule.tx_end or self.tx_end.decode()).encode()
            )
            log.debug("Responding: %r", response)
            await self.transport.write(response)
        else:
            log.warning("No rule for %r", msg)

    async def run(self):
        await self.transport.open()
        try:
            while True:
                await self.serve_once()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            await self.transport.close()


###############################################################################
# CLI #########################################################################
###############################################################################


def _parse_args(argv: List[str]):
    p = argparse.ArgumentParser(description="Generic DTE Emulator")
    p.add_argument("--transport", choices=["serial", "tcp"], required=True)

    # Serial‑specific
    p.add_argument("--port", help="Serial port (e.g. COM3 or /dev/ttyUSB0)")
    p.add_argument("--baud", type=int, default=9600)

    # TCP‑specific
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--tcp-port", type=int, default=6000)

    p.add_argument("--rules", type=Path, required=True, help="Path to YAML rule file")
    p.add_argument("--rx-end", default="\r\n")
    p.add_argument("--tx-end", default="\r\n")
    return p.parse_args(argv)


def _build_transport(opts) -> Transport:
    if opts.transport == "serial":
        if not opts.port:
            raise SystemExit("--port is required for serial transport")
        return SerialTransport(opts.port, opts.baud)
    elif opts.transport == "tcp":
        return TCPTransport(opts.host, opts.tcp_port)
    else:
        raise ValueError("Unsupported transport")


def main(argv: List[str] | None = None):
    opts = _parse_args(argv or sys.argv[1:])
    transport = _build_transport(opts)
    rules = RuleEngine(opts.rules)

    emu = DTEEmulator(transport, rules, opts.rx_end.encode(), opts.tx_end.encode())

    try:
        asyncio.run(emu.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
