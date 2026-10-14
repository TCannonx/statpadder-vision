"""The `spv` command line."""

from __future__ import annotations

import argparse
import sys

from spv import __version__


def _not_implemented(args: argparse.Namespace) -> int:
    print(f"spv {args.command}: not implemented yet", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spv", description=__doc__)
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    sub = parser.add_subparsers(dest="command")
    for name, help_text in [
        ("process", "turn a match video into a .sptrack file"),
        ("check", "run the regression check"),
        ("clip", "manage reference clips"),
        ("data", "fetch public data"),
    ]:
        sub.add_parser(name, help=help_text).set_defaults(func=_not_implemented)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"spv {__version__}")
        return 0
    if args.command is None:
        parser.print_help()
        return 2
    return args.func(args)
