"""Shared bootstrap seed constants and helpers for overlay experiments.

These are the real nixpkgs bootstrap derivation parameters, extracted from
pixpkgs/tests/test_bootstrap_hash.py. Stage0 of each experiment uses these
to produce hash-identical derivations verified against real nixpkgs.

The bootstrap chain:
    busybox (fixed-output fetchurl)
    tarball (fixed-output fetchurl)
    bootstrap_tools(busybox, tarball)  → unpacks tools
    stdenv(bootstrap_tools)            → stage0 stdenv
"""

import base64

from pixpkgs.drv import drv, Package

TARBALLS_BASE = (
    "http://tarballs.nixos.org/stdenv/x86_64-unknown-linux-gnu/"
    "82b583ba2ba2e5706b35dbe23f31362e62be2a9d"
)

FETCHURL_ENV_BASE = {
    "impureEnvVars": "http_proxy https_proxy ftp_proxy all_proxy no_proxy",
    "preferLocalBuild": "1",
}

UNPACK_SCRIPT = "/nix/store/i9nx0dp1khrgikqr95ryy2jkigr4c5yv-unpack-bootstrap-tools.sh"
BUILDER_SCRIPT = "/nix/store/cnss4bmvsa7kjmghgksgcadrxsvkyla1-builder.sh"
SETUP_SCRIPT = "/nix/store/qz36dkinx4pg0p2ry7dzj66s469awic2-setup.sh"

HOOK_SCRIPTS = [
    "/nix/store/0y5xmdb7qfvimjwbq7ibg1xdgkgjwqng-no-broken-symlinks.sh",
    "/nix/store/5yzw0vhkyszf2d179m0qfkgxmp5wjjx4-move-docs.sh",
    "/nix/store/85clx3b0xkdf58jn161iy80y5223ilbi-compress-man-pages.sh",
    "/nix/store/cickvswrvann041nqxb0rxilc46svw1n-prune-libtool-files.sh",
    "/nix/store/cmzya9irvxzlkh7lfy6i82gbp0saxqj3-multiple-outputs.sh",
    "/nix/store/cnss4bmvsa7kjmghgksgcadrxsvkyla1-builder.sh",
    "/nix/store/cv1d7p48379km6a85h4zp6kr86brh32q-audit-tmpdir.sh",
    "/nix/store/fyaryjvghbkpfnsyw97hb3lyb37s1pd6-move-lib64.sh",
    "/nix/store/kd4xwxjpjxi71jkm6ka0np72if9rm3y0-move-sbin.sh",
    "/nix/store/pag6l61paj1dc9sv15l7bm5c17xn5kyk-move-systemd-user-units.sh",
    "/nix/store/pilsssjjdxvdphlg2h19p0bfx5q0jzkn-strip.sh",
    "/nix/store/qz36dkinx4pg0p2ry7dzj66s469awic2-setup.sh",
    "/nix/store/wgrbkkaldkrlrni33ccvm3b6vbxzb656-make-symlinks-relative.sh",
    "/nix/store/x8c40nfigps493a07sdr2pm5s9j1cdc0-patch-shebangs.sh",
    "/nix/store/xyff06pkhki3qy1ls77w10s0v79c9il0-reproducible-builds.sh",
    "/nix/store/z7k98578dfzi6l3hsvbivzm7hfqlk0zc-set-source-date-epoch-to-latest.sh",
]

STAGE0_DEFAULT_NATIVE_BUILD_INPUTS = " ".join([
    "/nix/store/0y5xmdb7qfvimjwbq7ibg1xdgkgjwqng-no-broken-symlinks.sh",
    "/nix/store/cv1d7p48379km6a85h4zp6kr86brh32q-audit-tmpdir.sh",
    "/nix/store/85clx3b0xkdf58jn161iy80y5223ilbi-compress-man-pages.sh",
    "/nix/store/wgrbkkaldkrlrni33ccvm3b6vbxzb656-make-symlinks-relative.sh",
    "/nix/store/5yzw0vhkyszf2d179m0qfkgxmp5wjjx4-move-docs.sh",
    "/nix/store/fyaryjvghbkpfnsyw97hb3lyb37s1pd6-move-lib64.sh",
    "/nix/store/kd4xwxjpjxi71jkm6ka0np72if9rm3y0-move-sbin.sh",
    "/nix/store/pag6l61paj1dc9sv15l7bm5c17xn5kyk-move-systemd-user-units.sh",
    "/nix/store/cmzya9irvxzlkh7lfy6i82gbp0saxqj3-multiple-outputs.sh",
    "/nix/store/x8c40nfigps493a07sdr2pm5s9j1cdc0-patch-shebangs.sh",
    "/nix/store/cickvswrvann041nqxb0rxilc46svw1n-prune-libtool-files.sh",
    "/nix/store/xyff06pkhki3qy1ls77w10s0v79c9il0-reproducible-builds.sh",
    "/nix/store/z7k98578dfzi6l3hsvbivzm7hfqlk0zc-set-source-date-epoch-to-latest.sh",
    "/nix/store/pilsssjjdxvdphlg2h19p0bfx5q0jzkn-strip.sh",
])

