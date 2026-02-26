"""Source tarballs for xgcc dependency tree.

All source tarballs are fixed-output fetchurl derivations with 0 dependencies.
Three hash styles match the three nixpkgs conventions:
  - fetchurl(): hash = "sha256-<base64>" → outputHashAlgo=""
  - fetchurl_sha256(): sha256 = "sha256-<base64>" → outputHashAlgo="sha256"
  - fetchurl_nix32(): sha256 = "<nix32>" → outputHashAlgo="sha256"
"""

from pixpkgs.drv import Package
from pixpkgs.fetchurl import fetchurl, fetchurl_nix32, fetchurl_sha256

# --- Style 1: fetchurl() — SRI hash, outputHashAlgo="" ---


def which_src() -> Package:
    return fetchurl(
        "which-2.23.tar.gz",
        "https://ftpmirror.gnu.org/which/which-2.23.tar.gz",
        "a2c558226fc4d9e4ce331bd2fd3c3f17f955115d2c00e447618a4ef9978a2a73",
    )


def zlib_src() -> Package:
    return fetchurl(
        "zlib-1.3.1.tar.gz",
        "https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz",
        "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23",
    )


def m4_src() -> Package:
    return fetchurl(
        "m4-1.4.20.tar.bz2",
        "https://ftpmirror.gnu.org/m4/m4-1.4.20.tar.bz2",
        "ac6989ee5d2aed81739780630cc2ce097e2a6546feb96a4a54db37d46a1452e4",
    )


def gettext_src() -> Package:
    return fetchurl(
        "gettext-0.25.1.tar.gz",
        "https://ftpmirror.gnu.org/gettext/gettext-0.25.1.tar.gz",
        "746f955d42d71eb69ce763869cb92682f09a4066528d018b6ca7a3f48089a085",
    )


def texinfo_src() -> Package:
    return fetchurl(
        "texinfo-7.2.tar.xz",
        "https://ftpmirror.gnu.org/texinfo/texinfo-7.2.tar.xz",
        "0329d7788fbef113fa82cb80889ca197a344ce0df7646fe000974c5d714363a6",
    )


def gmp_src() -> Package:
    return fetchurl(
        "gmp-6.3.0.tar.bz2",
        "https://ftpmirror.gnu.org/gmp/gmp-6.3.0.tar.bz2",
        "ac28211a7cfb609bae2e2c8d6058d66c8fe96434f740cf6fe2e47b000d1c20cb",
    )


def mpfr_src() -> Package:
    return fetchurl(
        "mpfr-4.2.2.tar.xz",
        "https://www.mpfr.org/mpfr-4.2.2/mpfr-4.2.2.tar.xz",
        "b67ba0383ef7e8a8563734e2e889ef5ec3c3b898a01d00fa0a6869ad81c6ce01",
    )


def libxcrypt_src() -> Package:
    return fetchurl(
        "libxcrypt-4.5.2.tar.xz",
        "https://github.com/besser82/libxcrypt/releases/download/v4.5.2/libxcrypt-4.5.2.tar.xz",
        "71513a31c01a428bccd5367a32fd95f115d6dac50fb5b60c779d5c7942aec071",
    )


def bash_src() -> Package:
    return fetchurl(
        "bash-5.3.tar.gz",
        "https://ftpmirror.gnu.org/bash/bash-5.3.tar.gz",
        "0d5cd86965f869a26cf64f4b71be7b96f90a3ba8b3d74e27e8e9d9d5550f31ba",
    )


# --- Style 2: fetchurl_sha256() — sha256 = "sha256-<base64>" ---


def patchelf_src() -> Package:
    return fetchurl_sha256(
        "patchelf-0.15.2.tar.bz2",
        "https://github.com/NixOS/patchelf/releases/download/0.15.2/patchelf-0.15.2.tar.bz2",
        "17745f564159c8e228fc412da65a2048b846c4b6b4220b77cbf22416e02f2d7c",
    )


def bison_src() -> Package:
    return fetchurl_sha256(
        "bison-3.8.2.tar.gz",
        "https://ftpmirror.gnu.org/bison/bison-3.8.2.tar.gz",
        "06c9e13bdf7eb24d4ceb6b59205a4f67c2c7e7213119644430fe82fbd14a0abb",
    )


def perl_src() -> Package:
    return fetchurl_sha256(
        "perl-5.40.0.tar.gz",
        "https://cpan.metacpan.org/src/5.0/perl-5.40.0.tar.gz",
        "c740348f357396327a9795d3e8323bafd0fe8a5c7835fc1cbaba0cc8dfe7161f",
    )


def mpc_src() -> Package:
    return fetchurl_sha256(
        "mpc-1.3.1.tar.gz",
        "https://ftpmirror.gnu.org/mpc/mpc-1.3.1.tar.gz",
        "ab642492f5cf882b74aa0cb730cd410a81edcdbec895183ce930e706c1c759b8",
    )


def gcc_src() -> Package:
    return fetchurl_sha256(
        "gcc-14.3.0.tar.xz",
        "https://mirror.koddos.net/gcc/releases/gcc-14.3.0/gcc-14.3.0.tar.xz",
        "e0dc77297625631ac8e50fa92fffefe899a4eb702592da5c32ef04e2293aca3a",
    )


# --- Style 3: fetchurl_nix32() — sha256 = "<nix32>" ---


def isl_src() -> Package:
    return fetchurl_nix32(
        "isl-0.20.tar.xz",
        "https://downloads.sourceforge.net/libisl/isl-0.20.tar.xz",
        "1akpgq0rbqbah5517blg2zlnfvjxfcl9cjrfc75nbcx5p2gnlnd5",
    )


def bash_patch_001() -> Package:
    return fetchurl_nix32(
        "bash53-001",
        "https://ftpmirror.gnu.org/bash/bash-5.3-patches/bash53-001",
        "0zr8wgg1gb67vxn7ws971n1znrdinczymc688ndnpy2a6qs88q0z",
    )


def bash_patch_002() -> Package:
    return fetchurl_nix32(
        "bash53-002",
        "https://ftpmirror.gnu.org/bash/bash-5.3-patches/bash53-002",
        "009051z55plsy4jmmjdb3ys7li2jraynz99qg7n6a1qk025591g3",
    )


def bash_patch_003() -> Package:
    return fetchurl_nix32(
        "bash53-003",
        "https://ftpmirror.gnu.org/bash/bash-5.3-patches/bash53-003",
        "1vb0gnrkmz49rcfpxjcxy0v0k5278wrlkljk9gc20nizvk3xjigj",
    )
