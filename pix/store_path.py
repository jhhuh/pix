"""Nix store path computation.

A store path is: /nix/store/<hash>-<name>

The <hash> is 32 characters of Nix base32, encoding 160 bits (20 bytes).
It's computed by:
  1. Building a fingerprint string: "<type>:sha256:<hex(inner_hash)>:/nix/store:<name>"
  2. SHA-256 hashing the fingerprint
  3. XOR-folding the 32-byte hash down to 20 bytes
  4. Nix-base32 encoding the result

The <type> prefix determines what kind of store object this is:
  "text"         — builtins.toFile, pkgs.writeText (inner hash = sha256 of content)
  "source"       — path imports, filterSource (inner hash = sha256 of NAR)
  "output:<name>"— derivation outputs (inner hash = hashDerivationModulo result)

References (other store paths this object depends on) are appended to
the type with ':' separators. When there are no references, the type
has NO trailing colon — "text" not "text:".

See: nix/src/libstore/store-api.cc — makeStorePath(), makeTextPath()
"""

from pix.base32 import encode as b32encode
from pix.hash import compress_hash, sha256, sha256_hex

STORE_DIR = "/nix/store"
HASH_BYTES = 20  # 160 bits, XOR-folded (not truncated)


def make_store_path(type_prefix: str, inner_hash: bytes, name: str) -> str:
    """Core store path computation. Most callers use the typed helpers below."""
    fingerprint = f"{type_prefix}:sha256:{inner_hash.hex()}:{STORE_DIR}:{name}"
    compressed = compress_hash(sha256(fingerprint.encode()), HASH_BYTES)
    return f"{STORE_DIR}/{b32encode(compressed)}-{name}"


def _make_type(base: str, refs: list[str]) -> str:
    """Build a type string with sorted references appended.

    Important: no trailing colon when refs is empty.
    "text" + [] → "text"       (correct)
    "text" + [] → "text:"      (WRONG — would produce different hash)
    "text" + ["/nix/store/x"]  → "text:/nix/store/x"
    """
    t = base
    for r in sorted(refs):
        t += ":" + r
    return t


def make_text_store_path(name: str, content: bytes, references: list[str] | None = None) -> str:
    """Store path for text content (builtins.toFile, writeText).

    Inner hash is sha256 of the raw content bytes, NOT the NAR hash.
    """
    type_prefix = _make_type("text", references or [])
    inner_hash = sha256(content)
    return make_store_path(type_prefix, inner_hash, name)


def make_source_store_path(name: str, nar_hash: bytes, references: list[str] | None = None) -> str:
    """Store path for a source import (builtins.path, filterSource, ./foo).

    Inner hash is sha256 of the NAR serialization of the path.
    """
    type_prefix = _make_type("source", references or [])
    return make_store_path(type_prefix, nar_hash, name)


def make_fixed_output_path(
    name: str,
    hash_algo: str,
    content_hash: bytes,
    recursive: bool = False,
) -> str:
    """Store path for fixed-output derivation results (fetchurl, fetchgit).

    Special case: recursive + sha256 is treated as a source path directly
    (same computation as make_source_store_path). This is because the NAR
    hash of a recursively-hashed path IS the source hash.
    For other combinations, an intermediate hash is computed first.
    """
    method = "r:" if recursive else ""
    if recursive and hash_algo == "sha256":
        return make_store_path("source", content_hash, name)
    inner_desc = f"fixed:out:{method}{hash_algo}:{content_hash.hex()}:"
    inner_hash = sha256(inner_desc.encode())
    return make_store_path("output:out", inner_hash, name)


def path_to_store_path(path: str, name: str | None = None) -> str:
    """Compute the store path for a local file or directory.

    Like ``nix-store --add`` or ``builtins.path`` — NAR-serializes the path,
    hashes it, and computes the /nix/store/... path without touching the daemon.

    Args:
        path: Local filesystem path to hash.
        name: Nix store name (defaults to the basename of path).
    """
    from pathlib import Path as P

    from pix.nar import nar_hash as _nar_hash

    p = P(path)
    h = _nar_hash(str(p))
    return make_source_store_path(name or p.name, h)


def placeholder(output_name: str) -> str:
    """Nix's ``builtins.placeholder`` — a deterministic marker for output paths.

    Returns "/" + nix-base32(sha256("nix-output:" + output_name)).
    Used in env vars that need the output path at eval time (e.g. configureFlags
    with -Dprefix). The drv() pipeline replaces these markers with actual output
    paths after hashDerivationModulo is computed.

    See: nix/src/libstore/store-api.cc — hashPlaceholder()
    """
    inner = sha256(f"nix-output:{output_name}".encode())
    return "/" + b32encode(inner)


def make_output_path(drv_hash: bytes, output_name: str, name: str) -> str:
    """Store path for a derivation output.

    drv_hash comes from hash_derivation_modulo() in derivation.py.
    The "out" output uses the base name; other outputs append "-<output>":
      "out" → "zlib-1.3.1"
      "dev" → "zlib-1.3.1-dev"
    """
    type_prefix = f"output:{output_name}"
    path_name = name if output_name == "out" else f"{name}-{output_name}"
    return make_store_path(type_prefix, drv_hash, path_name)
