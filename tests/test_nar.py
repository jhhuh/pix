"""Tests for NAR serialization."""

import base64
import hashlib
import os
import struct
import tempfile
from pathlib import Path

from pix.nar import nar_serialize, nar_hash, nar_hash_hex


# From: nix hash path /tmp/pix-test-hello.txt (file containing "hello", no newline)
# sha256-CkMIecJm+LV/QJKg+TXPP6zUi7zN5XYNR0jKQFFx6Wk=
HELLO_NAR_HASH_B64 = "CkMIecJm+LV/QJKg+TXPP6zUi7zN5XYNR0jKQFFx6Wk="
HELLO_NAR_HASH = base64.b64decode(HELLO_NAR_HASH_B64)


def _str(s: str | bytes) -> bytes:
    """NAR string encoding helper for building expected output."""
    if isinstance(s, str):
        s = s.encode()
    pad = (8 - len(s) % 8) % 8
    return struct.pack("<Q", len(s)) + s + b"\0" * pad


def test_regular_file():
    """NAR of a regular file containing 'hello'."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello")
        f.flush()
        path = f.name

    try:
        nar = nar_serialize(path)

        expected = (
            _str("nix-archive-1")
            + _str("(")
            + _str("type")
            + _str("regular")
            + _str("contents")
            + _str("hello")
            + _str(")")
        )
        assert nar == expected
        assert hashlib.sha256(nar).digest() == HELLO_NAR_HASH
    finally:
        os.unlink(path)


def test_nar_hash_matches_nix():
    """nar_hash matches `nix hash path` output."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello")
        f.flush()
        path = f.name

    try:
        assert nar_hash(path) == HELLO_NAR_HASH
    finally:
        os.unlink(path)


def test_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        path = f.name

    try:
        nar = nar_serialize(path)
        expected = (
            _str("nix-archive-1")
            + _str("(")
            + _str("type")
            + _str("regular")
            + _str("contents")
            + _str(b"")
            + _str(")")
        )
        assert nar == expected
    finally:
        os.unlink(path)


def test_directory():
    with tempfile.TemporaryDirectory() as d:
        Path(d, "a.txt").write_text("aaa")
        Path(d, "b.txt").write_text("bbb")

        nar = nar_serialize(d)

        # Should contain directory type and sorted entries
        assert _str("directory") in nar
        # 'a.txt' should come before 'b.txt'
        pos_a = nar.index(_str("a.txt"))
        pos_b = nar.index(_str("b.txt"))
        assert pos_a < pos_b


def test_symlink():
    with tempfile.TemporaryDirectory() as d:
        target = Path(d, "target.txt")
        target.write_text("data")
        link = Path(d, "link")
        link.symlink_to("target.txt")

        nar = nar_serialize(str(link))
        assert _str("symlink") in nar
        assert _str("target.txt") in nar


def test_executable_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write("#!/bin/sh\n")
        path = f.name

    try:
        os.chmod(path, 0o755)
        nar = nar_serialize(path)
        assert _str("executable") in nar
    finally:
        os.unlink(path)
