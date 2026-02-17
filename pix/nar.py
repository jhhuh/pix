"""NAR (Nix Archive) serialization and hashing.

NAR is Nix's deterministic archive format. Unlike tar:
- No timestamps, uid/gid, or permission modes (only executable bit)
- Directory entries are sorted, so the same tree always serializes identically
- Symlinks are stored as-is (not resolved)

This makes NAR suitable as a content-addressing mechanism: identical filesystem
content always produces the identical byte stream, and thus the same hash.

Wire format: every value (keywords, names, file contents) is encoded as:
    uint64_le(length) + raw bytes + zero-padding to 8-byte boundary

Grammar (where str(x) is the wire encoding above):
    str("nix-archive-1")
    str("(") str("type")
      str("regular") [str("executable") str("")] str("contents") str(<data>)
    | str("symlink") str("target") str(<target>)
    | str("directory") { str("entry") str("(") str("name") str(<n>) str("node") <recurse> str(")") }
    str(")")

See: nix/src/libutil/archive.cc — dump(), dumpContents()
"""

import hashlib
import os
import struct
from pathlib import Path


def _pad8(n: int) -> int:
    """Bytes of zero-padding needed to reach 8-byte alignment."""
    r = n % 8
    return (8 - r) % 8


def _str(s: str | bytes) -> bytes:
    """Encode a value in NAR wire format: uint64_le length + data + pad."""
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
        # NAR only preserves the executable bit — all other permission
        # bits, ownership, and timestamps are discarded for reproducibility.
        if os.access(path, os.X_OK):
            parts.append(_str("executable"))
            parts.append(_str(""))
        parts.append(_str("contents"))
        data = path.read_bytes()
        parts.append(_str(data))

    elif path.is_dir():
        parts.append(_str("type"))
        parts.append(_str("directory"))
        # Entries MUST be sorted — this is what makes NAR deterministic.
        # Without sorting, directory enumeration order would vary by
        # filesystem and OS, producing different hashes for identical content.
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
    """SHA-256 of the NAR serialization. This is what `nix hash path` computes."""
    return hashlib.sha256(nar_serialize(path)).digest()


def nar_hash_hex(path: str | Path) -> str:
    """SHA-256 of the NAR serialization, as hex."""
    return hashlib.sha256(nar_serialize(path)).hexdigest()
