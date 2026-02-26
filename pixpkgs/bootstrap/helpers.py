"""Shared helpers for the bootstrap stages.

Functions and constants used across multiple stages:
  - make_stdenv(): creates a stdenv derivation for any stage
  - STAGE0_PREHOOK: prehook that disables patchShebangs
  - TARBALLS_BASE: URL prefix for bootstrap-tools downloads
  - GNU_CONFIG_*: config.guess/config.sub source URLs
"""

from pixpkgs.drv import Package, drv
from pixpkgs.vendor import BUILDER_SCRIPT, HOOK_SCRIPTS, SETUP_SCRIPT


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARBALLS_BASE = (
    "http://tarballs.nixos.org/stdenv/x86_64-unknown-linux-gnu/"
    "82b583ba2ba2e5706b35dbe23f31362e62be2a9d"
)

STAGE0_PREHOOK = """\
# Don't patch #!/interpreter because it leads to retained
# dependencies on the bootstrapTools in the final stdenv.
dontPatchShebangs=1
export NIX_ENFORCE_PURITY="${NIX_ENFORCE_PURITY-1}"
export NIX_ENFORCE_NO_NATIVE="${NIX_ENFORCE_NO_NATIVE-1}"

"""

GNU_CONFIG_COMMIT = "948ae97ca5703224bd3eada06b7a69f40dd15a02"
GNU_CONFIG_BASE = "https://git.savannah.gnu.org/cgit/config.git/plain"


# ---------------------------------------------------------------------------
# make_stdenv: the stdenv derivation constructor
# ---------------------------------------------------------------------------

def make_stdenv(name: str, *, shell: str, initial_path: str,
                builder: str, default_native_build_inputs: str,
                pre_hook: str, deps: list[Package],
                srcs: list[str] | None = None,
                disallowed_requisites: str = "",
                default_build_inputs: str = "") -> Package:
    """Create a stdenv derivation.

    Like nixpkgs/pkgs/stdenv/generic/make-derivation.nix — each bootstrap
    stage produces a stdenv that provides the build environment (compiler,
    shell, setup hooks) for the next stage.
    """
    return drv(
        name=name,
        builder=builder,
        system="x86_64-linux",
        args=["-e", BUILDER_SCRIPT],
        deps=deps,
        srcs=srcs or HOOK_SCRIPTS,
        env={
            "defaultBuildInputs": default_build_inputs,
            "defaultNativeBuildInputs": default_native_build_inputs,
            "disallowedRequisites": disallowed_requisites,
            "initialPath": initial_path,
            "preHook": pre_hook,
            "setup": SETUP_SCRIPT,
            "shell": shell,
        },
    )
