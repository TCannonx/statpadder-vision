"""The `spv` command line."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from spv import __version__


def _not_implemented(args: argparse.Namespace) -> int:
    print(f"spv {args.command}: not implemented yet", file=sys.stderr)
    return 2


def _process(args: argparse.Namespace) -> int:
    from spv.cache import RunCache
    from spv.job import load_job
    from spv.pipeline import run_pipeline
    from spv.stages import default_stages

    try:
        job = load_job(args.job)
        report = run_pipeline(job, default_stages(), RunCache(job.cache_dir))
        job.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(job.cache_dir / "export" / "match.sptrack", job.output)
        report_path = job.output.with_name(job.output.stem + ".run_report.json")
        report_path.write_text(json.dumps(report.to_json(), indent=1))
    except Exception as exc:  # one line for the analyst, not a traceback
        print(f"spv process: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {job.output}")
    return 0


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
    process = sub.choices["process"]
    process.add_argument("--job", type=Path, required=True, help="path to job.json")
    process.set_defaults(func=_process)
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
