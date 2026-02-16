"""Parse and serialize Nix .drv files (ATerm format).

ATerm derivation format:
    Derive(
        [("out","/nix/store/...","",""), ...],       # outputs
        [("/nix/store/...drv",["out"]), ...],         # inputDrvs
        ["/nix/store/...", ...],                      # inputSrcs
        "x86_64-linux",                               # platform
        "/nix/store/...-bash",                        # builder
        ["--", ...],                                  # args
        [("key","value"), ...]                        # env
    )
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
    """Compute the hash used for output path computation.

    For fixed-output derivations (single output "out" with hash_algo set),
    returns sha256("fixed:out:<hashAlgo>:<hashValue>:").

    For other derivations, replaces each input derivation path with its
    modular hash, then hashes the masked ATerm.

    drv_hashes: map from input .drv path to its modular hash (from recursive calls)
    """
    drv_hashes = drv_hashes or {}

    # Fixed-output check
    if (
        len(drv.outputs) == 1
        and "out" in drv.outputs
        and drv.outputs["out"].hash_algo != ""
    ):
        o = drv.outputs["out"]
        return sha256(f"fixed:out:{o.hash_algo}:{o.hash_value}:".encode())

    # Build a masked derivation: replace output paths with "" and input drv paths with hashes
    masked = Derivation(
        outputs={name: DerivationOutput("", o.hash_algo, o.hash_value) for name, o in drv.outputs.items()},
        input_drvs={},
        input_srcs=list(drv.input_srcs),
        platform=drv.platform,
        builder=drv.builder,
        args=list(drv.args),
        env={k: v for k, v in drv.env.items()},
    )

    # Replace input drv paths with their modular hashes
    for drv_path in sorted(drv.input_drvs):
        if drv_path in drv_hashes:
            hash_hex = drv_hashes[drv_path].hex()
        else:
            raise ValueError(f"missing hash for input derivation: {drv_path}")
        masked.input_drvs[hash_hex] = sorted(drv.input_drvs[drv_path])

    return sha256(serialize(masked).encode())
