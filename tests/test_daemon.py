"""Tests for daemon connection (require running Nix daemon)."""

import os
import socket
import pytest

from pix.daemon import DaemonConnection, NixDaemonError

SOCKET_PATH = "/nix/var/nix/daemon-socket/socket"


def daemon_available() -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SOCKET_PATH)
        s.close()
        return True
    except (FileNotFoundError, ConnectionRefusedError, PermissionError):
        return False


needs_daemon = pytest.mark.skipif(
    not daemon_available(),
    reason="Nix daemon not available",
)


@needs_daemon
def test_connect():
    with DaemonConnection() as conn:
        assert conn.daemon_version > 0


@needs_daemon
def test_is_valid_path_invalid():
    with DaemonConnection() as conn:
        assert not conn.is_valid_path("/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-nonexistent")


@needs_daemon
def test_is_valid_path_valid():
    """Test with a path we add ourselves."""
    with DaemonConnection() as conn:
        path = conn.add_text_to_store("pix-valid-test.txt", "valid test")
        assert conn.is_valid_path(path)


@needs_daemon
def test_add_text_to_store():
    with DaemonConnection() as conn:
        path = conn.add_text_to_store("pix-test.txt", "hello from pix")
        assert path.startswith("/nix/store/")
        assert path.endswith("-pix-test.txt")
        # Verify it's now valid
        assert conn.is_valid_path(path)


@needs_daemon
def test_query_path_info():
    with DaemonConnection() as conn:
        # First add something so we know it exists
        path = conn.add_text_to_store("pix-query-test.txt", "test content")
        info = conn.query_path_info(path)
        assert info.nar_size > 0
        assert len(info.nar_hash) > 0
