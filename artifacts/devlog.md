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
