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


def _data_fetch(args: argparse.Namespace) -> int:
    from spv.config import data_dir
    from spv.sim.tracks import ensure_metrica

    for game in args.game or [1, 2]:
        home, away = ensure_metrica(game, data_dir())
        print(f"metrica game {game}: {home.parent}")
    return 0


def _check(args: argparse.Namespace) -> int:
    from spv.check.measures import compare, load_baseline, results_table, update_baseline
    from spv.check.suites import SUITES
    from spv.config import REPO_ROOT

    failed = False
    names = list(SUITES) if args.suite == "all" else [args.suite]
    for name in names:
        measures = SUITES[name]()
        if measures is None:
            print(f"## {name}: skipped (no data configured)\n")
            continue
        baseline_path = REPO_ROOT / "tests" / "baselines" / f"{name}.json"
        if args.update_baselines:
            try:
                outcomes = update_baseline(baseline_path, measures)
            except ValueError as exc:
                print(f"spv check: {exc}", file=sys.stderr)
                return 1
        else:
            outcomes = compare(measures, load_baseline(baseline_path))
        table = results_table(outcomes)
        results_path = REPO_ROOT / "tests" / "results" / f"{name}.md"
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(f"# spv check: {name}\n\n{table}", encoding="utf-8")
        print(f"## {name}\n\n{table}")
        failed |= any(o.status in ("worse", "missing") for o in outcomes)
    return 1 if failed else 0


def _clip_add(args: argparse.Namespace) -> int:
    from spv.check.suites import add_clip
    from spv.config import REPO_ROOT

    add_clip(args.name, args.path, REPO_ROOT)
    print(f"registered {args.name}: metadata in tests/clips/{args.name}.json, path in local.config.json")
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
    check = sub.choices["check"]
    check.add_argument("--suite", choices=["all", "sim", "clips"], default="all")
    check.add_argument("--update-baselines", action="store_true",
                       help="save new and better values (refused if anything got worse)")
    check.set_defaults(func=_check)
    clip_sub = sub.choices["clip"].add_subparsers(dest="clip_command", required=True)
    clip_add = clip_sub.add_parser("add", help="register a reference clip (its path stays in local.config.json)")
    clip_add.add_argument("name")
    clip_add.add_argument("path", type=Path)
    clip_add.set_defaults(func=_clip_add)
    data_sub = sub.choices["data"].add_subparsers(dest="data_command", required=True)
    fetch = data_sub.add_parser("fetch", help="download public tracking data")
    fetch.add_argument("source", choices=["metrica"])
    fetch.add_argument("--game", type=int, action="append", help="Metrica sample game (default 1 and 2)")
    fetch.set_defaults(func=_data_fetch)
    from spv.truth.cli import register_truth

    register_truth(sub)
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
