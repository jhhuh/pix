"""Nix store path computation.

A store path is /nix/store/<hash>-<name> where <hash> is a 160-bit
(20-byte) truncated hash encoded in Nix base32 (32 chars).

The fingerprint is:
    <type>:sha256:<inner-hash-hex>:/nix/store:<name>

where <type> depends on the kind of store object.
"""

from pix.base32 import encode as b32encode
from pix.hash import compress_hash, sha256, sha256_hex

STORE_DIR = "/nix/store"
HASH_BYTES = 20  # 160 bits, truncated via XOR-fold


def make_store_path(type_prefix: str, inner_hash: bytes, name: str) -> str:
    """Compute a store path from a type prefix, inner hash, and name.

    The fingerprint hashed is: <type>:sha256:<hex(inner_hash)>:/nix/store:<name>
    """
    fingerprint = f"{type_prefix}:sha256:{inner_hash.hex()}:{STORE_DIR}:{name}"
    compressed = compress_hash(sha256(fingerprint.encode()), HASH_BYTES)
    return f"{STORE_DIR}/{b32encode(compressed)}-{name}"


def _make_type(base: str, refs: list[str]) -> str:
    """Build a type string, appending sorted references with ':' separators."""
    t = base
    for r in sorted(refs):
        t += ":" + r
    return t


def make_text_store_path(name: str, content: bytes, references: list[str] | None = None) -> str:
    """Store path for a text file added to the store (like writeText)."""
    type_prefix = _make_type("text", references or [])
    inner_hash = sha256(content)
    return make_store_path(type_prefix, inner_hash, name)


def make_source_store_path(name: str, nar_hash: bytes, references: list[str] | None = None) -> str:
    """Store path for a source directory (like filterSource/path import)."""
    type_prefix = _make_type("source", references or [])
    return make_store_path(type_prefix, nar_hash, name)


def make_fixed_output_path(
    name: str,
    hash_algo: str,
    content_hash: bytes,
    recursive: bool = False,
) -> str:
    """Store path for a fixed-output derivation result."""
    method = "r:" if recursive else ""
    # For recursive sha256, the path is computed directly
    if recursive and hash_algo == "sha256":
        return make_store_path("source", content_hash, name)
    # Otherwise, compute an intermediate hash
    inner_desc = f"fixed:out:{method}{hash_algo}:{content_hash.hex()}:"
    inner_hash = sha256(inner_desc.encode())
    return make_store_path("output:out", inner_hash, name)


def make_output_path(drv_hash: bytes, output_name: str, name: str) -> str:
    """Store path for a derivation output, given the derivation hash."""
    type_prefix = f"output:{output_name}"
    return make_store_path(type_prefix, drv_hash, name)
