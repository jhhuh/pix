# Nix make-derivation.nix: How Env Vars End Up in .drv Files

## Three Sources of Env Vars

### 1. Attrs pass-through (the `//` merge)

`derivationArg = removeAttrs attrs removedOrReplacedAttrNames // { ... }`

Most package attributes survive into the derivation env unless they're in
`removedOrReplacedAttrNames` (only 15 attrs: `checkInputs`, `installCheckInputs`,
`nativeCheckInputs`, `nativeInstallCheckInputs`, `__contentAddressed`,
`__darwinAllowLocalNetworking`, `__impureHostDeps`, `__propagatedImpureHostDeps`,
`sandboxProfile`, `propagatedSandboxProfile`, `disallowedReferences`,
`disallowedRequisites`, `allowedReferences`, `allowedRequisites`,
`allowedImpureDLLs`).

Also removed separately: `meta`, `passthru`, `pos`, `env`.

**Examples of pass-through attrs that appear in .drv env:**
- `patch_suffix` (bash: `"p3"`)
- `makeFlags` (empty list → `""`)
- `hardeningDisable` (list → space-separated string)
- `enableParallelBuilding` (when true)

### 2. Conditional env vars (null-key pattern)

```nix
${if enableParallelBuilding then "enableParallelBuilding" else null} = ...;
```

In Nix, `{ ${null} = "value"; }` equals `{}` — null keys are no-ops.
So when `enableParallelBuilding` is false, the key doesn't appear at all.

**Key conditionals:**
- `enableParallelBuilding/Checking/Installing`: only when `enableParallelBuilding = true`
- `NIX_HARDENING_ENABLE`: only when `hardeningDisable != [] || hardeningEnable != [] || isMusl`
- `__contentAddressed` + `outputHashAlgo/Mode`: only for CA derivations

### 3. `env` attrset (merged at the end)

```nix
derivation (derivationArg // checkedEnv)
```

The `env` attribute from the package (e.g., `env.NIX_CFLAGS_COMPILE`) is
processed into `checkedEnv` and merged into the derivation args last.
`NIX_MAIN_PROGRAM` is injected here from `meta.mainProgram`.

## NIX_HARDENING_ENABLE

Computed from `defaultHardeningFlags` (from `bintools-wrapper/default.nix`) minus
`hardeningDisable`, plus `hardeningEnable`. The default flags (12):

```
bindnow format fortify fortify3 libcxxhardeningextensive libcxxhardeningfast
pic relro stackclashprotection stackprotector strictoverflow zerocallusedregs
```

Note: `defaultHardeningFlags` is NOT `knownHardeningFlags` (which has 19).
It comes from `stdenv.cc.defaultHardeningFlags` → `bintools.defaultHardeningFlags`.

## NIX_MAIN_PROGRAM

From `meta.mainProgram`. Added to `env'` in `mkDerivationSimple`:
```nix
env' = env // lib.optionalAttrs (mainProgram != null) { NIX_MAIN_PROGRAM = mainProgram; };
```

## outputs env var ordering

The `outputs` env var preserves the user's list order with "out" first:
`outputs = ["out" "dev" "man" "doc" "info"]`. The ATerm outputs *section* is
alphabetically sorted, but the env var mirrors the source `.nix` file order.

## separateDebugInfo

When `separateDebugInfo = true` on Linux:
1. Adds "debug" to the outputs list
2. Adds `separate-debug-info.sh` to nativeBuildInputs
3. The setup hook creates `.build-id` directory with debug symbols

## input_drvs output filtering

Multi-output packages may only use a subset of outputs. The `input_drvs` dict
specifies which outputs each dependency contributes:
- Single-output deps: always `["out"]`
- Multi-output deps: only the outputs actually referenced
  - Example: perl has `["out", "man", "devdoc"]` but bison only uses `["out"]`
  - Example: zlib has `["dev", "out", "static"]` but perl only uses `["dev", "out"]`
