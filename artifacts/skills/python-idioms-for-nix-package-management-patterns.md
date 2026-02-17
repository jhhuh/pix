# Python Idioms for Nix Package Management Patterns

## Mapping Table

| Nix Pattern | Python Idiom | Location |
|---|---|---|
| `callPackage` | `inspect.signature` + `getattr` | `pixpkgs/package_set.py` |
| `pkg.override {}` | `dataclasses.replace` / re-call with merged kwargs | `pixpkgs/drv.py` (`Package.override`) |
| String interpolation context | `__str__` returning output path | `pixpkgs/drv.py` (`Package.__str__`) |
| Lazy attribute set evaluation | `@cached_property` on `PackageSet` subclass | `pixpkgs/package_set.py` |
| `mkDerivation` | `drv()` constructor with 6-step pipeline | `pixpkgs/drv.py` |

## callPackage → inspect.signature + getattr

```python
class PackageSet:
    def call(self, fn):
        sig = inspect.signature(fn)
        kwargs = {}
        for name in sig.parameters:
            kwargs[name] = getattr(self, name)
        return fn(**kwargs)
```

The function declares its dependencies as parameter names. `PackageSet.call()` resolves each name as an attribute on the set. Combined with `@cached_property`, this gives lazy, memoized evaluation.

## override → stored kwargs + re-derivation

```python
@dataclass(frozen=True)
class Package:
    _args: dict   # original kwargs to drv()

    def override(self, **kw):
        merged = {**self._args, **kw}
        return drv(**merged)
```

The `Package` stores its construction arguments. `override()` merges new kwargs and re-derives, exactly mirroring Nix's `pkg.override`.

## String interpolation → __str__

```python
@dataclass(frozen=True)
class Package:
    out: str  # output store path

    def __str__(self):
        return self.out
```

In Nix, `"${pkg}"` evaluates to the package's output path. In Python, `f"{pkg}"` calls `__str__`, achieving the same effect.

## The 6-step drv() pipeline

1. Create `Derivation` with blank output paths
2. Compute `hash_derivation_modulo` (own outputs: `mask_outputs=True`)
3. Compute output paths via `make_output_path`
4. Fill output paths in `.outputs` and `.env`
5. Serialize to ATerm
6. Compute `.drv` store path via `make_text_store_path`
