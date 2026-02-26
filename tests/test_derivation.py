"""Tests for .drv ATerm parsing and serialization."""

from pix.derivation import parse, serialize, Derivation, DerivationOutput, hash_derivation_modulo


MINIMAL_DRV = (
    'Derive('
    '[("out","/nix/store/abc-hello","","")],'
    '[("/nix/store/xyz.drv",["out"])],'
    '["/nix/store/src"],'
    '"x86_64-linux",'
    '"/nix/store/bash",'
    '["--build"],'
    '[("key","value"),("out","/nix/store/abc-hello")]'
    ')'
)


def test_parse_minimal():
    drv = parse(MINIMAL_DRV)
    assert "out" in drv.outputs
    assert drv.outputs["out"].path == "/nix/store/abc-hello"
    assert drv.outputs["out"].hash_algo == ""
    assert drv.outputs["out"].hash_value == ""
    assert drv.input_drvs == {"/nix/store/xyz.drv": ["out"]}
    assert drv.input_srcs == ["/nix/store/src"]
    assert drv.platform == "x86_64-linux"
    assert drv.builder == "/nix/store/bash"
    assert drv.args == ["--build"]
    assert drv.env == {"key": "value", "out": "/nix/store/abc-hello"}


def test_roundtrip():
    drv = parse(MINIMAL_DRV)
    text = serialize(drv)
    drv2 = parse(text)
    assert drv == drv2


def test_serialize_sorted():
    """Outputs and env keys should be sorted in serialized form."""
    drv = Derivation(
        outputs={"z": DerivationOutput("pz", "", ""), "a": DerivationOutput("pa", "", "")},
        env={"z": "1", "a": "2"},
    )
    text = serialize(drv)
    # 'a' should appear before 'z' in outputs
    assert text.index('"a"') < text.index('"z"')


def test_escape_roundtrip():
    """Strings with special characters survive parse/serialize."""
    drv = Derivation(
        outputs={"out": DerivationOutput("/nix/store/x", "", "")},
        env={"script": 'echo "hello\\nworld"'},
    )
    text = serialize(drv)
    drv2 = parse(text)
    assert drv2.env["script"] == drv.env["script"]


def test_hash_derivation_modulo_fixed_output():
    """Fixed-output derivations hash to sha256('fixed:out:<algo>:<hash>:<path>')."""
    drv = Derivation(
        outputs={"out": DerivationOutput("/nix/store/x", "sha256", "abc123")},
    )
    h = hash_derivation_modulo(drv)
    from pix.hash import sha256
    expected = sha256(b"fixed:out:sha256:abc123:/nix/store/x")
    assert h == expected


def test_parse_empty_lists():
    text = 'Derive([("out","/nix/store/x","","")],[],[],"","",[][("out","/nix/store/x")])'
    # This has a missing comma before the last list — let's use valid ATerm
    text = 'Derive([("out","/nix/store/x","","")],[],[],"","",[],' \
           '[("out","/nix/store/x")])'
    drv = parse(text)
    assert drv.input_drvs == {}
    assert drv.input_srcs == []
    assert drv.args == []
