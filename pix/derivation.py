"""Parse and serialize Nix .drv files (ATerm format).

A derivation is Nix's unit of build — it describes how to produce store
paths from inputs. Derivations are stored as .drv files in ATerm format:

    Derive(
        [("out","/nix/store/...","",""), ...],       # outputs
        [("/nix/store/...drv",["out"]), ...],         # inputDrvs
        ["/nix/store/...", ...],                      # inputSrcs
        "x86_64-linux",                               # platform
        "/nix/store/...-bash",                        # builder
        ["--", ...],                                  # args
        [("key","value"), ...]                        # env
    )

Each output is a 4-tuple: (name, path, hashAlgo, hash).
  - Normal outputs: hashAlgo and hash are "" — the path is computed by Nix
  - Fixed outputs (fetchurl): hashAlgo is "sha256" or "r:sha256",
    hash is the expected content hash. "r:" means recursive (NAR hash).

See: nix/src/libstore/derivations.cc
"""

from dataclasses import dataclass, field
from pix.hash import sha256


@dataclass
class DerivationOutput:
    path: str
    hash_algo: str  # "" for non-fixed-output
    hash_value: str  # "" for non-fixed-output


@dataclass
class Derivation:
    outputs: dict[str, DerivationOutput] = field(default_factory=dict)
    input_drvs: dict[str, list[str]] = field(default_factory=dict)  # drv_path -> [output_names]
    input_srcs: list[str] = field(default_factory=list)
    platform: str = ""
    builder: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


# --- ATerm parser ---

class _Parser:
    def __init__(self, s: str):
        self.s = s
        self.pos = 0

    def peek(self) -> str:
        if self.pos >= len(self.s):
            raise ValueError("unexpected end of input")
        return self.s[self.pos]

    def expect(self, ch: str) -> None:
        if self.s[self.pos] != ch:
            raise ValueError(f"expected {ch!r} at pos {self.pos}, got {self.s[self.pos]!r}")
        self.pos += 1

    def expect_str(self, s: str) -> None:
        end = self.pos + len(s)
        if self.s[self.pos:end] != s:
            raise ValueError(f"expected {s!r} at pos {self.pos}")
        self.pos = end

    def parse_string(self) -> str:
        self.expect('"')
        parts: list[str] = []
        while self.s[self.pos] != '"':
            if self.s[self.pos] == '\\':
                self.pos += 1
                ch = self.s[self.pos]
                if ch == 'n':
                    parts.append('\n')
                elif ch == 'r':
                    parts.append('\r')
                elif ch == 't':
                    parts.append('\t')
                else:
                    parts.append(ch)
            else:
                parts.append(self.s[self.pos])
            self.pos += 1
        self.expect('"')
        return "".join(parts)

    def parse_string_list(self) -> list[str]:
        self.expect('[')
        items = []
        while self.peek() != ']':
            if items:
                self.expect(',')
            items.append(self.parse_string())
        self.expect(']')
        return items

    def parse_outputs(self) -> dict[str, DerivationOutput]:
        self.expect('[')
        outputs = {}
        while self.peek() != ']':
            if outputs:
                self.expect(',')
            self.expect('(')
            name = self.parse_string()
            self.expect(',')
            path = self.parse_string()
            self.expect(',')
            hash_algo = self.parse_string()
            self.expect(',')
            hash_value = self.parse_string()
            self.expect(')')
            outputs[name] = DerivationOutput(path, hash_algo, hash_value)
        self.expect(']')
        return outputs

    def parse_input_drvs(self) -> dict[str, list[str]]:
        self.expect('[')
        drvs = {}
        while self.peek() != ']':
            if drvs:
                self.expect(',')
            self.expect('(')
            path = self.parse_string()
            self.expect(',')
            outputs = self.parse_string_list()
            self.expect(')')
            drvs[path] = outputs
        self.expect(']')
        return drvs

    def parse_env(self) -> dict[str, str]:
        self.expect('[')
        env = {}
        while self.peek() != ']':
            if env:
                self.expect(',')
            self.expect('(')
            key = self.parse_string()
            self.expect(',')
            val = self.parse_string()
            self.expect(')')
            env[key] = val
        self.expect(']')
        return env


