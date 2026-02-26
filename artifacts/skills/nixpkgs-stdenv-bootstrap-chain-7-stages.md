# Nixpkgs stdenv Bootstrap Chain — 7 Stages (x86_64-linux)

## Source

Inspected from local nixpkgs:
- Stage definition: `pkgs/stdenv/linux/default.nix`
- `__bootPackages` chain has 7 links (seed + 6 stages + final)

## Stage Summary

| Stage | stdenv name | Shell | CC Compiler | Libc | Key Builds |
|-------|------------|-------|-------------|------|------------|
| seed | (raw attrs) | — | — | — | — |
| 0 | `bootstrap-stage0-stdenv-linux` | bootstrap-tools/bash | bootstrap-tools | dummy glibc | gcc-wrapper, fetchurl |
| 1 | `bootstrap-stage1-stdenv-linux` | bootstrap-tools/bash | bootstrap-tools (wrapped) | dummy glibc | binutils, perl |
| xgcc | `bootstrap-stage-xgcc-stdenv-linux` | bootstrap-tools/bash | xgcc-14.3.0 | dummy glibc | gcc-unwrapped (xgcc), gmp, mpfr, libmpc, isl, patchelf |
| 2 | `bootstrap-stage2-stdenv-linux` | bootstrap-tools/bash | xgcc-14.3.0 | **glibc-2.40-218** | glibc (the libc transition) |
| 3 | `bootstrap-stage3-stdenv-linux` | bootstrap-tools/bash | **gcc-14.3.0** | glibc-2.40-218 | final gcc (the compiler transition) |
| 4 | `bootstrap-stage4-stdenv-linux` | bootstrap-tools/bash | gcc-14.3.0 | glibc-2.40-218 | coreutils, bash, sed, grep, etc. (the tools transition) |
| **final** | `stdenv-linux` | **bash-5.3p3** | gcc-14.3.0 | glibc-2.40-218 | assembles all, no bootstrap refs |

## Three Key Transitions

1. **Libc transition (stage 2)**: xgcc compiles real glibc-2.40-218. All new code from here links against real glibc.
2. **Compiler transition (stage 3)**: Real glibc + nixpkgs binutils compile final gcc-14.3.0 (no longer "xgcc").
3. **Tools transition (stage 4)**: Final gcc rebuilds all coreutils/findutils/grep/sed/etc. from source.

## Bootstrap-tools (the seed)

Path: `/nix/store/razasrvdg7ckplfmvdxv4ia3wbayr94s-bootstrap-tools`

Single prebuilt tarball: 125 binaries (coreutils, gcc, g++, ld, ar, make, sed, grep, etc.)
plus glibc, libgcc, libgmp, libisl, libmpc, libmpfr, binutils libs.

Contents: `bin/` (125 executables), `lib/`, `include-glibc/`, `libexec/`.

## Final stdenv

**drv:** `gcm3x4yxwc0wzcgvhb6msyqnbd6afh2w-stdenv-linux.drv`
**out:** `nyb412rmpdv4wx11vvs499mqggzzdv22-stdenv-linux`

- builder: bash-5.3p3 (rebuilt, not bootstrap-tools)
- inputDrvs: 38
- initialPath: 14 packages (coreutils, findutils, diffutils, gnused, gnugrep, gawk, gnutar, gzip, bzip2, gnumake, bash, patch, xz, file)
- defaultNativeBuildInputs: 17 items (patchelf, gcc-wrapper, various hooks)
- Output: `setup` script + `nix-support/` dir

## hello (test target)

**drv:** `8vsr43y1hyqahxxrphgrcg2039jjzjq0-hello-2.12.2.drv`
**out:** `bgcw8smdrjxcgv1g32nhpip31nk7x9mj-hello-2.12.2`

- builder: bash-5.3p3
- args: `['-e', 'source-stdenv.sh', 'default-builder.sh']`
- inputDrvs: 4 (stdenv-linux, bash-5.3p3, hello-2.12.2.tar.gz, version-check-hook)

## Three Invariants (from `default.nix`)

1. Final stdenv must not **reference** any bootstrap files
2. Final stdenv must not **contain** any bootstrap files
3. Final stdenv must not contain files **directly generated** by bootstrap code generators

## Overlay Pattern

Each stage is an overlay over the previous:
- Stage0: creates dummy stdenv with bootstrap-tools
- Each subsequent stage overrides specific packages (gcc, glibc, binutils, coreutils...)
- Non-overridden packages inherit from previous stage
- `self`/`final` gives late binding (open recursion)
- `prev` gives previous stage's versions (build dependencies)
