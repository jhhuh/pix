"""Tests for store path computation."""

from pix.store_path import make_text_store_path, make_source_store_path, make_store_path, STORE_DIR
from pix.hash import sha256


def test_text_store_path_format():
    """Store path has correct format: /nix/store/<32-char-hash>-<name>."""
    path = make_text_store_path("hello.txt", b"hello world")
    assert path.startswith(STORE_DIR + "/")
    rest = path[len(STORE_DIR) + 1:]
    hash_part, name = rest.split("-", 1)
    assert len(hash_part) == 32
    assert name == "hello.txt"


def test_text_store_path_deterministic():
    """Same inputs always produce the same store path."""
    p1 = make_text_store_path("test", b"content")
    p2 = make_text_store_path("test", b"content")
    assert p1 == p2


def test_text_store_path_content_sensitive():
    """Different content produces different paths."""
    p1 = make_text_store_path("test", b"aaa")
    p2 = make_text_store_path("test", b"bbb")
    assert p1 != p2


def test_text_store_path_name_sensitive():
    """Different names produce different paths."""
    p1 = make_text_store_path("foo", b"content")
    p2 = make_text_store_path("bar", b"content")
    assert p1 != p2


def test_source_store_path_format():
    """Source store paths also have the correct format."""
    nar_h = sha256(b"some nar data")
    path = make_source_store_path("my-source", nar_h)
    assert path.startswith(STORE_DIR + "/")
    rest = path[len(STORE_DIR) + 1:]
    hash_part, name = rest.split("-", 1)
    assert len(hash_part) == 32
    assert name == "my-source"
