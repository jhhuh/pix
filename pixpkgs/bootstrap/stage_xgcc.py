"""Stage Xgcc: First rebuild of GCC.

Like nixpkgs/pkgs/stdenv/linux/default.nix "bootstrap-stage-xgcc":
The xgcc stage compiles GCC from source using the bootstrap-tools compiler.
The resulting xgcc binary is "linked against junk from bootstrap-files",
but we only care about the code it *emits* — it's not part of the final stdenv.

Key infrastructure packages:
  - cc_wrapper_stdenv: stage1 stdenv without gcc-wrapper (avoids circular dep)
  - expand_response_params: C program that expands @file args (new)
  - gnu_config: config.guess/config.sub rebuilt with stage1 stdenv
  - update_autotools_hook: rebuilt with cc_wrapper_stdenv + rebuilt gnu_config
  - gcc_wrapper: like stage1 but with expand-response-params
  - stdenv: uses new gcc_wrapper + rebuilt update_autotools_hook

Uses composition (not inheritance) to avoid MRO issues: inherited packages
from Stage1 are accessed via self._prev, not re-derived through self.
"""

from functools import cached_property

from pixpkgs.bootstrap.helpers import (
    STAGE0_PREHOOK, make_stdenv,
)
from pixpkgs.bootstrap.stage1 import Stage1
from pixpkgs.drv import Package
from pixpkgs.package_set import PackageSet
from pixpkgs.bootstrap.sources import gmp_src
from pixpkgs.pkgs.cc_wrapper import make_gcc_wrapper
from pixpkgs.pkgs.expand_response_params import make_expand_response_params
from pixpkgs.pkgs.gmp import make_gmp
from pixpkgs.pkgs.gnu_config import make_gnu_config
from pixpkgs.pkgs.update_autotools import make_update_autotools_hook
from pixpkgs.vendor import DEFAULT_NATIVE_BUILD_INPUTS


EXPECTED_STAGE_XGCC = {
    "cc_wrapper_stdenv.drv": "/nix/store/azldj1vl9q67bin997dfwdknvgx94qiw-bootstrap-stage1-stdenv-linux.drv",
    "cc_wrapper_stdenv.out": "/nix/store/8qbdvj24jhi4920b5xp2pvhmg0pv95mz-bootstrap-stage1-stdenv-linux",
    "expand_response_params.drv": "/nix/store/zdwwa5vravzi5k0976cvxv7gnkprzq6k-expand-response-params.drv",
    "expand_response_params.out": "/nix/store/49ams3jica8y6c2p93058rp67wkq5bdy-expand-response-params",
    "gnu_config.drv": "/nix/store/w85rskf0f40fw3ygbpcs3iq87ynncrkg-gnu-config-2024-01-01.drv",
    "gnu_config.out": "/nix/store/2b96blvjcclrswkdy5fqzq2kz0nzzac7-gnu-config-2024-01-01",
    "update_autotools_hook.drv": "/nix/store/vcq0nzi3rzndlyryvb2pz35xpp580ghy-update-autotools-gnu-config-scripts-hook.drv",
    "update_autotools_hook.out": "/nix/store/9lid25cvryxhm6xzp80lp29nai9245sc-update-autotools-gnu-config-scripts-hook",
    "gcc_wrapper.drv": "/nix/store/0pifk66l65nk7jw6q2svhrw73lmzpw1j-bootstrap-stage-xgcc-gcc-wrapper-.drv",
    "gcc_wrapper.out": "/nix/store/mk49cy3kxsmxfhpjvvv8gg8nsp67knrf-bootstrap-stage-xgcc-gcc-wrapper-",
    "stdenv.drv": "/nix/store/kpb871v49izkzs3z4pbd6ayrg1x3q0ak-bootstrap-stage-xgcc-stdenv-linux.drv",
    "stdenv.out": "/nix/store/180jrl2n0wh7p4rbphy406dbxpjbp60s-bootstrap-stage-xgcc-stdenv-linux",
    "gmp.drv": "/nix/store/4xws3d0jp4viffjqbjv9y1ydb524ld3n-gmp-6.3.0.drv",
    "gmp.out": "/nix/store/5wxh08is7sqk98xhganbxivbvr52pp1d-gmp-6.3.0",
}


