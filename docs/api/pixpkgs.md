# pixpkgs

A nixpkgs-like package set built on pix's low-level primitives. Maps Nix patterns to Python idioms.

## `drv()`

```python
from pixpkgs import drv

pkg = drv(
    name="hello",
    builder="/bin/sh",
    args=["-c", "echo hello > $out"],
)
```

### Signature

```python
def drv(
    name: str,
    builder: str,
    system: str = "x86_64-linux",
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    output_names: list[str] | None = None,
    deps: list[Package] | None = None,
    srcs: list[str] | None = None,
) -> Package
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `name` | — | Package name (becomes the store path suffix) |
| `builder` | — | Path to the builder executable |
| `system` | `"x86_64-linux"` | Build platform |
| `args` | `[]` | Arguments to the builder |
| `env` | `{}` | Extra environment variables |
| `output_names` | `["out"]` | Output names |
| `deps` | `[]` | Package dependencies (added as `inputDrvs`) |
| `srcs` | `[]` | Input source store paths |

### Pipeline

`drv()` runs the full 6-step derivation pipeline internally:

```
1. Create Derivation with blank output paths
2. Collect input derivation hashes (mask_outputs=False)
3. hashDerivationModulo (mask_outputs=True for self)
4. make_output_path → fill output paths into .outputs and .env
5. serialize to ATerm
6. make_text_store_path → compute .drv store path
```

Standard env vars (`name`, `builder`, `system`, output names) are added automatically, matching what Nix's `derivation` builtin does.

## `Package`

A frozen dataclass returned by `drv()`.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Package name |
| `drv` | `Derivation` | The underlying pix Derivation object |
| `drv_path` | `str` | Store path of the `.drv` file |
| `outputs` | `dict[str, str]` | Output name → store path mapping |

### `Package.out`

```python
pkg.out  # "/nix/store/<hash>-hello"
```

Shortcut to `pkg.outputs["out"]` — the default output path.

### `Package.__str__`

```python
f"echo {pkg} > $out"  # embeds the output path
```

Returns `pkg.out`. This mirrors Nix's string interpolation context — using `${pkg}` in Nix gives the package's default output path.

### `Package.override()`

```python
pkg2 = pkg.override(name="hello-custom", env={"CFLAGS": "-O2"})
```

Re-derives the package with changed arguments. Like `pkg.override` in Nix — creates a new Package with a fresh derivation hash.

## `PackageSet`

Base class for defining a set of interdependent packages with automatic dependency injection.

```python
from pixpkgs import drv, PackageSet, realize
from functools import cached_property

class MyPkgs(PackageSet):
    @cached_property
    def greeting(self):
        return drv(
            name="greeting",
            builder="/bin/sh",
            args=["-c", "echo hello > $out"],
        )

    @cached_property
    def shouter(self):
        return self.call(lambda greeting: drv(
            name="shouter",
            builder="/bin/sh",
            args=["-c", f"read line < {greeting}; echo $line! > $out"],
            deps=[greeting],
        ))

pkgs = MyPkgs()
realize(pkgs.shouter)  # builds greeting first, then shouter
```

### `PackageSet.call(fn)`

Inspects `fn`'s parameter names and looks them up as attributes on `self`. This is the Python equivalent of Nix's `callPackage` pattern — dependencies are injected by name rather than passed explicitly.

```python
# These are equivalent:
pkgs.call(lambda greeting: use(greeting))
use(pkgs.greeting)
```

Combined with `@cached_property`, this gives lazy evaluation — packages are only constructed when first accessed, and memoized thereafter.

## `realize()`

```python
from pixpkgs import realize

output_path = realize(pkg)
# "/nix/store/<hash>-hello"
```

### Signature

```python
def realize(pkg: Package, conn: DaemonConnection | None = None) -> str
```

Builds a package via the Nix daemon:

1. Recursively registers all dependency `.drv` files in the store via `add_text_to_store`
2. Calls `build_paths` to build the package
3. Returns the default output path

If `conn` is not provided, opens and closes a `DaemonConnection` automatically.