def parse(drv_text: str) -> Derivation:
    """Parse an ATerm .drv file into a Derivation."""
    p = _Parser(drv_text)
    p.expect_str("Derive(")
    outputs = p.parse_outputs()
    p.expect(',')
    input_drvs = p.parse_input_drvs()
    p.expect(',')
    input_srcs = p.parse_string_list()
    p.expect(',')
    platform = p.parse_string()
    p.expect(',')
    builder = p.parse_string()
    p.expect(',')
    args = p.parse_string_list()
    p.expect(',')
    env = p.parse_env()
    p.expect(')')
    return Derivation(outputs, input_drvs, input_srcs, platform, builder, args, env)


def _escape(s: str) -> str:
    """Escape a string for ATerm output."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def serialize(drv: Derivation) -> str:
    """Serialize a Derivation to ATerm .drv format."""
    parts = ["Derive("]

    # outputs (sorted by name)
    out_parts = []
    for name in sorted(drv.outputs):
        o = drv.outputs[name]
        out_parts.append(f'("{_escape(name)}","{_escape(o.path)}","{_escape(o.hash_algo)}","{_escape(o.hash_value)}")')
    parts.append("[" + ",".join(out_parts) + "]")

    parts.append(",")

    # inputDrvs (sorted by path)
    drv_parts = []
    for path in sorted(drv.input_drvs):
        outs = ",".join(f'"{_escape(o)}"' for o in sorted(drv.input_drvs[path]))
        drv_parts.append(f'("{_escape(path)}",[{outs}])')
    parts.append("[" + ",".join(drv_parts) + "]")

    parts.append(",")

    # inputSrcs (sorted)
    parts.append("[" + ",".join(f'"{_escape(s)}"' for s in sorted(drv.input_srcs)) + "]")

    parts.append(",")
    parts.append(f'"{_escape(drv.platform)}"')
    parts.append(",")
    parts.append(f'"{_escape(drv.builder)}"')
    parts.append(",")

    # args
    parts.append("[" + ",".join(f'"{_escape(a)}"' for a in drv.args) + "]")

    parts.append(",")

    # env (sorted by key)
    env_parts = []
    for key in sorted(drv.env):
        env_parts.append(f'("{_escape(key)}","{_escape(drv.env[key])}")')
    parts.append("[" + ",".join(env_parts) + "]")

    parts.append(")")
    return "".join(parts)


def hash_derivation_modulo(drv: Derivation, drv_hashes: dict[str, bytes] | None = None) -> bytes:
    """Compute the modular hash of a derivation for output path computation.

    The problem: a derivation's output path depends on the derivation hash,
    but the derivation *contains* its own output paths (in the env). This is
    circular. hashDerivationModulo breaks the cycle:

    For FIXED-OUTPUT derivations (fetchurl, etc.):
      The hash depends only on the expected output hash, not on how it's built.
      This is why changing a fetchurl's build deps doesn't change its output path.
      → sha256("fixed:out:<hashAlgo>:<hashValue>:")

    For REGULAR derivations:
      1. Blank all output paths (replace with "")
      2. Replace each input .drv path with its own hashDerivationModulo (recursive)
      3. Serialize the masked derivation to ATerm
      4. SHA-256 hash the result

    This means a derivation's hash depends on the *content* of its inputs,
    not their store paths — which is the key insight that makes Nix's
    content-addressing work.

    See: nix/src/libstore/derivations.cc — hashDerivationModulo()
    """
    drv_hashes = drv_hashes or {}

    # Fixed-output: hash depends only on the expected output, not the build process
    if (
        len(drv.outputs) == 1
        and "out" in drv.outputs
        and drv.outputs["out"].hash_algo != ""
    ):
        o = drv.outputs["out"]
        return sha256(f"fixed:out:{o.hash_algo}:{o.hash_value}:".encode())

    # Regular: mask output paths and replace input drv paths with their hashes
    masked = Derivation(
        outputs={name: DerivationOutput("", o.hash_algo, o.hash_value) for name, o in drv.outputs.items()},
        input_drvs={},
        input_srcs=list(drv.input_srcs),
        platform=drv.platform,
        builder=drv.builder,
        args=list(drv.args),
        env={k: v for k, v in drv.env.items()},
    )

    for drv_path in sorted(drv.input_drvs):
        if drv_path in drv_hashes:
            hash_hex = drv_hashes[drv_path].hex()
        else:
            raise ValueError(f"missing hash for input derivation: {drv_path}")
        masked.input_drvs[hash_hex] = sorted(drv.input_drvs[drv_path])

    return sha256(serialize(masked).encode())
