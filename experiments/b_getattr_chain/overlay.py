"""Overlay pattern via __getattr__ delegation chain.

Direct translation of Nix's overlay system:
    overlay = final: prev: { gcc = mkGcc { shell = prev.shell; }; };

Each Overlay wraps a previous layer. __getattr__ delegates to prev
for attributes not overridden in this layer. Overlay functions receive
both `final` (the outermost composed set) and `prev` (the set before
this overlay), matching Nix's two-argument overlay signature.

    base = AttrSet({"shell": ..., "tools": ..., "app": ...})
    stage1 = Overlay(base, lambda final, prev: {"tools": mk(deps=[prev.shell])})
    stage2 = Overlay(stage1, lambda final, prev: {"shell": mk(deps=[prev.tools])})

    stage2.app  # delegates to base.app, which uses final.shell/final.tools
"""


class AttrSet:
    """Base attribute set — a dict-like object with attribute access.

    All values are thunks (zero-arg callables) that receive `final`
    when evaluated. This provides lazy evaluation + open recursion.
    """

    def __init__(self, thunks: dict):
        # Store in object's __dict__ directly to avoid __getattr__ interception
        object.__setattr__(self, '_thunks', thunks)
        object.__setattr__(self, '_cache', {})
        object.__setattr__(self, '_final', self)

    def _set_final(self, final):
        """Propagate the outermost (final) reference down the chain."""
        object.__setattr__(self, '_final', final)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        cache = object.__getattribute__(self, '_cache')
        if name in cache:
            return cache[name]
        thunks = object.__getattribute__(self, '_thunks')
        if name not in thunks:
            raise AttributeError(f"no package '{name}' in this set")
        final = object.__getattribute__(self, '_final')
        result = thunks[name](final)
        cache[name] = result
        return result


class Overlay:
    """An overlay that wraps a previous set, overriding some attributes.

    The overlay function receives (final, prev) and returns a dict of
    thunks. Attributes not in the overlay delegate to prev.
    """

    def __init__(self, prev, overlay_fn):
        """
        Args:
            prev: the previous AttrSet or Overlay
            overlay_fn: callable(final, prev) -> dict of thunks
                Each thunk is callable(final) -> Package
        """
        object.__setattr__(self, '_prev', prev)
        object.__setattr__(self, '_overlay_fn', overlay_fn)
        object.__setattr__(self, '_cache', {})
        object.__setattr__(self, '_thunks', None)  # computed lazily
        object.__setattr__(self, '_final', self)

    def _set_final(self, final):
        """Propagate final reference through the chain."""
        object.__setattr__(self, '_final', final)
        prev = object.__getattribute__(self, '_prev')
        prev._set_final(final)

    def _get_thunks(self):
        thunks = object.__getattribute__(self, '_thunks')
        if thunks is not None:
            return thunks
        overlay_fn = object.__getattribute__(self, '_overlay_fn')
        final = object.__getattribute__(self, '_final')
        prev = object.__getattribute__(self, '_prev')
        thunks = overlay_fn(final, prev)
        object.__setattr__(self, '_thunks', thunks)
        return thunks

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        cache = object.__getattribute__(self, '_cache')
        if name in cache:
            return cache[name]
        thunks = self._get_thunks()
        if name in thunks:
            final = object.__getattribute__(self, '_final')
            result = thunks[name](final)
        else:
            prev = object.__getattribute__(self, '_prev')
            result = getattr(prev, name)
        cache[name] = result
        return result


def compose(*layers):
    """Compose an AttrSet base with zero or more Overlay layers.

    Sets the final reference on all layers so open recursion works.
    Returns the outermost layer.
    """
    if not layers:
        raise ValueError("need at least one layer")
    top = layers[0]
    for layer in layers[1:]:
        object.__setattr__(layer, '_prev', top)
        top = layer
    top._set_final(top)
    return top
