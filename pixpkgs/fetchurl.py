"""Fixed-output fetchurl derivation. Python equivalent of <nix/fetchurl.nix>.

Nix bundles a special fetchurl that uses ``builtin:fetchurl`` — a builder
implemented inside the Nix daemon itself (no sandbox, no coreutils needed).
It's the only way to bootstrap: you can't build a downloader before you
have a downloader.

Usage::

    from pixpkgs.fetchurl import fetchurl

    src = fetchurl(
        "hello-2.12.2.tar.gz",
        "https://ftp.gnu.org/gnu/hello/hello-2.12.2.tar.gz",
        "cf04af86dc085268c5f4470fbae49b18afbc221b78096aab842d934a76bad0ab",
    )
"""

import base64

from pixpkgs.drv import Package, drv

FETCHURL_ENV_BASE = {
    "impureEnvVars": "http_proxy https_proxy ftp_proxy all_proxy no_proxy",
    "preferLocalBuild": "1",
}


def fetchurl(name: str, url: str, output_hash: str, *,
             recursive: bool = False, executable: bool = False) -> Package:
    """Fixed-output fetchurl derivation. Matches Nix's builtin:fetchurl.

    Like ``<nix/fetchurl.nix>`` bundled with Nix. The ``builtin:fetchurl``
    builder runs inside the daemon — no sandbox, no coreutils.

    Args:
        name: Derivation name (e.g. "hello-2.12.2.tar.gz").
        url: URL to fetch.
        output_hash: SHA-256 hex digest of the expected output.
        recursive: If True, output is a directory (NAR hash). If False, flat file hash.
        executable: If True, mark the output as executable.
    """
    mode = "recursive" if recursive else "flat"
    sri = "sha256-" + base64.b64encode(bytes.fromhex(output_hash)).decode()
    return drv(
        name=name,
        builder="builtin:fetchurl",
        system="builtin",
        output_hash=output_hash,
        output_hash_algo="sha256",
        output_hash_mode=mode,
        env={
            **FETCHURL_ENV_BASE,
            "executable": "1" if executable else "",
            "outputHash": sri,
            "outputHashAlgo": "",
            "outputHashMode": mode,
            "unpack": "",
            "url": url,
            "urls": url,
        },
    )
