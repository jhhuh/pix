# pix — Dev Journal

Append-only log of what was attempted, what failed, what worked, and why.

---

## 2026-02-16 ~16:53 — Project bootstrap

- Ran `/init` to create initial CLAUDE.md. First attempt failed (OAuth token expired).
- After re-login, generated CLAUDE.md + README.md for the existing codebase (C++ FFI + Python ctypes).
- Initialized git repo. First commit — "Initial commit: Nix C API exploration in C++ and Python".

## 2026-02-16 ~17:00 — Direction clarification

- User clarified: "this is attempting to implement nix functionality with python with minimal FFI."
- Multiple planning iterations followed. User further clarified: "nix functionality, not a nix implementation" — meaning store paths, derivations, daemon protocol, not a Nix expression language evaluator.
- Research subagent failed with internal error (`classifyHandoffIfNeeded is not defined`), but enough context was gathered from the planning phase.

## 2026-02-16 ~18:05 — Pure Python implementation

- User provided an implementation plan specifying 7 modules + tests.
- Explored existing codebase, found old ctypes-based `pix/main.py` and `flake.nix` with nixos-24.11.
- Implemented all 7 core modules in ~3 minutes: `base32.py`, `hash.py`, `nar.py`, `store_path.py`, `derivation.py`, `daemon.py`, `main.py`.
- Generated Nix test vectors via real `nix` CLI. Created 5 test files.

### First test run: 23/28 pass, 5 daemon tests fail

- **Bug: Daemon handshake field ordering.** The hex value `0x352e38322e32` in the error decodes to ASCII `"2.28.5"` — a version string being misread as uint64. The code was missing the version string read (protocol >= 1.33) before the trusted status read (protocol >= 1.35). Fix: added `self._recv_string()` before `self._recv_uint64()` in `_handshake()`.

### Second test run: 26/28 pass

- **Bug: `.links` directory.** `os.listdir("/nix/store")[0]` picked `.links`, an internal Nix directory, not a valid store path. Fix: changed test to use `add_text_to_store`.
- **Bug: Hash format assertion.** Daemon returns raw hex, not `sha256:`-prefixed. Fix: relaxed assertion.

### Third test run: 28/28 pass

### End-to-end verification: store path mismatch

- **Bug: Trailing colon in type prefix.** `"text:" + ":".join([])` produces `"text:"` but Nix uses `"text"` (no trailing colon) when references list is empty. Fix: created `_make_type()` helper that only appends `:ref` when references exist.
- After fix, computed store paths match daemon output exactly. CLI smoke tests pass (NAR hash matches `nix hash path`).
- Commit — "Implement pure Python Nix functionality (no FFI)".

## 2026-02-17 ~03:24 — Documentation

- Cross-verified against `nix derivation show`, `nix store add-path`, `nix path-info`. All match.
- Wrote full README.md and CLAUDE.md.
- Commit — "Add full documentation for all modules".

## 2026-02-17 ~03:58 — MkDocs site

- Created MkDocs site with Material theme: 16 pages across API, CLI, and Internals sections.
- Commit — "Add MkDocs documentation site with Material theme".

## 2026-02-17 ~04:13 — Educational reframing (user-steered)

- User clarified project purpose: "explore/understand nix internals in terms of more easy to read python code."
- All documentation, source comments, and project framing rewritten with "why" explanations and Nix C++ source references.
- CLAUDE.md gained principle: "Priority: readability over performance."
- Commit — "Reframe as educational project for exploring Nix internals".

## 2026-02-17 ~04:23 — Agentic coding experiment (user-steered)

- User revealed secondary purpose: testing how much agentic coding can achieve without a reference project.
- Added "How this was built" section to README with specific data points.
- Commit — "Document the agentic coding experiment in README".
- Created GitHub repo via `gh repo create pix --public --source=. --push`.
- Set description + topics: `nix`, `nix-store`, `python`, `educational`, `reverse-engineering`, `agentic-coding`.
- Deployed MkDocs to GitHub Pages.

## 2026-02-17 ~05:00 — Korean translation

- Created 15 Korean translation pages, dual-config i18n approach (`mkdocs.yml` + `mkdocs-ko.yml`), language switcher.
- **Gotcha:** `mkdocs gh-deploy` wipes `site/ko/` because it runs its own `mkdocs build`. Fix: build both sites separately, then deploy with `ghp-import -n -p -f site`.
- Commit — "Add Korean translation for documentation".

## 2026-02-17 ~05:20 — Cleanup

- Removed `c/` directory (old C++ Nix API hello-world, irrelevant to educational purpose) and C-related dev dependencies from `flake.nix`.
- **Gotcha:** Compiled binary `c/main` was accidentally tracked. Fix: `git rm --cached c/main`.
- Commit — "Remove c/ directory and C-related dev dependencies".

## 2026-02-17 ~05:25 — pixpkgs design & implementation

- Designed pixpkgs architecture: nixpkgs-like package set using Python idioms.
- Python idiom mappings decided:
  - `callPackage` → `inspect.signature` + `getattr` (`PackageSet.call`)
  - `override` → `dataclasses.replace` / re-call with merged kwargs
  - String interpolation → `__str__` returning output path
  - Lazy package attrs → `@cached_property` on PackageSet
