# Nix Multiline String ('' '') Whitespace Stripping

## The Rule

Nix `''...''` strings strip the **minimum indentation** from all non-empty lines.
The first line (after the opening `''`) always starts with a newline, which is
then stripped because the first "content" line sets the indentation baseline.

## Example: bash NIX_CFLAGS_COMPILE

```nix
env.NIX_CFLAGS_COMPILE = ''
  -DSYS_BASHRC="/etc/bashrc"
  -DSYS_BASH_LOGOUT="/etc/bash_logout"
''
+ ''
  -DDEFAULT_PATH_VALUE="/no-such-path"
  -DSTANDARD_UTILS_PATH="/no-such-path"
''
+ ''
  -DNON_INTERACTIVE_LOGIN_SHELLS
  -DSSH_SOURCE_BASHRC
'';
```

Each `''...''` block produces:
- Block 1: `-DSYS_BASHRC="/etc/bashrc"\n-DSYS_BASH_LOGOUT="/etc/bash_logout"\n`
- Block 2: `-DDEFAULT_PATH_VALUE="/no-such-path"\n-DSTANDARD_UTILS_PATH="/no-such-path"\n`
- Block 3: `-DNON_INTERACTIVE_LOGIN_SHELLS\n-DSSH_SOURCE_BASHRC\n`

Concatenated result starts with `-DSYS_BASHRC` (no leading `\n`), and has no
`\n\n` gaps between blocks.

## Common Python Mistake

```python
# WRONG — adds leading \n and \n\n between sections
nix_cflags = (
    '\n-DSYS_BASHRC="/etc/bashrc"\n'
    '\n-DDEFAULT_PATH_VALUE="/no-such-path"\n'
)

# CORRECT — each Nix block strips to just the content lines
nix_cflags = (
    '-DSYS_BASHRC="/etc/bashrc"\n'
    '-DDEFAULT_PATH_VALUE="/no-such-path"\n'
)
```

## Key Insight

When converting Nix `''...''` + `''...''` concatenation to Python, each block
produces content that starts directly with the first non-empty line and ends
with `\n`. No extra newlines between blocks.
