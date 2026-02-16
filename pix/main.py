#!/usr/bin/env python3
"""pix — Nix functionality in Python."""

import argparse
import json
import sys

from pix import base32, hash as nixhash, nar, store_path, derivation, daemon


def cmd_hash_path(args):
    h = nar.nar_hash(args.path)
    if args.base32:
        print(f"sha256:{base32.encode(h)}")
    else:
        print(f"sha256:{h.hex()}")


def cmd_hash_file(args):
    import hashlib
    data = open(args.path, "rb").read()
    h = hashlib.sha256(data).digest()
    if args.base32:
        print(f"sha256:{base32.encode(h)}")
    else:
        print(f"sha256:{h.hex()}")


def cmd_store_path(args):
    h = nar.nar_hash(args.path)
    name = args.name or args.path.rstrip("/").split("/")[-1]
    sp = store_path.make_source_store_path(name, h)
    print(sp)


def cmd_drv_show(args):
    text = open(args.drv_path).read()
    drv = derivation.parse(text)
    info = {
        "outputs": {k: {"path": v.path, "hashAlgo": v.hash_algo, "hash": v.hash_value} for k, v in drv.outputs.items()},
        "inputDrvs": drv.input_drvs,
        "inputSrcs": drv.input_srcs,
        "platform": drv.platform,
        "builder": drv.builder,
        "args": drv.args,
        "env": drv.env,
    }
    json.dump(info, sys.stdout, indent=2)
    print()


def cmd_path_info(args):
    with daemon.DaemonConnection() as conn:
        info = conn.query_path_info(args.path)
        print(f"deriver: {info.deriver}")
        print(f"nar-hash: {info.nar_hash}")
        print(f"nar-size: {info.nar_size}")
        print(f"references: {' '.join(info.references)}")
        print(f"sigs: {' '.join(info.sigs)}")


def cmd_is_valid(args):
    with daemon.DaemonConnection() as conn:
        valid = conn.is_valid_path(args.path)
        print("valid" if valid else "invalid")
        sys.exit(0 if valid else 1)


def cmd_add_text(args):
    content = sys.stdin.read() if args.content == "-" else args.content
    with daemon.DaemonConnection() as conn:
        path = conn.add_text_to_store(args.name, content)
        print(path)


def cmd_build(args):
    with daemon.DaemonConnection() as conn:
        conn.build_paths(args.paths)
        print("build succeeded")


def main():
    parser = argparse.ArgumentParser(prog="pix", description="Nix functionality in Python")
    sub = parser.add_subparsers(dest="command")

    # hash-path
    p = sub.add_parser("hash-path", help="Hash a path in NAR format")
    p.add_argument("path")
    p.add_argument("--base32", action="store_true")
    p.set_defaults(func=cmd_hash_path)

    # hash-file
    p = sub.add_parser("hash-file", help="Hash a file (flat, not NAR)")
    p.add_argument("path")
    p.add_argument("--base32", action="store_true")
    p.set_defaults(func=cmd_hash_file)

    # store-path
    p = sub.add_parser("store-path", help="Compute store path for a local path")
    p.add_argument("path")
    p.add_argument("--name", help="Override the store name")
    p.set_defaults(func=cmd_store_path)

    # drv-show
    p = sub.add_parser("drv-show", help="Show parsed .drv file as JSON")
    p.add_argument("drv_path")
    p.set_defaults(func=cmd_drv_show)

    # path-info
    p = sub.add_parser("path-info", help="Query path info from daemon")
    p.add_argument("path")
    p.set_defaults(func=cmd_path_info)

    # is-valid
    p = sub.add_parser("is-valid", help="Check if a store path is valid")
    p.add_argument("path")
    p.set_defaults(func=cmd_is_valid)

    # add-text
    p = sub.add_parser("add-text", help="Add text to the store")
    p.add_argument("name")
    p.add_argument("content", nargs="?", default="-", help="Text content (or - for stdin)")
    p.set_defaults(func=cmd_add_text)

    # build
    p = sub.add_parser("build", help="Build store paths")
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_build)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
