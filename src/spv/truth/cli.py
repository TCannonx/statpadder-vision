"""`spv truth`: phase P0, checking event files against their videos."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from spv import config
from spv.truth import truth_dir
from spv.truth.split import load_split


def untestable_path() -> Path:
    return truth_dir() / "untestable.json"


def load_untestable() -> dict[str, str]:
    path = untestable_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _match(match_id: str) -> tuple[dict, dict]:
    from spv.truth.events import read_events
    from spv.truth.registry import registered

    matches = registered()
    if match_id not in matches:
        raise ValueError(f"{match_id} is not registered: run spv truth add first")
    events = read_events(Path(matches[match_id]["events"])).events
    return matches[match_id], {e.row_id: e for e in events}


def _event(match_id: str, row: str):
    match, events = _match(match_id)
    if row not in events:
        raise ValueError(f"row {row} is not a kick-off, restart, shot or goal in {match_id}")
    return match, events[row]


def _sheet_dir(match_id: str) -> Path:
    return Path(config.REPO_ROOT) / "runs" / "truth" / match_id


def _add(a) -> int:
    from spv.truth.registry import add_match

    add_match(a.match, a.video, a.events)
    print(f"registered {a.match} (paths in local.config.json only)")
    return 0


def _inventory(a) -> int:
    from spv.truth import truth_dir
    from spv.truth.registry import inventory, inventory_markdown
    from spv.truth.split import load_split

    text = inventory_markdown(inventory(), load_split())
    path = truth_dir() / "inventory.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(text)
    return 0


def _split(a) -> int:
    from spv.truth.registry import inventory
    from spv.truth.split import choose_holdout, save_split

    rows = inventory()
    holdout = choose_holdout(rows)
    path = save_split(holdout, [r["id"] for r in rows], force=a.force)
    print(f"held out: {', '.join(holdout)}; P0 matches: {', '.join(holdout[:3])} ({path.name})")
    return 0


def _events(a) -> int:
    from spv.truth.events import zone

    _, events = _match(a.match)
    for e in sorted(events.values(), key=lambda e: (e.half, e.video_s)):
        if a.kind is None or e.kind == a.kind:
            print(f"{e.row_id}\thalf {e.half}\t{e.video_s:9.1f}\t{e.kind}\t{e.team}\t{zone(e.x, e.y)}")
    return 0


def _sheet(a) -> int:
    from spv.truth.align import half_offset, load_alignment
    from spv.truth.frames import clock, contact_sheet, offsets

    match, e = _event(a.match, a.row)
    base = a.base if a.base is not None else (half_offset(load_alignment(a.match), e.half) or 0.0)
    steps = offsets(a.around)
    times = [e.video_s + base + s for s in steps]
    labels = [f"row {e.row_id} {e.kind} {e.team} | offset {base + s:+.1f} s | video {clock(t)}"
              for s, t in zip(steps, times)]
    name = f"row{e.row_id}_{a.around.replace(':', '_')}_base{base:+.1f}.png"
    print(contact_sheet(Path(match["video"]), times, labels, _sheet_dir(a.match) / name, columns=a.columns))
    return 0


def _mark(a) -> int:
    from spv.truth.align import add_mark, half_offset, half_spread, load_alignment, save_alignment

    _, e = _event(a.match, a.row)
    data = load_alignment(a.match)
    add_mark(data, e.half, e.row_id, e.kind, a.offset)
    save_alignment(a.match, data)
    count = sum(1 for m in data["marks"] if m["half"] == e.half)
    spread = half_spread(data, e.half)
    print(f"half {e.half}: offset {half_offset(data, e.half):+.2f} s from {count} anchors, "
          f"spread {'-' if spread is None else f'{spread:.2f} s'}")
    return 0


def _kit(a) -> int:
    from spv.truth.align import load_alignment, save_alignment, set_kit

    data = load_alignment(a.match)
    set_kit(data, a.team, a.looks)
    save_alignment(a.match, data)
    print(f"team {a.team}: {a.looks}")
    return 0


def _attack(a) -> int:
    from spv.truth.align import add_attack_mark, attack_summary, load_alignment, save_alignment

    _, e = _event(a.match, a.row)
    data = load_alignment(a.match)
    add_attack_mark(data, e.half, e.row_id, e.team, a.goal)
    save_alignment(a.match, data)
    print(attack_summary(data))
    return 0


def _spots(a) -> int:
    from spv.truth.align import half_offset, load_alignment
    from spv.truth.events import zone
    from spv.truth.frames import clock, contact_sheet, offsets
    from spv.truth.spot import load_spot, sample_spot_rows, save_spot, top_up

    match, events = _match(a.match)
    alignment = load_alignment(a.match)
    base = {h: half_offset(alignment, h) for h in (1, 2)}
    missing = [h for h in (1, 2) if base[h] is None]
    if missing:
        raise ValueError(f"align half {missing[0]} first (spv truth mark)")
    kinds = [k.strip() for k in a.kinds.split(",") if k.strip()] if a.kinds else None
    data = load_spot(a.match)
    if not data["rows"]:
        data["rows"] = sample_spot_rows(list(events.values()))
        save_spot(a.match, data)
        sheet_rows = data["rows"]
    else:
        sheet_rows = top_up(data, list(events.values()), exclude={m["row"] for m in alignment["marks"]},
                            kinds=kinds)
        if not sheet_rows:
            print("no rows to add")
            return 0
        save_spot(a.match, data)
    kits = alignment.get("kits", {})
    for row in sheet_rows:
        e = events[row]
        steps = offsets("-2:2:1")
        times = [e.video_s + base[e.half] + s for s in steps]
        title = f"row {row} {e.kind} team {e.team} ({kits.get(e.team, 'kit not noted')}) | {zone(e.x, e.y)}"
        labels = [f"{title} | {s:+.0f} s | {clock(t)}" if s == 0 else f"{s:+.0f} s | {clock(t)}"
                  for s, t in zip(steps, times)]
        print(contact_sheet(Path(match["video"]), times, labels, _sheet_dir(a.match) / f"spot_row{row}.png",
                            columns=5))
    return 0


def _spot(a) -> int:
    from spv.truth.spot import load_spot, record_verdict, save_spot, spot_score

    data = load_spot(a.match)
    record_verdict(data, a.row, moment=a.moment, kind=a.kind, place=a.place, team=a.team)
    save_spot(a.match, data)
    right, checked, total = spot_score(data)
    print(f"{a.match}: {right} right of {checked} checked ({total} in the sample)")
    return 0


def _report(a) -> int:
    from spv.truth.align import load_alignment
    from spv.truth.report import is_go, match_result, p0_report

    split = load_split()
    if not split:
        raise ValueError("no split yet: run spv truth split first")
    results = {m: match_result(load_alignment(m), _load_spot(m)) for m in split["p0"]}
    untestable = load_untestable()
    text = p0_report(results, untestable)
    path = truth_dir() / "p0_report.md"
    if path.exists():
        old = path.read_text(encoding="utf-8").splitlines(keepends=True)
        notes = next((i for i, line in enumerate(old) if line.strip() == "## Notes"), None)
        if notes is not None:
            text += "\n" + "".join(old[notes:])
    path.write_text(text, encoding="utf-8")
    print(text)
    return 0 if is_go(results, untestable) else 1


def _untestable(a) -> int:
    from spv.truth.registry import registered

    if not a.reason.strip():
        raise ValueError("give a reason: --reason must not be empty")
    split = load_split()
    if not split:
        raise ValueError("no split yet: run spv truth split first")
    if a.match not in registered():
        raise ValueError(f"{a.match} is not registered: run spv truth add first")
    if a.match not in split["p0"]:
        raise ValueError(f"{a.match} is not a P0 match ({', '.join(split['p0'])})")
    data = load_untestable()
    data[a.match] = a.reason
    path = untestable_path()
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{a.match}: not testable ({a.reason})")
    return 0


def _load_spot(match_id: str) -> dict:
    from spv.truth.spot import load_spot

    return load_spot(match_id)


def _score_dir() -> Path:
    return truth_dir() / "score"


def _label(label: str) -> str:
    import re

    if not re.fullmatch(r"[a-z0-9-]{1,40}", label):
        raise ValueError("--label must be 1-40 characters: lower-case letters, digits, hyphens")
    return label


def _score(a) -> int:
    from spv.truth.align import half_offset, load_alignment
    from spv.truth.events import read_events, team_names
    from spv.truth.registry import registered
    from spv.truth.score import score_markdown, score_match, team_map

    label = _label(a.label)
    matches = registered()
    if a.match not in matches:
        raise ValueError(f"{a.match} is not registered: run spv truth add first")
    truth_path, pred_path = Path(matches[a.match]["events"]), Path(a.pred)
    truth, pred = read_events(truth_path).events, read_events(pred_path).events
    alignment = load_alignment(a.match)
    saved = {h: half_offset(alignment, h) for h in (1, 2)}
    unaligned = [h for h in (1, 2) if saved[h] is None]
    if unaligned and not a.assume_zero_offset:
        raise ValueError(f"half {unaligned[0]} of {a.match} has no saved offset: run spv truth mark, "
                         "or pass --assume-zero-offset")
    offsets = {h: 0.0 if v is None else v for h, v in saved.items()}
    mapping = team_map(team_names(truth_path), team_names(pred_path))
    result = score_match(truth, pred, offsets, mapping)
    text = score_markdown(a.match, label, result)
    out = _score_dir()
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.match}-{label}.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n",
                                                        encoding="utf-8")
    (out / f"{a.match}-{label}.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


def _score_pool(a) -> int:
    from spv.truth.score import pool, score_markdown

    label = _label(a.label)
    import re

    pattern = re.compile(r"m\d{2}-" + re.escape(label) + r"\.json")
    files = sorted(f for f in _score_dir().glob("*.json") if pattern.fullmatch(f.name))
    if not files:
        raise ValueError(f"no scores with label {label}: run spv truth score first")
    text = score_markdown("pool", label, pool([json.loads(f.read_text(encoding="utf-8")) for f in files]))
    (_score_dir() / f"pool-{label}.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


def _guarded(func):
    def run(args: argparse.Namespace) -> int:
        try:
            return func(args)
        except (ValueError, FileNotFoundError, FileExistsError, RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"spv truth: {exc}", file=sys.stderr)
            return 1
    return run


def register_truth(sub: argparse._SubParsersAction) -> None:
    truth = sub.add_parser("truth", help="check event files against their videos (phase P0)")
    t = truth.add_subparsers(dest="truth_command", required=True)

    def command(name: str, help_text: str, func, match: bool = True) -> argparse.ArgumentParser:
        p = t.add_parser(name, help=help_text)
        if match:
            p.add_argument("match", help="anonymous match id, e.g. m01")
        p.set_defaults(func=_guarded(func))
        return p

    p = command("add", "register a match: its video and its event file", _add)
    p.add_argument("video", type=Path)
    p.add_argument("events", type=Path)
    command("inventory", "write tests/truth/inventory.md", _inventory, match=False)
    p = command("split", "choose and fix the held-out matches", _split, match=False)
    p.add_argument("--force", action="store_true", help="replace the split (only if Thomas agrees)")
    p = command("events", "list a match's kick-offs, restarts, shots and goals", _events)
    p.add_argument("--kind")
    p = command("sheet", "contact sheet of frames around a row (written to runs/)", _sheet)
    p.add_argument("--row", required=True)
    p.add_argument("--around", default="-3:3:0.5", help="offsets from:to:step; write --around=-60:60:4")
    p.add_argument("--base", type=float, help="offset to centre on (default: the half's saved offset, else 0)")
    p.add_argument("--columns", type=int, default=4)
    p = command("mark", "record the offset at which a row happens in the video", _mark)
    p.add_argument("--row", required=True)
    p.add_argument("--offset", type=float, required=True, help="video time minus event file time, in seconds")
    p = command("kit", "record what a team wears", _kit)
    p.add_argument("--team", choices=["A", "B"], required=True)
    p.add_argument("--looks", required=True)
    p = command("attack", "record which side of the picture a row's team attacks", _attack)
    p.add_argument("--row", required=True)
    p.add_argument("--goal", choices=["left", "right"], required=True)
    p = command("spots", "choose the 20 spot-check rows and make their sheets", _spots)
    p.add_argument("--kinds", help="comma-separated kinds the top-up rows may have, e.g. corner,throw_in")
    p = command("spot", "record a spot-check verdict", _spot)
    p.add_argument("--row", required=True)
    p.add_argument("--moment", choices=["ok", "off", "unseen"], required=True)
    p.add_argument("--kind", choices=["ok", "wrong"], required=True)
    p.add_argument("--place", choices=["ok", "wrong", "unsure"], required=True)
    p.add_argument("--team", choices=["ok", "wrong", "unsure"], required=True)
    p = command("untestable", "record that a P0 match cannot be judged on its footage", _untestable)
    p.add_argument("--reason", required=True)
    command("report", "write tests/truth/p0_report.md with the go / stop verdict", _report, match=False)
    p = command("score", "score a prediction file against a match's truth", _score)
    p.add_argument("pred", type=Path)
    p.add_argument("--label", required=True)
    p.add_argument("--assume-zero-offset", action="store_true",
                   help="score even though a half has no saved offset (treated as 0 s)")
    p = command("score-pool", "pool every score with a label", _score_pool, match=False)
    p.add_argument("--label", required=True)
