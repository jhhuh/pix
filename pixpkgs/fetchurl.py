"""Fixed-output fetchurl derivation. Python equivalent of <nix/fetchurl.nix>.

Nix bundles a special fetchurl that uses ``builtin:fetchurl`` — a builder
implemented inside the Nix daemon itself (no sandbox, no coreutils needed).
It's the only way to bootstrap: you can't build a downloader before you
have a downloader.

Three hash attribute styles exist in nixpkgs, producing different .drv bytes:

1. ``hash = "sha256-<base64>"`` → outputHash=SRI, outputHashAlgo=""
2. ``sha256 = "sha256-<base64>"`` → outputHash=SRI, outputHashAlgo="sha256"
3. ``sha256 = "<nix32>"`` → outputHash=nix32, outputHashAlgo="sha256"

Use ``fetchurl()`` for style 1, ``fetchurl_sha256()`` for style 2,
and ``fetchurl_nix32()`` for style 3.
"""

import base64

from pix.base32 import decode as nix32_decode
from pixpkgs.drv import Package, drv

FETCHURL_ENV_BASE = {
    "impureEnvVars": "http_proxy https_proxy ftp_proxy all_proxy no_proxy",
    "preferLocalBuild": "1",
}


def _make_fetchurl(name: str, url: str, hex_hash: str,
                   env_hash: str, env_algo: str,
                   mode: str, executable: bool) -> Package:
    """Internal: create a builtin:fetchurl derivation."""
    return drv(
        name=name,
        builder="builtin:fetchurl",
        system="builtin",
        output_hash=hex_hash,
        output_hash_algo="sha256",
        output_hash_mode=mode,
        env={
            **FETCHURL_ENV_BASE,
            "executable": "1" if executable else "",
            "outputHash": env_hash,
            "outputHashAlgo": env_algo,
            "outputHashMode": mode,
            "unpack": "",
            "url": url,
            "urls": url,
        },
    )


def _sri(hex_hash: str) -> str:
    return "sha256-" + base64.b64encode(bytes.fromhex(hex_hash)).decode()


def fetchurl(name: str, url: str, output_hash: str, *,
             recursive: bool = False, executable: bool = False) -> Package:
    """Fetchurl matching nixpkgs ``hash = "sha256-<base64>"``.

    outputHashAlgo="" (algo embedded in SRI string).
    """
    mode = "recursive" if recursive else "flat"
    return _make_fetchurl(name, url, output_hash,
                          _sri(output_hash), "", mode, executable)


def fetchurl_sha256(name: str, url: str, output_hash: str, *,
                    recursive: bool = False, executable: bool = False) -> Package:
    """Fetchurl matching nixpkgs ``sha256 = "sha256-<base64>"``.

    Same SRI string in env, but outputHashAlgo="sha256".
    Used when package authors write ``sha256 = "sha256-..."`` instead of ``hash = "sha256-..."``.
    """
    mode = "recursive" if recursive else "flat"
    return _make_fetchurl(name, url, output_hash,
                          _sri(output_hash), "sha256", mode, executable)


def fetchurl_nix32(name: str, url: str, nix32_hash: str, *,
                   recursive: bool = False, executable: bool = False) -> Package:
    """Fetchurl matching nixpkgs ``sha256 = "<nix32>"``.

    Nix32 string in env, outputHashAlgo="sha256".
    """
    hex_hash = nix32_decode(nix32_hash).hex()
    mode = "recursive" if recursive else "flat"
    return _make_fetchurl(name, url, hex_hash,
                          nix32_hash, "sha256", mode, executable)
