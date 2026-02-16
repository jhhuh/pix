"""Nix daemon Unix socket protocol client.

Connects to the Nix daemon at /nix/var/nix/daemon-socket/socket and
implements a subset of the worker protocol for store queries and builds.
"""

import os
import socket
import struct
from dataclasses import dataclass

# Protocol constants
WORKER_MAGIC_1 = 0x6E697863  # "nixc"
WORKER_MAGIC_2 = 0x6478696F  # "dxio"
PROTOCOL_VERSION = (1 << 8) | 37  # 1.37 — common in Nix 2.x

# Worker operations
WOP_IS_VALID_PATH = 1
WOP_QUERY_PATH_INFO = 26
WOP_ADD_TEXT_TO_STORE = 8
WOP_BUILD_PATHS = 9
WOP_ADD_TO_STORE_NAR = 39
WOP_QUERY_VALID_PATHS = 31

# Stderr message types from daemon
STDERR_NEXT = 0x6F6C6D67   # log line
STDERR_READ = 0x64617461   # read data (unused here)
STDERR_WRITE = 0x64617416  # write data
STDERR_LAST = 0x616C7473   # end of stderr
STDERR_ERROR = 0x63787470  # error
STDERR_START_ACTIVITY = 0x53545254
STDERR_STOP_ACTIVITY = 0x53544F50
STDERR_RESULT = 0x52534C54


@dataclass
class PathInfo:
    deriver: str
    nar_hash: str
    references: list[str]
    registration_time: int
    nar_size: int
    sigs: list[str]


class NixDaemonError(Exception):
    pass


