"""Verify that drv() produces derivations matching real nixpkgs bootstrap.

Each test constructs a derivation using drv() with the same parameters as
the real nixpkgs bootstrap chain, then checks that the .drv path and output
path match exactly. This validates our entire hash pipeline:
  hash_derivation_modulo → make_output_path → make_text_store_path

The expected hashes come from: nix eval nixpkgs#stdenv (Nix 2.28, nixpkgs master)
"""

import subprocess
import pytest
from pix.derivation import parse, serialize
from pixpkgs.drv import drv, Package

# --- Bootstrap seed: two fixed-output fetches + unpack ---

TARBALLS_BASE = (
    "http://tarballs.nixos.org/stdenv/x86_64-unknown-linux-gnu/"
    "82b583ba2ba2e5706b35dbe23f31362e62be2a9d"
)

FETCHURL_ENV_BASE = {
    "impureEnvVars": "http_proxy https_proxy ftp_proxy all_proxy no_proxy",
    "preferLocalBuild": "1",
}


def _fetchurl(name, url, output_hash, *, recursive=False, executable=False):
    """Create a fixed-output fetchurl derivation matching Nix's builtin:fetchurl."""
    mode = "recursive" if recursive else "flat"
    # Nix stores the SRI hash in env.outputHash; we need to compute it
    import base64
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


def busybox():
    return _fetchurl(
        "busybox",
        f"{TARBALLS_BASE}/busybox",
        "42b4c49d04c133563fa95f6876af22ad9910483f6e38c6ecd90e4d802bca08d4",
        recursive=True,
        executable=True,
    )


def tarball():
    return _fetchurl(
        "bootstrap-tools.tar.xz",
        f"{TARBALLS_BASE}/bootstrap-tools.tar.xz",
        "61096bd3cf073e8556054da3a4f86920cc8eca81036580f0d72eb448619b50cd",
    )


def bootstrap_tools(bb: Package, tb: Package):
    return drv(
        name="bootstrap-tools",
        builder=str(bb),
        system="x86_64-linux",
        args=["ash", "-e", "/nix/store/i9nx0dp1khrgikqr95ryy2jkigr4c5yv-unpack-bootstrap-tools.sh"],
        deps=[bb, tb],
        srcs=["/nix/store/i9nx0dp1khrgikqr95ryy2jkigr4c5yv-unpack-bootstrap-tools.sh"],
        env={
            "hardeningUnsupportedFlags": "fortify3 shadowstack pacret stackclashprotection trivialautovarinit zerocallusedregs",
            "isGNU": "1",
            "langC": "1",
            "langCC": "1",
            "tarball": str(tb),
        },
    )


# --- Stage 0: minimal stdenv ---

# 16 shell scripts used as inputSrcs in stage0-stdenv
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


def stage0_stdenv(bt: Package):
    bt_path = str(bt)
    return drv(
        name="bootstrap-stage0-stdenv-linux",
        builder=f"{bt_path}/bin/bash",
        system="x86_64-linux",
        args=["-e", "/nix/store/cnss4bmvsa7kjmghgksgcadrxsvkyla1-builder.sh"],
        deps=[bt],
        srcs=HOOK_SCRIPTS,
        env={
            "defaultBuildInputs": "",
            "defaultNativeBuildInputs": STAGE0_DEFAULT_NATIVE_BUILD_INPUTS,
            "disallowedRequisites": "",
            "initialPath": bt_path,
            "preHook": STAGE0_PREHOOK,
            "setup": "/nix/store/qz36dkinx4pg0p2ry7dzj66s469awic2-setup.sh",
            "shell": f"{bt_path}/bin/bash",
        },
    )


# --- Tests ---

class TestBootstrapSeed:
    def test_busybox(self):
        bb = busybox()
        assert bb.drv_path == "/nix/store/0m4y3j4pnivlhhpr5yqdvlly86p93fwc-busybox.drv"
        assert bb.out == "/nix/store/p9wzypb84a60ymqnhqza17ws0dvlyprg-busybox"

    def test_tarball(self):
        tb = tarball()
        assert tb.drv_path == "/nix/store/xjkydxc0n24mwxp8kh4wn5jq0fppga9k-bootstrap-tools.tar.xz.drv"
        assert tb.out == "/nix/store/2pizl7lq4awa7p9bklr8037yh1sca0hg-bootstrap-tools.tar.xz"

    def test_bootstrap_tools(self):
        bb = busybox()
        tb = tarball()
        bt = bootstrap_tools(bb, tb)
        assert bt.drv_path == "/nix/store/05q48dcd4lgk4vh7wyk330gr2fr082i2-bootstrap-tools.drv"
        assert bt.out == "/nix/store/razasrvdg7ckplfmvdxv4ia3wbayr94s-bootstrap-tools"

    def test_bootstrap_tools_aterm_matches(self):
        """The full ATerm text must be byte-identical to the real .drv."""
        bb = busybox()
        tb = tarball()
        bt = bootstrap_tools(bb, tb)
        expected = open("/nix/store/05q48dcd4lgk4vh7wyk330gr2fr082i2-bootstrap-tools.drv").read()
        assert serialize(bt.drv) == expected