- Implemented `pixpkgs/drv.py`, `pixpkgs/package_set.py`, `pixpkgs/realize.py`, tests.

### First pixpkgs test run: 10/10 unit, 1/3 e2e pass

- **Bug: `^` vs `!` separator.** Daemon wire protocol uses `!` (legacy DerivedPath format), not `^` (CLI format). Fix: changed separator in `realize.py`.
- **Bug: Missing recursive .drv registration.** `realize()` only registered top-level .drv, not dependency .drv files. Fix: added `_register_drv()` recursive function.
- **Bug: Env not blanked in `hash_derivation_modulo`.** Nix blanks output paths in BOTH `.outputs` AND `.env`. Our code only blanked `.outputs`. Fix: added env blanking.

### Still failing: derivations with dependencies

- Entered deep debugging: byte-by-byte .drv comparison, SHA-256 trace.
- Fetched Nix 2.24.14 C++ source from GitHub (`src/libstore/derivations.cc`).

### The hardest bug: `hashDerivationModulo` two-mode distinction

- **Root cause** (found at lines 798-800 of `derivations.cc`):
  - `staticOutputHashes` calls `hashDerivationModulo` with `maskOutputs=true` — blanks own output paths (for computing OWN outputs).
  - `pathDerivationModulo` calls it with `maskOutputs=false` — keeps filled output paths (for computing INPUT derivation hashes).
  - Our code always used the equivalent of `maskOutputs=true`.
- **Fix:** Added `mask_outputs: bool = True` parameter to `hash_derivation_modulo`. In `pixpkgs/drv.py`, `_collect_input_hashes()` recursively computes dep hashes with `mask_outputs=False`.

### Sandbox build failure

- **Bug: `cat`/`tr` not found in Nix build sandbox.** Only shell builtins available via `/bin/sh`. Fix: replaced `cat` with `read line < file; echo $line`.

### All 41 tests pass (28 pix + 13 pixpkgs)

- Commit — "Add pixpkgs: nixpkgs-like package set using Python idioms".

## 2026-02-17 ~07:12 — Final documentation updates

- Updated CLAUDE.md with pixpkgs architecture and new gotchas.
- Commit — "Update CLAUDE.md with pixpkgs architecture and new gotchas".

## 2026-02-17 ~07:21 — Docs deployment & verification

- Updated all docs (EN+KO) to cover pixpkgs and maskOutputs explanation.
- Verified deployed docs via WebFetch (7 pages checked, all correct).
- Commit — "Update docs to cover pixpkgs and maskOutputs two-mode explanation".

## 2026-02-26 — Overlay pattern experiments

- Designed and implemented 4 experiments exploring Python patterns for Nix overlay semantics:
  - **A: Class Inheritance** — `self` = final, `self._prev` = prev
  - **B: `__getattr__` Chain** — dynamic overlay objects with `_final` propagation
  - **C: Lazy Fix** — direct Nix `lib.fix` / `lib.composeExtensions` translation
  - **D: Class Decorator** — `@overlay(tools=lambda self, prev: ...)` creates dynamic subclasses

### Critical bug: infinite recursion in Experiment A

- **First attempt used only `self`** for both final and prev references.
- Stage2.shell accessed `self.tools` → resolved to Stage1.tools (via MRO)
- Stage1.tools accessed `self.shell` → resolved to Stage2.shell (via MRO)
- **Cycle: Stage2.shell → self.tools → Stage1.tools → self.shell → Stage2.shell → ...**
- `@cached_property` doesn't help because the cache stores values only AFTER computation completes — during the first computation, there's nothing cached to break the cycle.
- `super()` doesn't help either — it changes method lookup class but `self` remains the most-derived instance.
- **Root cause**: Nix overlays have TWO arguments (`final` and `prev`), Python's `self` is only ONE. Without separating them, overrides that build with "previous stage's tools" inevitably chase the late-bound reference back to the current stage's override.
- **Fix**: Added `self._prev = PreviousStageClass()` as a `@cached_property`. Overridden methods use `self._prev.X` for build inputs (breaking cycles), inherited methods keep using `self.X` (preserving late binding).
- See `artifacts/skills/python-class-inheritance-infinite-recursion-in-overlay-pattern.md` for detailed trace.

### All 36 tests pass (9 per experiment × 4)

### Research: actual nixpkgs bootstrap chain

- Inspected the real bootstrap chain on the local system (`pkgs/stdenv/linux/default.nix`).
- **7 stages** (seed → stage0 → stage1 → xgcc → stage2 → stage3 → stage4 → final stdenv).
- Three key transitions:
  1. **Libc transition** (stage 2): xgcc compiles real glibc-2.40-218
  2. **Compiler transition** (stage 3): real glibc + binutils compile final gcc-14.3.0
  3. **Tools transition** (stage 4): final gcc rebuilds coreutils/sed/grep/bash/etc.
- Bootstrap-tools = single prebuilt tarball with 125 binaries (the only external input).
- Final stdenv: 38 inputDrvs, 14 initialPath packages, bash-5.3p3 as shell.
- hello-2.12.2 depends on: stdenv-linux, bash-5.3p3, hello-2.12.2.tar.gz, version-check-hook.
- See `artifacts/skills/nixpkgs-stdenv-bootstrap-chain-7-stages.md` for full detail.
