# Nix Build Sandbox: No Coreutils Available

## The Constraint

Inside a Nix build sandbox, only `/bin/sh` builtins are available. Standard Unix utilities are NOT present unless explicitly provided as build inputs.

**Available** (shell builtins): `echo`, `read`, `test`, `[`, `printf`, `set`, `export`, `eval`, `exec`, `shift`, `while`, `for`, `if`, `case`

**NOT available**: `cat`, `tr`, `cp`, `mv`, `mkdir -p`, `sed`, `awk`, `grep`, `cut`, `head`, `tail`, `wc`

## Common Replacements

```bash
# Instead of: cat file
read line < file; echo "$line"    # single line
while read line; do echo "$line"; done < file  # multi-line

# Instead of: cp src dst
read content < src; echo "$content" > dst

# Instead of: echo "text" | tr a-z A-Z
# No general replacement — compute the value in the builder script directly

# Instead of: mkdir -p dir/subdir
# Provide coreutils as a build input, or restructure to avoid it
```

## How It Was Discovered

After fixing the `hashDerivationModulo` two-mode bug, builds failed with `cat: not found`, `tr: not found`. The test derivation build scripts used coreutils commands that don't exist in the sandbox.

## Key Lesson

When writing build scripts for Nix derivations (especially test derivations), always use shell builtins or explicitly provide the tools as build dependencies.
