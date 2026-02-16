"""NAR (Nix Archive) serialization and hashing.

NAR format:
- Strings: uint64-le length + bytes + zero-padding to 8-byte boundary
- Regular file: ( type regular [executable ""] contents <data> )
- Symlink: ( type symlink target <target> )
- Directory: ( type directory [entry ( name <name> node <recurse> ) ...] )
  Directory entries are sorted by name.
"""

import hashlib
import os
import struct
from pathlib import Path


def _pad8(n: int) -> int:
    """Bytes of padding needed to reach 8-byte alignment."""
    r = n % 8
    return (8 - r) % 8


def _str(s: str | bytes) -> bytes:
    """Serialize a string in NAR format (length-prefixed, 8-byte padded)."""
    if isinstance(s, str):
        s = s.encode()
    return struct.pack("<Q", len(s)) + s + b"\0" * _pad8(len(s))


def nar_serialize(path: str | Path) -> bytes:
    """Serialize a filesystem path to NAR bytes."""
    parts: list[bytes] = []
    _serialize(Path(path), parts)
    return b"".join(parts)


def _serialize(path: Path, parts: list[bytes]) -> None:
    parts.append(_str("nix-archive-1"))
    _serialize_entry(path, parts)


def _serialize_entry(path: Path, parts: list[bytes]) -> None:
    parts.append(_str("("))

    if path.is_symlink():
        parts.append(_str("type"))
        parts.append(_str("symlink"))
        parts.append(_str("target"))
        parts.append(_str(os.readlink(path)))

    elif path.is_file():
        parts.append(_str("type"))
        parts.append(_str("regular"))
        if os.access(path, os.X_OK):
            parts.append(_str("executable"))
            parts.append(_str(""))
        parts.append(_str("contents"))
        data = path.read_bytes()
        parts.append(_str(data))

    elif path.is_dir():
        parts.append(_str("type"))
        parts.append(_str("directory"))
        for entry_name in sorted(os.listdir(path)):
            parts.append(_str("entry"))
            parts.append(_str("("))
            parts.append(_str("name"))
            parts.append(_str(entry_name))
            parts.append(_str("node"))
            _serialize_entry(path / entry_name, parts)
            parts.append(_str(")"))
    else:
        raise ValueError(f"unsupported file type: {path}")

    parts.append(_str(")"))


def nar_hash(path: str | Path) -> bytes:
    """Compute SHA-256 hash of the NAR serialization of a path."""
    return hashlib.sha256(nar_serialize(path)).digest()


def nar_hash_hex(path: str | Path) -> str:
    """Compute SHA-256 hash of the NAR serialization of a path, as hex."""
    return hashlib.sha256(nar_serialize(path)).hexdigest()
