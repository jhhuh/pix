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
from pixpkgs.bootstrap.sources import (
    bash_patch_001, bash_patch_002, bash_patch_003, bash_src,
    gcc_src, gettext_src, gmp_src, isl_src, libxcrypt_src, mpc_src, mpfr_src,
    texinfo_src, which_src,
)
from pixpkgs.bootstrap.stage1 import Stage1
from pixpkgs.drv import Package
from pixpkgs.package_set import PackageSet
from pixpkgs.pkgs.bash import make_bash
from pixpkgs.pkgs.cc_wrapper import make_gcc_wrapper
from pixpkgs.pkgs.expand_response_params import make_expand_response_params
from pixpkgs.pkgs.gettext import make_gettext
from pixpkgs.pkgs.gmp import make_gmp
from pixpkgs.pkgs.gnu_config import make_gnu_config
from pixpkgs.pkgs.isl import make_isl
from pixpkgs.pkgs.libmpc import make_libmpc
from pixpkgs.pkgs.libxcrypt import make_libxcrypt
from pixpkgs.pkgs.mpfr import make_mpfr
from pixpkgs.pkgs.nuke_references import make_nuke_references
from pixpkgs.pkgs.texinfo import make_texinfo
from pixpkgs.pkgs.update_autotools import make_update_autotools_hook
from pixpkgs.pkgs.which import make_which
from pixpkgs.pkgs.xgcc import make_xgcc
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
    "stdenv_no_cc.drv": "/nix/store/32rk2x7f17a6n8krwhhw37df4pvajv0r-bootstrap-stage-xgcc-stdenv-linux.drv",
    "stdenv_no_cc.out": "/nix/store/rb78bgfyckbnag1bpys0f2zipgw82jp1-bootstrap-stage-xgcc-stdenv-linux",
    "gnu_config_pkg.drv": "/nix/store/c14yc5znpdnwlab1a2pnmnhbwdp35vp6-gnu-config-2024-01-01.drv",
    "gnu_config_pkg.out": "/nix/store/0iz8c9d6dyq3fy9f9shk3fj7y085f7i1-gnu-config-2024-01-01",
    "update_autotools_hook_pkg.drv": "/nix/store/qvd48yga2kyydg00lwb87mfqn31mrzh9-update-autotools-gnu-config-scripts-hook.drv",
    "update_autotools_hook_pkg.out": "/nix/store/b6vpv6747yf3nz1rdsxlbibpfvlpw6c7-update-autotools-gnu-config-scripts-hook",
    "gmp.drv": "/nix/store/4xws3d0jp4viffjqbjv9y1ydb524ld3n-gmp-6.3.0.drv",
    "gmp.out": "/nix/store/5wxh08is7sqk98xhganbxivbvr52pp1d-gmp-6.3.0",
    "mpfr.drv": "/nix/store/y6h178j984aih84hfi6d1gkj3p2v9ihx-mpfr-4.2.2.drv",
    "mpfr.out": "/nix/store/d3jzigiaca36mqig1454s2xi56k62m33-mpfr-4.2.2",
    "isl.drv": "/nix/store/kj32l38r9bfh4dncdf7gkscnnzysz5y7-isl-0.20.drv",
    "isl.out": "/nix/store/x0p0rfjp51kps8qypslvz0zy24a8yv92-isl-0.20",
    "libmpc.drv": "/nix/store/y7gga2zv5gm723hgd6j488qagyrrmqfk-libmpc-1.3.1.drv",
    "libmpc.out": "/nix/store/3cilgifl43vi073g9f7v8lw6gpd82zsp-libmpc-1.3.1",
    "libxcrypt.drv": "/nix/store/dcjviapmsh40ransb323w1j1mx9sfiyl-libxcrypt-4.5.2.drv",
    "libxcrypt.out": "/nix/store/p05a4xm5hj6adzypfaq3la6vwlwdylal-libxcrypt-4.5.2",
    # --- stage1-evaluation packages (need xgcc infra update_autotools_hook) ---
    "bash_pkg.drv": "/nix/store/v9limmbzkvjcdrfijq5ig760yg5gvza6-bash-5.3p3.drv",
    "bash_pkg.out": "/nix/store/7fmqg3y3vgzd31a40azmz2szq34hmp9z-bash-5.3p3",
    "gettext.drv": "/nix/store/i32afvwnj2ph8z7zxrkl9b78djbknmbb-gettext-0.25.1.drv",
    "gettext.out": "/nix/store/x28dwagyvy8xyfbi0ggzib5jl2icy7fk-gettext-0.25.1",
    "texinfo.drv": "/nix/store/rz7galzrzr5y99cbqp8yz3b27c8zpvvb-texinfo-7.2.drv",
    "texinfo.out": "/nix/store/bkjfh4f71d24blykcljpg6gcrkqyx29j-texinfo-7.2",
    # --- xgcc prerequisites ---
    "nuke_references.drv": "/nix/store/lrars4gba2q7l2437nw5ir2qglsclm4v-nuke-references.drv",
    "nuke_references.out": "/nix/store/pm6lhapwm6p9ffq7hsb01s37hi8dk8jf-nuke-references",
    "which_pkg.drv": "/nix/store/dg0zhxdxrzap31fkk9d6r19ravryscj4-which-2.23.drv",
    "which_pkg.out": "/nix/store/vpkqvb9nwa2c13w6rmf8zlmwchad6xir-which-2.23",
    "bash_xgcc.drv": "/nix/store/bz65kaqhwsn63sihzr1yr0rapdx7mx46-bash-5.3p3.drv",
    "bash_xgcc.out": "/nix/store/w4qlsz5kzg93nqjs8v44b7vgcinx4wsq-bash-5.3p3",
    # --- xgcc itself ---
    "xgcc.drv": "/nix/store/bm5kzm1lv0dkrznzc79zl5rwbv71460w-xgcc-14.3.0.drv",
    "xgcc.out": "/nix/store/b9fm5nak3xrg6nhpmclqh45x2z1ssdnq-xgcc-14.3.0",
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

    # --- xgcc package-set support ---
    # In nixpkgs, the xgcc stage evaluates ALL of nixpkgs with xgcc stdenv.
    # Packages like makeSetupHook use stdenvNoCC (xgcc stdenv minus gcc-wrapper).
    # gnu-config and updateAutotoolsGnuConfigScriptsHook are rebuilt in this
    # evaluation context, separate from the infrastructure versions above.

    @cached_property
    def stdenv_no_cc(self) -> Package:
        """xgcc stdenv without gcc-wrapper (= stdenvNoCC in nixpkgs).

        Used by makeSetupHook and other packages that don't need a compiler.
        Same as self.stdenv but without gcc_wrapper in defaultNativeBuildInputs.
        """
        bt = str(self._prev._prev.bootstrap_tools)
        hook = str(self.update_autotools_hook)
        return make_stdenv(
            "bootstrap-stage-xgcc-stdenv-linux",
            shell=f"{bt}/bin/bash",
            initial_path=bt,
            builder=f"{bt}/bin/bash",
            default_native_build_inputs=" ".join([
                hook,
                *DEFAULT_NATIVE_BUILD_INPUTS.split(),
                # NO gcc_wrapper — this is stdenvNoCC
            ]),
            pre_hook=STAGE0_PREHOOK,
            deps=[
                self._prev._prev.bootstrap_tools,
                self.update_autotools_hook,
            ],
        )

    @cached_property
    def gnu_config_pkg(self) -> Package:
        """gnu-config built with full xgcc stdenv (for the package set)."""
        return make_gnu_config(
            self._prev.config_guess, self._prev.config_sub,
            self._prev._prev.bootstrap_tools, self.stdenv,
        )

    @cached_property
    def update_autotools_hook_pkg(self) -> Package:
        """updateAutotoolsGnuConfigScriptsHook for xgcc package set.

        Built with stdenv_no_cc (makeSetupHook uses stdenvNoCC) and
        gnu_config_pkg (gnu-config built with full xgcc stdenv).
        """
        return make_update_autotools_hook(
            self.gnu_config_pkg,
            self._prev._prev.bootstrap_tools,
            self.stdenv_no_cc,
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
    def mpfr(self) -> Package:
        """MPFR built with xgcc stdenv."""
        return make_mpfr(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=mpfr_src(),
            gmp=self.gmp,
            update_autotools_hook=self.update_autotools_hook_pkg,
        )

    @cached_property
    def isl(self) -> Package:
        """ISL 0.20 built with xgcc stdenv (for GCC Graphite)."""
        return make_isl(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=isl_src(),
            gmp=self.gmp,
            update_autotools_hook=self.update_autotools_hook_pkg,
        )

    @cached_property
    def libmpc(self) -> Package:
        """libmpc 1.3.1 built with xgcc stdenv."""
        return make_libmpc(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=mpc_src(),
            gmp=self.gmp,
            mpfr=self.mpfr,
            update_autotools_hook=self.update_autotools_hook_pkg,
        )

    @cached_property
    def libxcrypt(self) -> Package:
        """libxcrypt 4.5.2 built with xgcc stdenv."""
        return make_libxcrypt(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=libxcrypt_src(),
            perl=self.perl,  # stage1 perl via delegation
        )

    # --- "stage1 evaluation of nixpkgs" packages ---
    # These are compiled with stage1 stdenv but explicitly reference
    # updateAutotoolsGnuConfigScriptsHook in nativeBuildInputs, which
    # in the stage1 nixpkgs evaluation resolves to the xgcc infrastructure
    # version (self.update_autotools_hook), not stage1's infrastructure version.

    @cached_property
    def bash_pkg(self) -> Package:
        """Bash rebuilt with xgcc infrastructure update_autotools_hook.

        This is the "stage1 pkg-set" bash — same as stage1 bash but with
        the xgcc infrastructure update_autotools_hook in nativeBuildInputs.
        Used by gettext and texinfo (which need bash.dev as buildInput).
        """
        return make_bash(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self._prev.stdenv,
            src=bash_src(),
            bash_patch_001=bash_patch_001(),
            bash_patch_002=bash_patch_002(),
            bash_patch_003=bash_patch_003(),
            gcc_wrapper=self._prev.gcc_wrapper,
            update_autotools_hook=self.update_autotools_hook,
            bison=self._prev.bison,
        )

    @cached_property
    def gettext(self) -> Package:
        """gettext 0.25.1, stage1 stdenv + xgcc infra update_autotools_hook."""
        return make_gettext(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self._prev.stdenv,
            src=gettext_src(),
            bash=self.bash_pkg,
            update_autotools_hook=self.update_autotools_hook,
        )

    @cached_property
    def texinfo(self) -> Package:
        """texinfo 7.2, stage1 stdenv + xgcc infra update_autotools_hook."""
        return make_texinfo(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self._prev.stdenv,
            src=texinfo_src(),
            bash=self.bash_pkg,
            gcc_wrapper=self._prev.gcc_wrapper,
            perl=self._prev.perl,
            update_autotools_hook=self.update_autotools_hook,
        )

    # --- xgcc prerequisites (built with xgcc stdenv) ---

    @cached_property
    def nuke_references(self) -> Package:
        """nuke-references: strips store refs from build outputs.

        Uses xgcc stdenvNoCC (no compiler needed, just installs a script).
        """
        return make_nuke_references(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv_no_cc,
            perl=self._prev.perl,
        )

    @cached_property
    def which_pkg(self) -> Package:
        """which-2.23 rebuilt with xgcc stdenv."""
        return make_which(
            self._prev._prev.bootstrap_tools, self.stdenv, which_src(),
        )

    @cached_property
    def bash_xgcc(self) -> Package:
        """bash-5.3p3 rebuilt with xgcc stdenv.

        Uses xgcc gcc_wrapper for depsBuildBuild and xgcc pkg-set
        update_autotools_hook_pkg for nativeBuildInputs.
        """
        return make_bash(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=bash_src(),
            bash_patch_001=bash_patch_001(),
            bash_patch_002=bash_patch_002(),
            bash_patch_003=bash_patch_003(),
            gcc_wrapper=self.gcc_wrapper,
            update_autotools_hook=self.update_autotools_hook_pkg,
            bison=self._prev.bison,
        )

    # --- xgcc itself ---

    @cached_property
    def xgcc(self) -> Package:
        """gcc-unwrapped 14.3.0 compiled from source.

        The most complex package in the bootstrap chain. 6 outputs,
        19 inputDrvs, massive env vars with shell scripts.
        """
        return make_xgcc(
            bootstrap_tools=self._prev._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=gcc_src(),
            gcc_wrapper=self.gcc_wrapper,
            binutils_wrapper=self._prev.binutils_wrapper,
            patchelf=self._prev.patchelf,
            glibc_bootstrap_files=self._prev.glibc_bootstrap_files,
            gmp=self.gmp,
            mpfr=self.mpfr,
            libmpc=self.libmpc,
            libxcrypt=self.libxcrypt,
            isl=self.isl,
            zlib=self._prev.zlib,
            texinfo=self.texinfo,
            which_pkg=self.which_pkg,
            gettext=self.gettext,
            perl=self._prev.perl,
            bash_xgcc=self.bash_xgcc,
            nuke_references=self.nuke_references,
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
            self.stdenv_no_cc.drv_path: self.stdenv_no_cc,
            self.gnu_config_pkg.drv_path: self.gnu_config_pkg,
            self.update_autotools_hook_pkg.drv_path: self.update_autotools_hook_pkg,
            self.gmp.drv_path: self.gmp,
            self.mpfr.drv_path: self.mpfr,
            self.isl.drv_path: self.isl,
            self.libmpc.drv_path: self.libmpc,
            self.libxcrypt.drv_path: self.libxcrypt,
            self.bash_pkg.drv_path: self.bash_pkg,
            self.gettext.drv_path: self.gettext,
            self.texinfo.drv_path: self.texinfo,
            self.nuke_references.drv_path: self.nuke_references,
            self.which_pkg.drv_path: self.which_pkg,
            self.bash_xgcc.drv_path: self.bash_xgcc,
            self.xgcc.drv_path: self.xgcc,
        }
        return {**self._prev.all_packages, **own}