class StageXgcc(PackageSet):
    """First GCC rebuild: wraps bootstrap-tools with expand-response-params.

    Adds 6 packages: cc_wrapper_stdenv, expand_response_params, gnu_config
    (rebuilt), update_autotools_hook (rebuilt), gcc_wrapper, stdenv.

    Uses composition: non-overridden packages delegate to _prev (Stage1).
    """

    @cached_property
    def _prev(self) -> Stage1:
        return Stage1()

    def __getattr__(self, name: str):
        """Delegate unknown attributes to previous stage (Stage1)."""
        return getattr(self._prev, name)

    # --- cc_wrapper_stdenv: stage1 stdenv WITHOUT gcc-wrapper ---
    # Like nixpkgs ccWrapperStdenv — removes CC from defaultNativeBuildInputs
    # to avoid circular dependency when building the cc-wrapper itself.

    @cached_property
    def cc_wrapper_stdenv(self) -> Package:
        """Stage1 stdenv without gcc-wrapper in defaultNativeBuildInputs."""
        bt = str(self._prev._prev.bootstrap_tools)
        hook = str(self._prev.update_autotools_hook)
        return make_stdenv(
            "bootstrap-stage1-stdenv-linux",
            shell=f"{bt}/bin/bash",
            initial_path=bt,
            builder=f"{bt}/bin/bash",
            default_native_build_inputs=" ".join([
                hook,
                *DEFAULT_NATIVE_BUILD_INPUTS.split(),
                # NO gcc_wrapper here — that's the whole point
            ]),
            pre_hook=STAGE0_PREHOOK,
            deps=[
                self._prev._prev.bootstrap_tools,
                self._prev.update_autotools_hook,
            ],
        )

    # --- packages built by stage1 stdenv ---

    @cached_property
    def expand_response_params(self) -> Package:
        """C program that expands @file response-file arguments."""
        return make_expand_response_params(
            self._prev._prev.bootstrap_tools, self._prev.stdenv,
        )

    @cached_property
    def gnu_config(self) -> Package:
        """GNU config scripts rebuilt with stage1 stdenv."""
        return make_gnu_config(
            self._prev.config_guess, self._prev.config_sub,
            self._prev._prev.bootstrap_tools, self._prev.stdenv,
        )

    @cached_property
    def update_autotools_hook(self) -> Package:
        """Update-autotools hook rebuilt with cc_wrapper_stdenv + new gnu_config."""
        return make_update_autotools_hook(
            self.gnu_config,
            self._prev._prev.bootstrap_tools,
            self.cc_wrapper_stdenv,
        )

    # --- stage-xgcc infrastructure ---

    @cached_property
    def gcc_wrapper(self) -> Package:
        """GCC wrapper with expand-response-params (uses stage0 stdenv)."""
        erp = str(self.expand_response_params)
        return make_gcc_wrapper(
            self._prev._prev.bootstrap_tools,
            self._prev.binutils_wrapper,
            self._prev.glibc_bootstrap_files,
            self._prev._prev.stdenv,
            pname="bootstrap-stage-xgcc-gcc-wrapper",
            expand_response_params=f"{erp}/bin/expand-response-params",
            expand_response_params_pkg=self.expand_response_params,
        )

    @cached_property
    def stdenv(self) -> Package:
        """Stage-xgcc stdenv: uses gcc-wrapper with expand-response-params."""
        bt = str(self._prev._prev.bootstrap_tools)
        gcc_w = str(self.gcc_wrapper)
        hook = str(self.update_autotools_hook)
        return make_stdenv(
            "bootstrap-stage-xgcc-stdenv-linux",
            shell=f"{bt}/bin/bash",
            initial_path=bt,
            builder=f"{bt}/bin/bash",
            default_native_build_inputs=" ".join([
                hook,
                *DEFAULT_NATIVE_BUILD_INPUTS.split(),
                gcc_w,
            ]),
            pre_hook=STAGE0_PREHOOK,
            deps=[
                self._prev._prev.bootstrap_tools,
                self.gcc_wrapper,
                self.update_autotools_hook,
            ],
        )

    # --- Packages built by xgcc stdenv ---
    # These are the "overrides" from nixpkgs bootstrap-stage-xgcc.
    # gmp = super.gmp.override { cxx = false; }

    @cached_property
    def gmp(self) -> Package:
        """GMP built with xgcc stdenv (cxx=false for bootstrap)."""
        return make_gmp(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=gmp_src(),
            gcc_wrapper=self.gcc_wrapper,
            gnum4=self.gnum4,
        )

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        own = {
            self.cc_wrapper_stdenv.drv_path: self.cc_wrapper_stdenv,
            self.expand_response_params.drv_path: self.expand_response_params,
            self.gnu_config.drv_path: self.gnu_config,
            self.update_autotools_hook.drv_path: self.update_autotools_hook,
            self.gcc_wrapper.drv_path: self.gcc_wrapper,
            self.stdenv.drv_path: self.stdenv,
            self.gmp.drv_path: self.gmp,
        }
        return {**self._prev.all_packages, **own}