class DaemonConnection:
    """Low-level connection to the Nix daemon."""

    def __init__(self, socket_path: str | None = None):
        self.socket_path = socket_path or "/nix/var/nix/daemon-socket/socket"
        self.sock: socket.socket | None = None
        self.daemon_version: int = 0

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        self._handshake()

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    # --- Wire format ---

    def _send_uint64(self, n: int) -> None:
        self.sock.sendall(struct.pack("<Q", n))

    def _recv_uint64(self) -> int:
        data = self._recv_exact(8)
        return struct.unpack("<Q", data)[0]

    def _send_bytes(self, data: bytes) -> None:
        self._send_uint64(len(data))
        self.sock.sendall(data)
        pad = (8 - len(data) % 8) % 8
        if pad:
            self.sock.sendall(b"\0" * pad)

    def _recv_bytes(self) -> bytes:
        length = self._recv_uint64()
        data = self._recv_exact(length)
        pad = (8 - length % 8) % 8
        if pad:
            self._recv_exact(pad)
        return data

    def _send_string(self, s: str) -> None:
        self._send_bytes(s.encode())

    def _recv_string(self) -> str:
        return self._recv_bytes().decode()

    def _send_string_list(self, lst: list[str]) -> None:
        self._send_uint64(len(lst))
        for s in lst:
            self._send_string(s)

    def _recv_string_list(self) -> list[str]:
        n = self._recv_uint64()
        return [self._recv_string() for _ in range(n)]

    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("daemon closed connection")
            buf.extend(chunk)
        return bytes(buf)

    def _send_bool(self, b: bool) -> None:
        self._send_uint64(1 if b else 0)

    def _recv_bool(self) -> bool:
        return self._recv_uint64() != 0

    # --- Handshake ---

    def _handshake(self) -> None:
        self._send_uint64(WORKER_MAGIC_1)
        magic = self._recv_uint64()
        if magic != WORKER_MAGIC_2:
            raise NixDaemonError(f"bad daemon magic: {magic:#x}")

        self.daemon_version = self._recv_uint64()

        # Send our protocol version
        self._send_uint64(PROTOCOL_VERSION)

        # Since protocol >= 1.14, we can send CPU affinity (0 = no override)
        self._send_uint64(0)

        # Since protocol >= 1.11, send reserve-space flag
        self._send_bool(False)

        # Since protocol >= 1.33, daemon sends its nix version string
        if self.daemon_version >= (1 << 8 | 33):
            self._recv_string()  # daemon nix version (e.g. "2.28.5")

        # Since protocol >= 1.35, daemon sends trusted status
        if self.daemon_version >= (1 << 8 | 35):
            self._recv_uint64()  # trusted (0=unknown, 1=trusted, 2=not trusted)

        # Drain startup messages
        self._drain_stderr()

    # --- Stderr draining ---

    def _drain_stderr(self) -> None:
        """Read and discard daemon stderr log messages until STDERR_LAST."""
        while True:
            msg_type = self._recv_uint64()
            if msg_type == STDERR_LAST:
                return
            elif msg_type == STDERR_ERROR:
                error_type = self._recv_string()
                _level = self._recv_uint64()
                _name = self._recv_string()
                msg = self._recv_string()
                # traces
                n_traces = self._recv_uint64()
                for _ in range(n_traces):
                    _trace_pos = self._recv_uint64()
                    _trace_msg = self._recv_string()
                raise NixDaemonError(f"{error_type}: {msg}")
            elif msg_type == STDERR_NEXT:
                _log = self._recv_string()
            elif msg_type == STDERR_START_ACTIVITY:
                _act_id = self._recv_uint64()
                _level = self._recv_uint64()
                _type = self._recv_uint64()
                _text = self._recv_string()
                _fields = self._recv_fields()
                _parent = self._recv_uint64()
            elif msg_type == STDERR_STOP_ACTIVITY:
                _act_id = self._recv_uint64()
            elif msg_type == STDERR_RESULT:
                _act_id = self._recv_uint64()
                _type = self._recv_uint64()
                _fields = self._recv_fields()
            else:
                raise NixDaemonError(f"unexpected stderr message type: {msg_type:#x}")

    def _recv_fields(self) -> list:
        n = self._recv_uint64()
        fields = []
        for _ in range(n):
            field_type = self._recv_uint64()
            if field_type == 0:
                fields.append(self._recv_uint64())
            elif field_type == 1:
                fields.append(self._recv_string())
            else:
                raise NixDaemonError(f"unknown field type: {field_type}")
        return fields

    # --- Operations ---

    def is_valid_path(self, path: str) -> bool:
        self._send_uint64(WOP_IS_VALID_PATH)
        self._send_string(path)
        self._drain_stderr()
        return self._recv_bool()

    def query_valid_paths(self, paths: list[str], substitute: bool = False) -> set[str]:
        self._send_uint64(WOP_QUERY_VALID_PATHS)
        self._send_string_list(paths)
        self._send_bool(substitute)
        self._drain_stderr()
        return set(self._recv_string_list())

    def query_path_info(self, path: str) -> PathInfo:
        self._send_uint64(WOP_QUERY_PATH_INFO)
        self._send_string(path)
        self._drain_stderr()

        valid = self._recv_bool()
        if not valid:
            raise NixDaemonError(f"path not valid: {path}")

        deriver = self._recv_string()
        nar_hash = self._recv_string()
        references = self._recv_string_list()
        registration_time = self._recv_uint64()
        nar_size = self._recv_uint64()

        # ultimate flag (since 1.16)
        _ultimate = self._recv_bool()
        sigs = self._recv_string_list()
        # content-address (since 1.25-ish)
        _ca = self._recv_string()

        return PathInfo(
            deriver=deriver,
            nar_hash=nar_hash,
            references=references,
            registration_time=registration_time,
            nar_size=nar_size,
            sigs=sigs,
        )

    def add_text_to_store(self, name: str, content: str, references: list[str] | None = None) -> str:
        refs = references or []
        self._send_uint64(WOP_ADD_TEXT_TO_STORE)
        self._send_string(name)
        self._send_string(content)
        self._send_string_list(refs)
        self._drain_stderr()
        return self._recv_string()

    def build_paths(self, paths: list[str], build_mode: int = 0) -> None:
        self._send_uint64(WOP_BUILD_PATHS)

        # Since protocol >= 1.30, paths are sent as DerivedPath serialization
        # For simplicity, send as string list (opaque paths or drv!out)
        self._send_string_list(paths)

        self._send_uint64(build_mode)  # bmNormal=0
        self._drain_stderr()
        self._recv_uint64()  # result (1 = success)
