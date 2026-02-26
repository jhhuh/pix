"""Vendored script files from nixpkgs — self-contained store path computation.

These are source files checked into nixpkgs that get imported into the Nix store
as path sources. We vendor them so pixpkgs doesn't depend on a nixpkgs checkout
at derivation-construction time.

Each file is byte-identical to the nixpkgs original. Store paths are computed
from the file's NAR hash + name using ``path_to_store_path()`` — the same
algorithm Nix uses for ``builtins.path`` / ``./file.nix`` imports.

Directory layout mirrors nixpkgs source tree::

    vendor/
      stdenv/          setup.sh, builder.sh, source-stdenv.sh, default-builder.sh
      bootstrap/       unpack-bootstrap-tools.sh
      bintools-wrapper/  setup-hook.sh, add-flags.sh, ld-wrapper.sh, ...
      cc-wrapper/        setup-hook.sh, add-flags.sh, cc-wrapper.sh, ...
      hooks/             no-broken-symlinks.sh, strip.sh, ...
      update-autotools/  update-autotools-gnu-config-scripts.sh
"""

from pathlib import Path

from pix.store_path import path_to_store_path

_VENDOR = Path(__file__).parent / "vendor"


def _src(subdir: str, filename: str) -> str:
    """Compute the nix store path for a vendored source file."""
    return path_to_store_path(str(_VENDOR / subdir / filename), filename)


# ---------------------------------------------------------------------------
# stdenv core scripts
# ---------------------------------------------------------------------------

SETUP_SCRIPT = _src("stdenv", "setup.sh")
BUILDER_SCRIPT = _src("stdenv", "builder.sh")
SOURCE_STDENV_SH = _src("stdenv", "source-stdenv.sh")
DEFAULT_BUILDER_SH = _src("stdenv", "default-builder.sh")

# ---------------------------------------------------------------------------
# bootstrap
# ---------------------------------------------------------------------------

UNPACK_SCRIPT = _src("bootstrap", "unpack-bootstrap-tools.sh")

# ---------------------------------------------------------------------------
# bintools-wrapper (pkgs/build-support/bintools-wrapper/)
# ---------------------------------------------------------------------------

BINTOOLS_SETUP_HOOK = _src("bintools-wrapper", "setup-hook.sh")
BINTOOLS_ADD_FLAGS = _src("bintools-wrapper", "add-flags.sh")
BINTOOLS_ADD_HARDENING = _src("bintools-wrapper", "add-hardening.sh")
LD_WRAPPER_SH = _src("bintools-wrapper", "ld-wrapper.sh")
STRIP_WRAPPER_SH = _src("bintools-wrapper", "gnu-binutils-strip-wrapper.sh")

# Shared between bintools-wrapper and cc-wrapper
ROLE_BASH = _src("bintools-wrapper", "role.bash")
UTILS_BASH = _src("bintools-wrapper", "utils.bash")
DARWIN_SDK_SETUP_BASH = _src("bintools-wrapper", "darwin-sdk-setup.bash")

# ---------------------------------------------------------------------------
# cc-wrapper (pkgs/build-support/cc-wrapper/)
# ---------------------------------------------------------------------------

CC_SETUP_HOOK = _src("cc-wrapper", "setup-hook.sh")
CC_ADD_FLAGS = _src("cc-wrapper", "add-flags.sh")
CC_ADD_HARDENING = _src("cc-wrapper", "add-hardening.sh")
CC_WRAPPER_SH = _src("cc-wrapper", "cc-wrapper.sh")
EXPAND_RESPONSE_PARAMS_C = _src("cc-wrapper", "expand-response-params.c")

# ---------------------------------------------------------------------------
# stdenv setup hooks (pkgs/build-support/setup-hooks/)
# ---------------------------------------------------------------------------

HOOK_NO_BROKEN_SYMLINKS = _src("hooks", "no-broken-symlinks.sh")
HOOK_AUDIT_TMPDIR = _src("hooks", "audit-tmpdir.sh")
HOOK_COMPRESS_MAN_PAGES = _src("hooks", "compress-man-pages.sh")
HOOK_MAKE_SYMLINKS_RELATIVE = _src("hooks", "make-symlinks-relative.sh")
HOOK_MOVE_DOCS = _src("hooks", "move-docs.sh")
HOOK_MOVE_LIB64 = _src("hooks", "move-lib64.sh")
HOOK_MOVE_SBIN = _src("hooks", "move-sbin.sh")
HOOK_MOVE_SYSTEMD_USER_UNITS = _src("hooks", "move-systemd-user-units.sh")
HOOK_MULTIPLE_OUTPUTS = _src("hooks", "multiple-outputs.sh")
HOOK_PATCH_SHEBANGS = _src("hooks", "patch-shebangs.sh")
HOOK_PRUNE_LIBTOOL_FILES = _src("hooks", "prune-libtool-files.sh")
HOOK_REPRODUCIBLE_BUILDS = _src("hooks", "reproducible-builds.sh")
HOOK_SET_SOURCE_DATE_EPOCH = _src("hooks", "set-source-date-epoch-to-latest.sh")
HOOK_STRIP = _src("hooks", "strip.sh")

HOOK_SCRIPTS = sorted([
    HOOK_NO_BROKEN_SYMLINKS, HOOK_AUDIT_TMPDIR, HOOK_COMPRESS_MAN_PAGES,
    HOOK_MAKE_SYMLINKS_RELATIVE, HOOK_MOVE_DOCS, HOOK_MOVE_LIB64,
    HOOK_MOVE_SBIN, HOOK_MOVE_SYSTEMD_USER_UNITS, HOOK_MULTIPLE_OUTPUTS,
    HOOK_PATCH_SHEBANGS, HOOK_PRUNE_LIBTOOL_FILES, HOOK_REPRODUCIBLE_BUILDS,
    HOOK_SET_SOURCE_DATE_EPOCH, HOOK_STRIP,
    BUILDER_SCRIPT, SETUP_SCRIPT,
])

# The default set for stdenv's defaultNativeBuildInputs
DEFAULT_NATIVE_BUILD_INPUTS = " ".join([
    HOOK_NO_BROKEN_SYMLINKS,
    HOOK_AUDIT_TMPDIR,
    HOOK_COMPRESS_MAN_PAGES,
    HOOK_MAKE_SYMLINKS_RELATIVE,
    HOOK_MOVE_DOCS,
    HOOK_MOVE_LIB64,
    HOOK_MOVE_SBIN,
    HOOK_MOVE_SYSTEMD_USER_UNITS,
    HOOK_MULTIPLE_OUTPUTS,
    HOOK_PATCH_SHEBANGS,
    HOOK_PRUNE_LIBTOOL_FILES,
    HOOK_REPRODUCIBLE_BUILDS,
    HOOK_SET_SOURCE_DATE_EPOCH,
    HOOK_STRIP,
])

# ---------------------------------------------------------------------------
# update-autotools-gnu-config-scripts-hook
# ---------------------------------------------------------------------------

UPDATE_AUTOTOOLS_SCRIPT = _src(
    "update-autotools", "update-autotools-gnu-config-scripts.sh",
)