STAGE0_PREHOOK = (
    "# Don't patch #!/interpreter because it leads to retained\n"
    "# dependencies on the bootstrapTools in the final stdenv.\n"
    "dontPatchShebangs=1\n"
    'export NIX_ENFORCE_PURITY="${NIX_ENFORCE_PURITY-1}"\n'
    'export NIX_ENFORCE_NO_NATIVE="${NIX_ENFORCE_NO_NATIVE-1}"\n'
    "\n"
)

BOOTSTRAP_TOOLS_ENV = {
    "hardeningUnsupportedFlags": (
        "fortify3 shadowstack pacret stackclashprotection "
        "trivialautovarinit zerocallusedregs"
    ),
    "isGNU": "1",
    "langC": "1",
    "langCC": "1",
}

# Expected hashes from real nixpkgs (Nix 2.28, nixpkgs master)
EXPECTED = {
    "busybox.drv": "/nix/store/0m4y3j4pnivlhhpr5yqdvlly86p93fwc-busybox.drv",
    "busybox.out": "/nix/store/p9wzypb84a60ymqnhqza17ws0dvlyprg-busybox",
    "tarball.drv": "/nix/store/xjkydxc0n24mwxp8kh4wn5jq0fppga9k-bootstrap-tools.tar.xz.drv",
    "tarball.out": "/nix/store/2pizl7lq4awa7p9bklr8037yh1sca0hg-bootstrap-tools.tar.xz",
    "bootstrap_tools.drv": "/nix/store/05q48dcd4lgk4vh7wyk330gr2fr082i2-bootstrap-tools.drv",
    "bootstrap_tools.out": "/nix/store/razasrvdg7ckplfmvdxv4ia3wbayr94s-bootstrap-tools",
    "stdenv.drv": "/nix/store/ydld0fh638kgppqrfx30fr205wiab9ja-bootstrap-stage0-stdenv-linux.drv",
    "stdenv.out": "/nix/store/ajrdf015k5ipn89gyh06isniabysrkcw-bootstrap-stage0-stdenv-linux",
}

BUSYBOX_HASH = "42b4c49d04c133563fa95f6876af22ad9910483f6e38c6ecd90e4d802bca08d4"
TARBALL_HASH = "61096bd3cf073e8556054da3a4f86920cc8eca81036580f0d72eb448619b50cd"


def fetchurl(name, url, output_hash, *, recursive=False, executable=False):
    """Create a fixed-output fetchurl derivation matching Nix's builtin:fetchurl."""
    mode = "recursive" if recursive else "flat"
    hash_bytes = bytes.fromhex(output_hash)
    sri = "sha256-" + base64.b64encode(hash_bytes).decode()
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


def make_bootstrap_tools_drv(bb: Package, tb: Package, env_overrides=None):
    """Create a bootstrap-tools derivation. Used by overlay experiments."""
    env = {**BOOTSTRAP_TOOLS_ENV, "tarball": str(tb)}
    if env_overrides:
        env.update(env_overrides)
    return drv(
        name="bootstrap-tools",
        builder=str(bb),
        system="x86_64-linux",
        args=["ash", "-e", UNPACK_SCRIPT],
        deps=[bb, tb],
        srcs=[UNPACK_SCRIPT],
        env=env,
    )


def make_stdenv_drv(bt: Package, env_overrides=None):
    """Create a stage0-stdenv derivation. Used by overlay experiments."""
    bt_path = str(bt)
    env = {
        "defaultBuildInputs": "",
        "defaultNativeBuildInputs": STAGE0_DEFAULT_NATIVE_BUILD_INPUTS,
        "disallowedRequisites": "",
        "initialPath": bt_path,
        "preHook": STAGE0_PREHOOK,
        "setup": SETUP_SCRIPT,
        "shell": f"{bt_path}/bin/bash",
    }
    if env_overrides:
        env.update(env_overrides)
    return drv(
        name="bootstrap-stage0-stdenv-linux",
        builder=f"{bt_path}/bin/bash",
        system="x86_64-linux",
        args=["-e", BUILDER_SCRIPT],
        deps=[bt],
        srcs=HOOK_SCRIPTS,
        env=env,
    )