class TestStage0:
    def test_stage0_stdenv(self):
        bb = busybox()
        tb = tarball()
        bt = bootstrap_tools(bb, tb)
        s0 = stage0_stdenv(bt)
        assert s0.drv_path == "/nix/store/ydld0fh638kgppqrfx30fr205wiab9ja-bootstrap-stage0-stdenv-linux.drv"
        assert s0.out == "/nix/store/ajrdf015k5ipn89gyh06isniabysrkcw-bootstrap-stage0-stdenv-linux"

    def test_stage0_aterm_matches(self):
        """The full ATerm text must be byte-identical to the real .drv."""
        bb = busybox()
        tb = tarball()
        bt = bootstrap_tools(bb, tb)
        s0 = stage0_stdenv(bt)
        expected = open("/nix/store/ydld0fh638kgppqrfx30fr205wiab9ja-bootstrap-stage0-stdenv-linux.drv").read()
        assert serialize(s0.drv) == expected


# --- Full chain: all 196 derivations from seed to hello ---

def _make_package_from_drv(drv_path, dep_packages):
    """Read a .drv file and reconstruct a matching Package using drv()."""
    drv_text = open(drv_path).read()
    parsed = parse(drv_text)
    is_fixed = (len(parsed.outputs) == 1 and "out" in parsed.outputs
                and parsed.outputs["out"].hash_algo != "")
    name = drv_path.rsplit("/", 1)[1].split("-", 1)[1][:-4]
    deps = [dep_packages[dp] for dp in sorted(parsed.input_drvs) if dp in dep_packages]
    env = dict(parsed.env)
    for k in {"name", "builder", "system"}:
        env.pop(k, None)
    for oname in parsed.outputs:
        env.pop(oname, None)
    kwargs = dict(
        name=name, builder=parsed.builder, system=parsed.platform,
        args=parsed.args if parsed.args else None,
        env=env if env else None,
        output_names=sorted(parsed.outputs) if sorted(parsed.outputs) != ["out"] else None,
        deps=deps if deps else None,
        srcs=parsed.input_srcs if parsed.input_srcs else None,
        input_drvs={dp: outs for dp, outs in parsed.input_drvs.items()},
    )
    if is_fixed:
        o = parsed.outputs["out"]
        algo = o.hash_algo
        if algo.startswith("r:"):
            kwargs["output_hash_mode"] = "recursive"
            algo = algo[2:]
        else:
            kwargs["output_hash_mode"] = "flat"
        kwargs["output_hash_algo"] = algo
        kwargs["output_hash"] = o.hash_value
    return drv(**kwargs)


class TestFullChain:
    def test_all_196_derivations_match_hello_closure(self):
        """Reconstruct every derivation in nixpkgs#hello's closure and verify
        byte-identical ATerm output — validates the entire hash pipeline."""
        hello_drv = subprocess.run(
            ["nix", "eval", "nixpkgs#hello.drvPath", "--raw"],
            capture_output=True, text=True,
        ).stdout
        all_drvs = [
            l for l in subprocess.run(
                ["nix-store", "--query", "--requisites", hello_drv],
                capture_output=True, text=True,
            ).stdout.strip().split("\n")
            if l.endswith(".drv")
        ]
        assert len(all_drvs) > 100, f"Expected 100+ derivations, got {len(all_drvs)}"

        packages = {}
        failures = []
        for drv_path in all_drvs:
            try:
                pkg = _make_package_from_drv(drv_path, packages)
                actual = serialize(pkg.drv)
                expected = open(drv_path).read()
                if actual == expected:
                    packages[drv_path] = pkg
                else:
                    name = drv_path.rsplit("/", 1)[1]
                    failures.append(f"ATerm mismatch: {name}")
            except Exception as e:
                name = drv_path.rsplit("/", 1)[1]
                failures.append(f"{name}: {e}")

        assert not failures, (
            f"{len(failures)}/{len(all_drvs)} derivations failed:\n"
            + "\n".join(failures[:10])
        )
