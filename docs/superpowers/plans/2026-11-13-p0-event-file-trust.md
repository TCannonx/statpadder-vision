# P0: Can the Event Files Be Trusted? Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find out, on 3 held-out matches, whether Thomas's event files line up with his videos at a constant offset and are coded well enough to be the truth for everything after, and produce a go / stop verdict.

**Architecture:** A new `spv.truth` package reads Eyeball files and StatPadder CSV exports into anonymous `TruthEvent`s (kick-offs, restarts, shots, goals; teams A/B; no names), registers matches (paths only in the git-ignored `local.config.json`), fixes the held-out split, and makes contact sheets of video frames around chosen rows. The executing agent looks at the sheets and records anchor offsets, attacking direction, kits and spot-check verdicts through `spv truth` commands. Those records (ids and numbers only) live in `tests/truth/`, and `spv truth report` turns them into the P0 verdict.

**Tech Stack:** Python 3.10+, argparse CLI `spv`, ffmpeg/ffprobe, Pillow for contact sheets, pytest.

**Spec:** `docs/superpowers/specs/2026-11-13-events-first-action-plan.md`, section 6.1 step P0 (and sections 2, 3 and 9 risk 1).

## Global Constraints

- The footage shows minors: no video, frame, contact sheet or local drive path may reach git. Sheets go to `runs/` (git-ignored). `tests/test_privacy.py` must keep passing.
- No player or team names in anything committed: matches are `m01`, `m02`, ... and teams are `A` (first team named in the file) and `B`. Kit descriptions ("white shirts, black shorts") are allowed.
- Thomas does no labelling. Every by-eye judgement in Task 7 is made by the executing agent from contact sheets, and the report says so.
- The held-out split is fixed once made. It is never changed without Thomas agreeing.
- P0 gate (spec 6.1): **go** if offsets are constant (anchors within 1 s per half) and at least 18 of 20 spot checks are right, on each of the 3 P0 matches; otherwise **stop and rethink with Thomas**.
- Building and running happen on the RTX 2060 computer, where the videos and event files live.
- Work on a new branch `feature/03-event-truth` from `main`; PR to `main`. `feature/02-camera` stays unmerged.
- This machine's repo files may be CRLF on disk; run Python from Bash, not PowerShell, when a step says `python`/`pytest`/`spv`.

## File Structure

| File | Responsibility |
| --- | --- |
| `src/spv/truth/__init__.py` | `truth_dir()`: where the committed P0 records live (`tests/truth/`) |
| `src/spv/truth/events.py` | `TruthEvent`, `TruthFile`, readers for Eyeball and StatPadder files, `zone()` |
| `src/spv/truth/registry.py` | Register matches (paths in `local.config.json`), inventory table |
| `src/spv/truth/split.py` | Choose and freeze the held-out split |
| `src/spv/truth/frames.py` | Grab frames with ffmpeg, build labelled contact sheets |
| `src/spv/truth/align.py` | Anchor offsets per half, kits, attacking direction |
| `src/spv/truth/spot.py` | Spot-check sample and verdicts |
| `src/spv/truth/report.py` | Per-match result and the P0 report with its verdict |
| `src/spv/truth/cli.py` | `spv truth ...` subcommands |
| `src/spv/cli.py` | Modify: register the `truth` command |
| `pyproject.toml` | Modify: add `pillow` |
| `tests/truth_samples.py` | Made-up Eyeball and StatPadder text for tests (no real file is ever committed) |
| `tests/test_truth_*.py` | Tests per module |
| `tests/truth/` | Committed P0 records: `inventory.md`, `split.json`, `align/mNN.json`, `spot/mNN.json`, `p0_report.md` |

---

### Task 0: Branch

**Files:** none

- [ ] **Step 1: Park the camera-branch work and branch from main**

The checkout is on `feature/02-camera` with an uncommitted `README.md` edit and the untracked spec. Keep both.

```bash
cd <personal OneDrive>/GitHub/statpadder-vision
git stash push README.md -m "camera-step README (feature/02-camera)"
git checkout main && git pull
git checkout -b feature/03-event-truth
git status --short
```

Expected: only `?? docs/superpowers/specs/2026-11-13-events-first-action-plan.md` and `?? docs/superpowers/plans/2026-11-13-p0-event-file-trust.md`.

- [ ] **Step 2: Working environment**

```bash
ffmpeg -version | head -1      # must print a version; install ffmpeg if not
python -m venv .venv            # the old .venv points at another machine: recreate it
.venv/Scripts/python -m pip install -e .[dev]
.venv/Scripts/python -m pytest -q
```

Expected: the existing suite passes (ffmpeg tests no longer skipped).

- [ ] **Step 3: Commit the spec and this plan**

```bash
git add docs/superpowers/specs/2026-11-13-events-first-action-plan.md docs/superpowers/plans/2026-11-13-p0-event-file-trust.md
git commit -m "docs: events-first action plan and P0 plan"
```

---

### Task 1: Read event files into anonymous truth events

**Files:**
- Create: `src/spv/truth/__init__.py`, `src/spv/truth/events.py`, `tests/truth_samples.py`
- Test: `tests/test_truth_events.py`

**Interfaces:**
- Produces:
  - `truth_dir(repo_root: Path | None = None) -> Path`
  - `KINDS: tuple[str, ...]` = `("kick_off", "corner", "free_kick", "throw_in", "goal_kick", "penalty", "shot", "goal")`
  - `TruthEvent(row_id: str, half: int, video_s: float, kind: str, team: str, x: float | None, y: float | None, outcome: str | None = None)` (frozen dataclass)
  - `TruthFile(source: str, rows: int, timed_rows: int, events: list[TruthEvent])` (frozen dataclass; `source` is `"eyeball"` or `"statpadder"`)
  - `read_eyeball(path) -> TruthFile`, `read_statpadder(path) -> TruthFile`, `read_events(path) -> TruthFile`
  - `zone(x: float | None, y: float | None) -> str`
- `tests/truth_samples.py` produces `EYEBALL_SAMPLE`, `EYEBALL_TIMED`, `STATPADDER_SAMPLE` (str).

- [ ] **Step 1: Write the sample files used by tests**

`tests/truth_samples.py` (teams and players are made up):

```python
"""Made-up event files for tests. Never put a real supplier file in the repo: they name minors."""

EYEBALL_SAMPLE = (
    "ID;Half;Event;Player;Team;Video time;Football time;X coordinate;Y coordinate;Details\n"
    '1;1st half;pass;9. Test PLAYER;Alpha;30.0;0;0.5;0.5;{"outcome":"success","restart":"no"}\n'
    '2;1st half;pass_received;7. Next PLAYER;Alpha;31.5;1;0.6;0.4;{"outcome":"success"}\n'
    '3;1st half;pass;4. Other PLAYER;Beta;95.2;65;0.99;0.02;{"outcome":"fail","restart":"corner-kick"}\n'
    '4;1st half;shot;9. Test PLAYER;Alpha;120.0;90;0.9;0.5;{"outcome":"success","on_target":"on","restart":"no","xg":0.3}\n'
    '5;1st half;goal;9. Test PLAYER;Alpha;121.0;91;0.9;0.5;{"goal_type":"open_play"}\n'
    "6;1st half;goal_conceded;-. - -;Beta;121.0;91;0.1;0.5;{}\n"
    '7;1st half;pass;-. - -;Beta;180.0;150;0.5;0.5;{"outcome":"success","restart":"no"}\n'
    '8;1st half;pass;-. - -;Beta;200,5;170;0.3;1.0;{"outcome":"success","restart":"throw-in"}\n'
    '9;2nd half;pass;-. - -;Beta;3000.0;2700;0.5;0.5;{"outcome":"success","restart":"no"}\n'
    '10;2nd half;shot;-. - -;Alpha;3100.0;2800;0.95;0.5;{"outcome":"fail","on_target":"off","restart":"penalty-kick"}\n'
    '11;2nd half;pass;-. - -;Alpha;3200.0;2900;0.1;0.5;{"outcome":"success","restart":"goal-kick"}\n'
    "12;2nd half;pass;-. - -;Beta;;;;;{}\n"
)

# The same file without its one untimed row.
EYEBALL_TIMED = "".join(EYEBALL_SAMPLE.splitlines(keepends=True)[:-1])

STATPADDER_SAMPLE = (
    "period,clock,match_minute,type,team,side,third,x,y,end_x,end_y,player_number,player_name,"
    "flagged,confidence,logged_at,xg,video_ms,outcome,penalty\n"
    "First half,01:05,2,corner,Us,own,final,0.99,0.02,,,7,Test Player,false,,2026-10-01T10:00:00Z,,65000,,\n"
    "First half,05:00,6,shot,Us,own,final,0.88,0.5,,,9,Test Player,false,,2026-10-01T10:04:00Z,0.200,300000,goal,false\n"
    "First half,06:00,7,pass,Them,opposition,middle,0.5,0.5,,,,,false,,2026-10-01T10:05:00Z,,360000,,\n"
    "Second half,01:00,46,shot,Them,opposition,final,0.95,0.5,,,,,false,,2026-10-01T11:00:00Z,0.700,2800000,saved,true\n"
    "Second half,02:00,47,corner,Us,own,final,0.99,0.98,,,,,false,,2026-10-01T11:01:00Z,,,,\n"
)
```

- [ ] **Step 2: Write the failing tests**

`tests/test_truth_events.py`:

```python
from pathlib import Path

import pytest

from spv.truth.events import TruthEvent, read_events, read_eyeball, read_statpadder, zone
from truth_samples import EYEBALL_SAMPLE, STATPADDER_SAMPLE


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8-sig")
    return path


def test_eyeball_kinds_teams_and_times(tmp_path):
    tf = read_eyeball(_write(tmp_path, "e.csv", EYEBALL_SAMPLE))
    assert (tf.source, tf.rows, tf.timed_rows) == ("eyeball", 12, 11)
    got = [(e.row_id, e.half, e.video_s, e.kind, e.team) for e in tf.events]
    assert got == [
        ("1", 1, 30.0, "kick_off", "A"),
        ("3", 1, 95.2, "corner", "B"),
        ("4", 1, 120.0, "shot", "A"),
        ("5", 1, 121.0, "goal", "A"),
        ("7", 1, 180.0, "kick_off", "B"),
        ("8", 1, 200.5, "throw_in", "B"),
        ("9", 2, 3000.0, "kick_off", "B"),
        ("10", 2, 3100.0, "penalty", "A"),
        ("11", 2, 3200.0, "goal_kick", "A"),
    ]
    shot = tf.events[2]
    assert (shot.x, shot.y, shot.outcome) == (0.9, 0.5, "on")


def test_names_are_never_kept(tmp_path):
    text = repr(read_eyeball(_write(tmp_path, "e.csv", EYEBALL_SAMPLE)))
    for name in ("PLAYER", "Alpha", "Beta"):
        assert name not in text


def test_statpadder_export(tmp_path):
    tf = read_statpadder(_write(tmp_path, "s.csv", STATPADDER_SAMPLE))
    assert (tf.source, tf.rows, tf.timed_rows) == ("statpadder", 5, 4)
    got = [(e.row_id, e.half, e.video_s, e.kind, e.team, e.outcome) for e in tf.events]
    assert got == [
        ("r1", 1, 65.0, "corner", "A", None),
        ("r2", 1, 300.0, "shot", "A", "goal"),
        ("r2g", 1, 300.0, "goal", "A", None),
        ("r4", 2, 2800.0, "penalty", "B", "saved"),
    ]
    assert "Test Player" not in repr(tf)


def test_read_events_detects_the_format(tmp_path):
    assert read_events(_write(tmp_path, "e.csv", EYEBALL_SAMPLE)).source == "eyeball"
    assert read_events(_write(tmp_path, "s.csv", STATPADDER_SAMPLE)).source == "statpadder"
    with pytest.raises(ValueError):
        read_events(_write(tmp_path, "x.csv", "a,b,c\n1,2,3\n"))


def test_zone():
    assert zone(0.9, 0.1) == "final third, left (as the team attacks)"
    assert zone(0.5, 0.5) == "middle third, centre (as the team attacks)"
    assert zone(None, 0.5) == "no place"


def test_truth_event_is_frozen():
    event = TruthEvent("1", 1, 1.0, "shot", "A", None, None)
    with pytest.raises(AttributeError):
        event.kind = "goal"
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `.venv/Scripts/python -m pytest tests/test_truth_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spv.truth'`.

- [ ] **Step 4: Write the package and the readers**

`src/spv/truth/__init__.py`:

```python
"""Phase P0: checking event files against their videos."""

from __future__ import annotations

from pathlib import Path

from spv import config


def truth_dir(repo_root: Path | None = None) -> Path:
    """Where the committed P0 records live. Ids and numbers only: no names, paths or frames."""
    return Path(repo_root or config.REPO_ROOT) / "tests" / "truth"
```

`src/spv/truth/events.py`:

```python
"""Trusted events read from an event file, as P0 and the scorer need them.

Only kick-offs, restarts, shots and goals are kept, and never a player's or a team's name:
teams become A (the first team named in the file) and B.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("kick_off", "corner", "free_kick", "throw_in", "goal_kick", "penalty", "shot", "goal")
_RESTARTS = {"corner-kick": "corner", "free-kick": "free_kick", "throw-in": "throw_in", "goal-kick": "goal_kick"}
_HALVES = {"1st half": 1, "2nd half": 2}


@dataclass(frozen=True)
class TruthEvent:
    row_id: str
    half: int  # 1 or 2
    video_s: float  # seconds on the event file's own video clock
    kind: str  # one of KINDS
    team: str  # "A" or "B"
    x: float | None  # 0-1 towards the goal the team attacks
    y: float | None  # 0-1 from the team's left touchline
    outcome: str | None = None  # shots: on / off / blocked (Eyeball) or the app's outcome


@dataclass(frozen=True)
class TruthFile:
    source: str  # "eyeball" or "statpadder"
    rows: int
    timed_rows: int
    events: list[TruthEvent] = field(default_factory=list)


def _number(text: str | None) -> float | None:
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _rows(text: str, delimiter: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return [{k.strip(): (v or "").strip() for k, v in row.items() if isinstance(k, str)} for row in reader]


class _Teams:
    def __init__(self) -> None:
        self.names: list[str] = []

    def letter(self, name: str) -> str | None:
        if not name:
            return None
        if name not in self.names:
            self.names.append(name)
        return "A" if name == self.names[0] else "B"


def read_eyeball(path: Path) -> TruthFile:
    rows = _rows(Path(path).read_text(encoding="utf-8-sig"), ";")
    teams, events, timed = _Teams(), [], 0
    kick_off_due = {1: True, 2: True}  # the first pass of a half, and the first after a goal
    for row in rows:
        half = _HALVES.get(row.get("Half", ""))
        team = teams.letter(row.get("Team", ""))
        t = _number(row.get("Video time"))
        if t is not None:
            timed += 1
        if half is None or team is None or t is None:
            continue
        try:
            details = json.loads(row.get("Details") or "{}")
        except json.JSONDecodeError:
            details = {}
        x, y = _number(row.get("X coordinate")), _number(row.get("Y coordinate"))
        kind, outcome = None, None
        event = row.get("Event", "")
        if event == "pass":
            if kick_off_due[half] and x is not None and 0.4 <= x <= 0.6:
                kind = "kick_off"
            else:
                kind = _RESTARTS.get(details.get("restart", "no"))
            kick_off_due[half] = False
        elif event == "shot":
            kind = "penalty" if details.get("restart") == "penalty-kick" else "shot"
            outcome = details.get("on_target")
        elif event == "goal":
            kind = "goal"
            kick_off_due[half] = True
        if kind:
            events.append(TruthEvent(row.get("ID", ""), half, t, kind, team, x, y, outcome))
    return TruthFile("eyeball", len(rows), timed, events)


def read_statpadder(path: Path) -> TruthFile:
    """A StatPadder match CSV export. Hand-coded matches have corners and shots, not other restarts."""
    rows = _rows(Path(path).read_text(encoding="utf-8-sig"), ",")
    teams, periods, events, timed = _Teams(), [], [], 0
    for i, row in enumerate(rows, start=1):
        period = row.get("period", "")
        if period not in periods:
            periods.append(period)
        half = periods.index(period) + 1
        team = teams.letter(row.get("team", ""))
        ms = _number(row.get("video_ms"))
        if ms is not None:
            timed += 1
        if half > 2 or team is None or ms is None:
            continue
        t, row_id = ms / 1000, f"r{i}"
        x, y = _number(row.get("x")), _number(row.get("y"))
        if row.get("type") == "corner":
            events.append(TruthEvent(row_id, half, t, "corner", team, x, y))
        elif row.get("type") == "shot":
            outcome = row.get("outcome") or None
            kind = "penalty" if row.get("penalty", "").lower() == "true" else "shot"
            events.append(TruthEvent(row_id, half, t, kind, team, x, y, outcome))
            if outcome == "goal":
                events.append(TruthEvent(f"{row_id}g", half, t, "goal", team, x, y))
    return TruthFile("statpadder", len(rows), timed, events)


def read_events(path: Path) -> TruthFile:
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    first = lines[0] if lines else ""
    if "Video time" in first:
        return read_eyeball(path)
    if "video_ms" in first:
        return read_statpadder(path)
    raise ValueError(f"{Path(path).name}: not an Eyeball events file or a StatPadder export")


def zone(x: float | None, y: float | None) -> str:
    if x is None or y is None:
        return "no place"
    third = "own third" if x < 1 / 3 else "middle third" if x < 2 / 3 else "final third"
    flank = "left" if y < 1 / 3 else "centre" if y < 2 / 3 else "right"
    return f"{third}, {flank} (as the team attacks)"
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/Scripts/python -m pytest tests/test_truth_events.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/spv/truth/__init__.py src/spv/truth/events.py tests/truth_samples.py tests/test_truth_events.py
git commit -m "feat(truth): read Eyeball and StatPadder files into anonymous truth events"
```

---

### Task 2: Register matches, inventory, held-out split

**Files:**
- Create: `src/spv/truth/registry.py`, `src/spv/truth/split.py`
- Test: `tests/test_truth_registry.py`

**Interfaces:**
- Consumes: `read_events`, `truth_dir` (Task 1); `spv.config.load_local_config/save_local_config`; `spv.stages.probe.probe_video(path) -> {"duration_s": float, ...}`.
- Produces:
  - `add_match(match_id: str, video: Path, events: Path, repo_root: Path | None = None) -> None`
  - `registered(repo_root: Path | None = None) -> dict[str, dict]` (`{"m01": {"video": str, "events": str}}`)
  - `inventory(repo_root=None, probe=None) -> list[dict]`, each `{"id", "source", "minutes", "rows", "timed_share", "halves", "kinds"}`
  - `inventory_markdown(rows: list[dict], split: dict | None = None) -> str`
  - `SEED = 20261113`, `choose_holdout(rows, n=5, seed=SEED) -> list[str]`
  - `save_split(holdout: list[str], all_ids: list[str], repo_root=None, force=False) -> Path`, `load_split(repo_root=None) -> dict | None` (`{"seed", "holdout", "p0", "train"}`; `p0` is the first 3 of `holdout`)

- [ ] **Step 1: Write the failing tests**

`tests/test_truth_registry.py`:

```python
import pytest

from spv.truth.registry import add_match, inventory, inventory_markdown, registered
from spv.truth.split import choose_holdout, load_split, save_split
from truth_samples import EYEBALL_SAMPLE


def _files(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"not really a video")
    events = tmp_path / "e.csv"
    events.write_text(EYEBALL_SAMPLE, encoding="utf-8-sig")
    return video, events


def test_add_and_inventory(tmp_path):
    video, events = _files(tmp_path)
    add_match("m01", video, events, repo_root=tmp_path)
    assert registered(tmp_path)["m01"] == {"video": str(video.resolve()), "events": str(events.resolve())}
    rows = inventory(tmp_path, probe=lambda p: {"duration_s": 5400.0})
    r = rows[0]
    assert (r["id"], r["source"], r["minutes"], r["rows"], r["timed_share"], r["halves"]) == (
        "m01", "eyeball", 90, 12, 0.917, 2)
    assert r["kinds"]["kick_off"] == 3 and r["kinds"]["corner"] == 1
    assert "| m01 | eyeball | 90 | 12 | 92% | 2 |" in inventory_markdown(rows)


def test_ids_are_anonymous(tmp_path):
    video, events = _files(tmp_path)
    with pytest.raises(ValueError):
        add_match("bohs-u17", video, events, repo_root=tmp_path)


def test_missing_file_is_refused(tmp_path):
    _, events = _files(tmp_path)
    with pytest.raises(FileNotFoundError):
        add_match("m01", tmp_path / "nope.mp4", events, repo_root=tmp_path)


def test_split_is_stable_and_fixed(tmp_path):
    rows = [{"id": f"m{i:02d}", "source": "eyeball", "halves": 2, "timed_share": 1.0} for i in range(1, 11)]
    rows.append({"id": "m11", "source": "statpadder", "halves": 2, "timed_share": 1.0})
    rows.append({"id": "m12", "source": "eyeball", "halves": 1, "timed_share": 1.0})
    holdout = choose_holdout(rows)
    assert len(holdout) == 5 and "m11" not in holdout and "m12" not in holdout
    assert choose_holdout(rows) == holdout
    save_split(holdout, [r["id"] for r in rows], repo_root=tmp_path)
    split = load_split(tmp_path)
    assert split["p0"] == holdout[:3] and len(split["train"]) == 7
    with pytest.raises(FileExistsError):
        save_split(holdout, [r["id"] for r in rows], repo_root=tmp_path)


def test_split_falls_back_to_hand_coded(tmp_path):
    rows = [{"id": "m01", "source": "eyeball", "halves": 2, "timed_share": 1.0},
            {"id": "m02", "source": "statpadder", "halves": 2, "timed_share": 0.99}]
    assert sorted(choose_holdout(rows)) == ["m01", "m02"]
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/Scripts/python -m pytest tests/test_truth_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spv.truth.registry'`.

- [ ] **Step 3: Write the registry**

`src/spv/truth/registry.py`:

```python
"""Matches with a video and a trusted event file. Paths stay in the git-ignored local.config.json."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from spv import config
from spv.truth.events import read_events

ID_PATTERN = re.compile(r"^m\d{2}$")
_KIND_COLUMNS = [("kick_off", "Kick-offs"), ("corner", "Corners"), ("free_kick", "Free kicks"),
                 ("throw_in", "Throw-ins"), ("goal_kick", "Goal kicks"), ("shot", "Shots"), ("goal", "Goals")]


def add_match(match_id: str, video: Path, events: Path, repo_root: Path | None = None) -> None:
    if not ID_PATTERN.match(match_id):
        raise ValueError("match ids are anonymous: m01, m02, ...")
    for path in (video, events):
        if not Path(path).is_file():
            raise FileNotFoundError(f"not found: {Path(path).name}")
    read_events(Path(events))  # refuses a file in neither format
    local = config.load_local_config(repo_root)
    local.setdefault("truth_matches", {})[match_id] = {
        "video": str(Path(video).resolve()), "events": str(Path(events).resolve())}
    config.save_local_config(local, repo_root)


def registered(repo_root: Path | None = None) -> dict[str, dict]:
    return config.load_local_config(repo_root).get("truth_matches", {})


def inventory(repo_root: Path | None = None, probe=None) -> list[dict]:
    if probe is None:
        from spv.stages.probe import probe_video as probe
    rows = []
    for match_id, match in sorted(registered(repo_root).items()):
        tf = read_events(Path(match["events"]))
        rows.append({
            "id": match_id,
            "source": tf.source,
            "minutes": round(probe(Path(match["video"]))["duration_s"] / 60),
            "rows": tf.rows,
            "timed_share": round(tf.timed_rows / tf.rows, 3) if tf.rows else 0.0,
            "halves": len({e.half for e in tf.events}),
            "kinds": dict(Counter(e.kind for e in tf.events)),
        })
    return rows


def inventory_markdown(rows: list[dict], split: dict | None = None) -> str:
    def role(match_id: str) -> str:
        if not split:
            return "-"
        if match_id in split["p0"]:
            return "held out, P0"
        return "held out" if match_id in split["holdout"] else "train"

    head = ["Match", "Source", "Video (min)", "Rows", "Timed", "Halves", *[t for _, t in _KIND_COLUMNS], "Role"]
    lines = ["# Matches with trusted events", "", "| " + " | ".join(head) + " |",
             "| " + " | ".join("---" for _ in head) + " |"]
    for r in rows:
        cells = [r["id"], r["source"], str(r["minutes"]), str(r["rows"]), f"{r['timed_share']:.0%}", str(r["halves"]),
                 *[str(r["kinds"].get(k, 0)) for k, _ in _KIND_COLUMNS], role(r["id"])]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Write the split**

`src/spv/truth/split.py`:

```python
"""The held-out matches: never trained on, never tuned on. Fixed once made."""

from __future__ import annotations

import json
import random
from pathlib import Path

from spv.truth import truth_dir

SEED = 20261113


def split_path(repo_root: Path | None = None) -> Path:
    return truth_dir(repo_root) / "split.json"


def choose_holdout(rows: list[dict], n: int = 5, seed: int = SEED) -> list[str]:
    """Eyeball matches first (full event stream), hand-coded ones only if there are too few.
    The first three returned are the P0 matches."""
    def usable(r: dict) -> bool:
        return r["halves"] == 2 and r["timed_share"] >= 0.95

    eyeball = sorted(r["id"] for r in rows if usable(r) and r["source"] == "eyeball")
    others = sorted(r["id"] for r in rows if usable(r) and r["source"] != "eyeball")
    rng = random.Random(seed)
    picked = rng.sample(eyeball, min(n, len(eyeball)))
    if len(picked) < n:
        picked += rng.sample(others, min(n - len(picked), len(others)))
    return picked


def save_split(holdout: list[str], all_ids: list[str], repo_root: Path | None = None, force: bool = False) -> Path:
    path = split_path(repo_root)
    if path.exists() and not force:
        raise FileExistsError("the split is fixed once made: use --force only if Thomas agrees")
    data = {"seed": SEED, "holdout": holdout, "p0": holdout[:3], "train": sorted(set(all_ids) - set(holdout))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return path


def load_split(repo_root: Path | None = None) -> dict | None:
    path = split_path(repo_root)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/Scripts/python -m pytest tests/test_truth_registry.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/spv/truth/registry.py src/spv/truth/split.py tests/test_truth_registry.py
git commit -m "feat(truth): match registry, inventory and fixed held-out split"
```

---

### Task 3: Contact sheets of video frames

**Files:**
- Create: `src/spv/truth/frames.py`
- Modify: `pyproject.toml` (dependencies)
- Test: `tests/test_truth_frames.py`

**Interfaces:**
- Produces:
  - `offsets(spec: str) -> list[float]` (`"from:to:step"`, inclusive)
  - `clock(t_s: float) -> str` (`"h:mm:ss.s"`)
  - `grab_frame(video: Path, t_s: float, width: int = 480) -> PIL.Image.Image`
  - `contact_sheet(video: Path, times: list[float], labels: list[str], out: Path, columns: int = 4, width: int = 480) -> Path` (a time with no frame gets a grey tile, never an error)

- [ ] **Step 1: Add Pillow**

In `pyproject.toml` change the dependencies line to:

```toml
dependencies = ["numpy>=1.26", "scipy>=1.11", "shapely>=2.0", "pillow>=10"]
```

Run: `.venv/Scripts/python -m pip install -e .[dev]`

- [ ] **Step 2: Write the failing tests**

`tests/test_truth_frames.py`:

```python
import pytest

from spv.truth.frames import clock, contact_sheet, offsets


def test_offsets():
    assert offsets("-2:2:1") == [-2.0, -1.0, 0.0, 1.0, 2.0]
    assert offsets("-1:1:0.5") == [-1.0, -0.5, 0.0, 0.5, 1.0]


@pytest.mark.parametrize("bad", ["1:2", "2:1:1", "0:1:0", "a:b:c"])
def test_offsets_refuses_bad_specs(bad):
    with pytest.raises(ValueError):
        offsets(bad)


def test_clock():
    assert clock(3725.25) == "1:02:05.2"
    assert clock(-3) == "0:00:00.0"


def test_contact_sheet(tiny_video, tmp_path):
    from PIL import Image

    out = contact_sheet(tiny_video, [0.5, 1.0, 1.5, 30.0], ["a", "b", "c", "after the end"],
                        tmp_path / "sheet.png", columns=4, width=160)
    assert Image.open(out).size == (4 * 160, 90 + 22)  # 320x180 scaled to 160x90, plus a label band
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `.venv/Scripts/python -m pytest tests/test_truth_frames.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spv.truth.frames'`.

- [ ] **Step 4: Write the frames module**

`src/spv/truth/frames.py`:

```python
"""Frames and contact sheets from a match video, for checking events by eye.

Sheets show minors: they go to runs/ (git-ignored) and are never committed.
"""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

LABEL_BAND = 22


def offsets(spec: str) -> list[float]:
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError("offsets are from:to:step, for example -3:3:0.5")
    start, stop, step = (float(p) for p in parts)
    if step <= 0 or stop < start:
        raise ValueError("offsets need a positive step and from <= to")
    n = round((stop - start) / step)
    return [round(start + i * step, 3) + 0.0 for i in range(n + 1)]


def clock(t_s: float) -> str:
    t_s = max(t_s, 0.0)
    hours, rest = divmod(t_s, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{int(hours)}:{int(minutes):02d}:{seconds:04.1f}"


def grab_frame(video: Path, t_s: float, width: int = 480) -> Image.Image:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found: install ffmpeg")
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(t_s, 0.0):.3f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, check=True).stdout
    if not out:
        raise ValueError(f"no frame at {t_s:.1f} s")
    return Image.open(io.BytesIO(out)).convert("RGB")


def contact_sheet(video: Path, times: list[float], labels: list[str], out: Path,
                  columns: int = 4, width: int = 480) -> Path:
    if not times or len(times) != len(labels):
        raise ValueError("one label per time, and at least one time")
    frames: list[Image.Image | None] = []
    for t in times:
        try:
            frames.append(grab_frame(video, t, width))
        except (ValueError, subprocess.CalledProcessError):
            frames.append(None)
    tile_w, tile_h = next((f.size for f in frames if f is not None), (width, width * 9 // 16))
    cols = min(columns, len(frames))
    rows = -(-len(frames) // cols)
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + LABEL_BAND)), "black")
    draw = ImageDraw.Draw(sheet)
    for i, (frame, label) in enumerate(zip(frames, labels)):
        x, y = (i % cols) * tile_w, (i // cols) * (tile_h + LABEL_BAND)
        sheet.paste(frame if frame is not None else Image.new("RGB", (tile_w, tile_h), "grey"), (x, y + LABEL_BAND))
        draw.text((x + 4, y + 4), label if frame is not None else f"{label} (no frame)", fill="white")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/Scripts/python -m pytest tests/test_truth_frames.py -v`
Expected: 7 passed (the sheet test skips only if ffmpeg is missing, which Task 0 ruled out).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/spv/truth/frames.py tests/test_truth_frames.py
git commit -m "feat(truth): labelled contact sheets of video frames"
```

---

### Task 4: Alignment records, spot checks and the P0 report

**Files:**
- Create: `src/spv/truth/align.py`, `src/spv/truth/spot.py`, `src/spv/truth/report.py`
- Test: `tests/test_truth_align.py`, `tests/test_truth_spot.py`, `tests/test_truth_report.py`

**Interfaces:**
- Consumes: `TruthEvent`, `truth_dir` (Task 1).
- Produces:
  - `align.py`: `FLIP = {"left": "right", "right": "left"}`; `alignment_path(match_id, repo_root=None) -> Path`; `load_alignment(match_id, repo_root=None) -> dict` (empty: `{"marks": [], "kits": {}, "attack_marks": []}`); `save_alignment(match_id, data, repo_root=None) -> Path`; `add_mark(data, half: int, row: str, kind: str, offset_s: float) -> None`; `half_offset(data, half) -> float | None` (median); `half_spread(data, half) -> float | None` (max - min, needs 2 marks); `set_kit(data, team: str, looks: str) -> None`; `add_attack_mark(data, half: int, row: str, team: str, goal_side: str) -> None`; `attack_summary(data) -> dict[int, dict]` (`{1: {"A": "right", "agree": 3, "of": 3}}`); `attack_consistent(summary, minimum=3) -> bool`.
  - `spot.py`: `TARGETS`; `VERDICTS`; `sample_spot_rows(events: list[TruthEvent], n=20) -> list[str]`; `spot_path(match_id, repo_root=None) -> Path`; `load_spot(match_id, repo_root=None) -> dict` (empty: `{"rows": [], "verdicts": {}}`); `save_spot(match_id, data, repo_root=None) -> Path`; `record_verdict(data, row: str, *, moment: str, kind: str, place: str, team: str) -> None`; `spot_score(data) -> tuple[int, int, int]` (right, checked, total).
  - `report.py`: `SPREAD_LIMIT_S = 1.0`, `SPOT_SHARE = 0.9`, `MIN_MARKS = 3`; `match_result(alignment: dict, spot: dict) -> dict` (`offsets`, `spreads`, `marks`, `attack`, `spot`, `usable: bool`, `reasons: list[str]`); `p0_report(results: dict[str, dict]) -> str`.

A mark's `offset_s` means: **video time = event file time + offset**, for that half.

- [ ] **Step 1: Write the failing tests**

`tests/test_truth_align.py`:

```python
import pytest

from spv.truth.align import (add_attack_mark, add_mark, attack_consistent, attack_summary, half_offset,
                             half_spread, load_alignment, save_alignment, set_kit)


def _empty():
    return {"marks": [], "kits": {}, "attack_marks": []}


def test_offset_and_spread():
    d = _empty()
    add_mark(d, 1, "1", "kick_off", 3.0)
    add_mark(d, 1, "3", "corner", 3.5)
    add_mark(d, 1, "8", "throw_in", 4.0)
    assert half_offset(d, 1) == 3.5 and half_spread(d, 1) == 1.0
    assert half_offset(d, 2) is None and half_spread(d, 2) is None
    add_mark(d, 1, "8", "throw_in", 3.2)  # marking a row again replaces it
    assert half_spread(d, 1) == 0.5 and len(d["marks"]) == 3


def test_save_and_load(tmp_path):
    d = _empty()
    add_mark(d, 2, "9", "kick_off", -12.5)
    set_kit(d, "A", "white shirts, black shorts")
    save_alignment("m01", d, tmp_path)
    assert load_alignment("m01", tmp_path) == d
    assert load_alignment("m02", tmp_path) == _empty()


def test_attack_direction():
    d = _empty()
    add_attack_mark(d, 1, "4", "A", "right")
    add_attack_mark(d, 1, "x", "B", "left")  # B shooting left means A attacks right
    add_attack_mark(d, 1, "y", "A", "right")
    for row in ("p", "q", "r"):
        add_attack_mark(d, 2, row, "A", "left")
    summary = attack_summary(d)
    assert summary[1] == {"A": "right", "agree": 3, "of": 3}
    assert attack_consistent(summary)
    add_attack_mark(d, 2, "z", "A", "right")
    assert not attack_consistent(attack_summary(d))
    with pytest.raises(ValueError):
        add_attack_mark(d, 1, "s", "A", "up")


def test_attack_needs_both_halves_switched():
    d = _empty()
    for row in ("a", "b", "c"):
        add_attack_mark(d, 1, row, "A", "right")
    assert not attack_consistent(attack_summary(d))
    for row in ("d", "e", "f"):
        add_attack_mark(d, 2, row, "A", "right")  # same end both halves: wrong
    assert not attack_consistent(attack_summary(d))
```

`tests/test_truth_spot.py`:

```python
from collections import Counter

import pytest

from spv.truth.events import TruthEvent
from spv.truth.spot import load_spot, record_verdict, sample_spot_rows, save_spot, spot_score


def _events(kinds):
    return [TruthEvent(str(i), 1 if i < len(kinds) // 2 else 2, float(i * 10), k, "A", 0.5, 0.5)
            for i, k in enumerate(kinds)]


def test_sample_meets_the_targets():
    events = _events(["goal"] * 2 + ["shot"] * 12 + ["corner"] * 10 + ["free_kick"] * 6
                     + ["goal_kick"] * 8 + ["throw_in"] * 30 + ["kick_off"] * 3)
    rows = sample_spot_rows(events)
    kinds = Counter(e.kind for e in events if e.row_id in rows)
    assert len(rows) == 20 == len(set(rows))
    assert kinds["goal"] == 2 and kinds["corner"] >= 4 and kinds["kick_off"] == 1
    assert sample_spot_rows(events) == rows


def test_short_file_gives_what_it_has():
    events = _events(["shot", "corner", "goal"])
    assert sorted(sample_spot_rows(events)) == ["0", "1", "2"]


def test_verdicts_and_score(tmp_path):
    d = {"rows": ["1", "2", "3"], "verdicts": {}}
    record_verdict(d, "1", moment="ok", kind="ok", place="unsure", team="ok")
    record_verdict(d, "2", moment="off", kind="ok", place="ok", team="ok")
    assert spot_score(d) == (1, 2, 3)
    with pytest.raises(ValueError):
        record_verdict(d, "9", moment="ok", kind="ok", place="ok", team="ok")
    with pytest.raises(ValueError):
        record_verdict(d, "3", moment="maybe", kind="ok", place="ok", team="ok")
    save_spot("m01", d, tmp_path)
    assert load_spot("m01", tmp_path) == d
    assert load_spot("m02", tmp_path) == {"rows": [], "verdicts": {}}
```

`tests/test_truth_report.py`:

```python
from spv.truth.align import add_attack_mark, add_mark
from spv.truth.report import match_result, p0_report
from spv.truth.spot import record_verdict


def _aligned():
    d = {"marks": [], "kits": {}, "attack_marks": []}
    for half in (1, 2):
        for i, offset in enumerate([2.0, 2.4, 2.8]):
            add_mark(d, half, f"{half}-{i}", "corner", offset)
    for i in range(3):
        add_attack_mark(d, 1, f"a{i}", "A", "right")
        add_attack_mark(d, 2, f"b{i}", "A", "left")
    return d


def _spots(right):
    rows = [str(i) for i in range(20)]
    d = {"rows": rows, "verdicts": {}}
    for i, row in enumerate(rows):
        record_verdict(d, row, moment="ok" if i < right else "off", kind="ok", place="ok", team="ok")
    return d


def test_usable_match():
    result = match_result(_aligned(), _spots(18))
    assert result["usable"], result["reasons"]
    assert result["offsets"] == {1: 2.4, 2: 2.4}


def test_too_few_right():
    result = match_result(_aligned(), _spots(17))
    assert not result["usable"]
    assert result["reasons"] == ["spot checks: 17 of 20 right, need 18"]


def test_drifting_offset():
    d = _aligned()
    add_mark(d, 2, "late", "corner", 4.0)
    assert "half 2: anchors spread 2.0 s" in match_result(d, _spots(20))["reasons"]


def test_unfinished_work_is_not_usable():
    result = match_result({"marks": [], "kits": {}, "attack_marks": []}, {"rows": [], "verdicts": {}})
    assert not result["usable"] and len(result["reasons"]) == 4


def test_report_verdicts():
    good = match_result(_aligned(), _spots(20))
    bad = match_result(_aligned(), _spots(10))
    assert "**Verdict:** GO" in p0_report({"m01": good, "m02": good, "m03": good})
    text = p0_report({"m01": good, "m02": bad})
    assert "**Verdict:** STOP" in text and "| m02 |" in text
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/Scripts/python -m pytest tests/test_truth_align.py tests/test_truth_spot.py tests/test_truth_report.py -v`
Expected: FAIL with `ModuleNotFoundError` for `spv.truth.align`, `spv.truth.spot`, `spv.truth.report`.

- [ ] **Step 3: Write `align.py`**

```python
"""How each event file lines up with its video: anchor offsets per half, kits, attacking direction.

Video time = event file time + offset. Records hold ids and numbers only.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from spv.truth import truth_dir

FLIP = {"left": "right", "right": "left"}


def alignment_path(match_id: str, repo_root: Path | None = None) -> Path:
    return truth_dir(repo_root) / "align" / f"{match_id}.json"


def load_alignment(match_id: str, repo_root: Path | None = None) -> dict:
    path = alignment_path(match_id, repo_root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"marks": [], "kits": {}, "attack_marks": []}


def save_alignment(match_id: str, data: dict, repo_root: Path | None = None) -> Path:
    path = alignment_path(match_id, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    return path


def add_mark(data: dict, half: int, row: str, kind: str, offset_s: float) -> None:
    data["marks"] = [m for m in data["marks"] if m["row"] != row]
    data["marks"].append({"half": half, "row": row, "kind": kind, "offset_s": round(offset_s, 2)})


def _offsets(data: dict, half: int) -> list[float]:
    return [m["offset_s"] for m in data["marks"] if m["half"] == half]


def half_offset(data: dict, half: int) -> float | None:
    values = _offsets(data, half)
    return statistics.median(values) if values else None


def half_spread(data: dict, half: int) -> float | None:
    values = _offsets(data, half)
    return round(max(values) - min(values), 2) if len(values) >= 2 else None


def set_kit(data: dict, team: str, looks: str) -> None:
    data["kits"][team] = looks


def add_attack_mark(data: dict, half: int, row: str, team: str, goal_side: str) -> None:
    """goal_side: the side of the picture holding the goal the row's team is attacking."""
    if goal_side not in FLIP:
        raise ValueError("the goal is on the left or the right of the picture")
    data["attack_marks"] = [m for m in data["attack_marks"] if m["row"] != row]
    data["attack_marks"].append({"half": half, "row": row, "team": team, "goal": goal_side})


def attack_summary(data: dict) -> dict[int, dict]:
    summary = {}
    for half in (1, 2):
        sides = [m["goal"] if m["team"] == "A" else FLIP[m["goal"]]
                 for m in data["attack_marks"] if m["half"] == half]
        if sides:
            top = max(("left", "right"), key=sides.count)
            summary[half] = {"A": top, "agree": sides.count(top), "of": len(sides)}
    return summary


def attack_consistent(summary: dict[int, dict], minimum: int = 3) -> bool:
    if set(summary) != {1, 2}:
        return False
    if any(s["of"] < minimum or s["agree"] != s["of"] for s in summary.values()):
        return False
    return summary[2]["A"] == FLIP[summary[1]["A"]]
```

- [ ] **Step 4: Write `spot.py`**

```python
"""Spot checks: 20 restarts, shots and goals per match, looked at by eye against the video."""

from __future__ import annotations

import json
from pathlib import Path

from spv.truth import truth_dir
from spv.truth.events import TruthEvent

TARGETS = (("goal", 3), ("shot", 5), ("corner", 4), ("free_kick", 3), ("goal_kick", 2), ("throw_in", 2),
           ("kick_off", 1))
VERDICTS = {"moment": ("ok", "off"), "kind": ("ok", "wrong"), "place": ("ok", "wrong", "unsure"),
            "team": ("ok", "wrong", "unsure")}


def _spread(pool: list[TruthEvent], k: int) -> list[TruthEvent]:
    """k events spread evenly through the match."""
    if k <= 0 or not pool:
        return []
    if k >= len(pool):
        return list(pool)
    if k == 1:
        return [pool[len(pool) // 2]]
    return [pool[round(i * (len(pool) - 1) / (k - 1))] for i in range(k)]


def sample_spot_rows(events: list[TruthEvent], n: int = 20) -> list[str]:
    def order(e: TruthEvent):
        return (e.half, e.video_s)

    by_kind = {kind: sorted((e for e in events if e.kind == kind), key=order) for kind, _ in TARGETS}
    chosen: list[TruthEvent] = []
    for kind, k in TARGETS:
        chosen += _spread(by_kind[kind], k)
    if len(chosen) < n:
        taken = {e.row_id for e in chosen}
        rest = sorted((e for kind in ("shot", "corner", "free_kick", "goal_kick", "throw_in")
                       for e in by_kind[kind] if e.row_id not in taken), key=order)
        chosen += _spread(rest, n - len(chosen))
    return [e.row_id for e in sorted(chosen, key=order)][:n]


def spot_path(match_id: str, repo_root: Path | None = None) -> Path:
    return truth_dir(repo_root) / "spot" / f"{match_id}.json"


def load_spot(match_id: str, repo_root: Path | None = None) -> dict:
    path = spot_path(match_id, repo_root)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"rows": [], "verdicts": {}}


def save_spot(match_id: str, data: dict, repo_root: Path | None = None) -> Path:
    path = spot_path(match_id, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    return path


def record_verdict(data: dict, row: str, *, moment: str, kind: str, place: str, team: str) -> None:
    if row not in data["rows"]:
        raise ValueError(f"row {row} is not in this match's spot-check sample")
    verdict = {"moment": moment, "kind": kind, "place": place, "team": team}
    for key, value in verdict.items():
        if value not in VERDICTS[key]:
            raise ValueError(f"{key} is one of {', '.join(VERDICTS[key])}")
    data["verdicts"][row] = verdict


def spot_score(data: dict) -> tuple[int, int, int]:
    """(right, checked, total). Right: the moment and the kind are right, and the place and team are not wrong."""
    verdicts = [data["verdicts"][r] for r in data["rows"] if r in data["verdicts"]]
    right = sum(1 for v in verdicts
                if v["moment"] == "ok" and v["kind"] == "ok" and v["place"] != "wrong" and v["team"] != "wrong")
    return right, len(verdicts), len(data["rows"])
```

- [ ] **Step 5: Write `report.py`**

```python
"""The P0 verdict: are the event files good enough to be the truth?"""

from __future__ import annotations

import math

from spv.truth.align import attack_consistent, attack_summary, half_offset, half_spread
from spv.truth.spot import spot_score

SPREAD_LIMIT_S = 1.0  # anchors in one half must agree within this
SPOT_SHARE = 0.9  # 18 of 20
MIN_MARKS = 3  # anchors per half


def match_result(alignment: dict, spot: dict) -> dict:
    marks = {h: sum(1 for m in alignment["marks"] if m["half"] == h) for h in (1, 2)}
    spreads = {h: half_spread(alignment, h) for h in (1, 2)}
    summary = attack_summary(alignment)
    right, checked, total = spot_score(spot)
    reasons = []
    for h in (1, 2):
        if marks[h] < MIN_MARKS:
            reasons.append(f"half {h}: {marks[h]} anchors, need {MIN_MARKS}")
        elif spreads[h] > SPREAD_LIMIT_S:
            reasons.append(f"half {h}: anchors spread {spreads[h]} s")
    if not attack_consistent(summary):
        reasons.append("attacking direction not settled")
    need = math.ceil(SPOT_SHARE * total)
    if total == 0 or checked < total:
        reasons.append(f"spot checks: {checked} of {total} done")
    elif right < need:
        reasons.append(f"spot checks: {right} of {total} right, need {need}")
    return {"offsets": {h: half_offset(alignment, h) for h in (1, 2)}, "spreads": spreads, "marks": marks,
            "attack": summary, "spot": (right, checked, total), "usable": not reasons, "reasons": reasons}


def _signed(value: float | None) -> str:
    return "-" if value is None else f"{value:+.2f}"


def _plain(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def p0_report(results: dict[str, dict]) -> str:
    lines = ["# P0: can the event files be trusted?", "",
             "| Match | Offset h1 (s) | Spread h1 (s) | Offset h2 (s) | Spread h2 (s) | A attacks (h1/h2) "
             "| Spot checks right | Usable |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for match_id, r in sorted(results.items()):
        attack = "/".join(r["attack"][h]["A"] if h in r["attack"] else "-" for h in (1, 2))
        right, _, total = r["spot"]
        usable = "yes" if r["usable"] else "no: " + "; ".join(r["reasons"])
        lines.append(f"| {match_id} | {_signed(r['offsets'][1])} | {_plain(r['spreads'][1])} "
                     f"| {_signed(r['offsets'][2])} | {_plain(r['spreads'][2])} | {attack} | {right}/{total} | {usable} |")
    go = bool(results) and all(r["usable"] for r in results.values())
    verdict = "GO" if go else "STOP: talk it through with Thomas before P2"
    lines += ["", f"**Verdict:** {verdict}", "",
              f"Gate: anchors within {SPREAD_LIMIT_S:g} s per half (at least {MIN_MARKS}), attacking direction "
              f"consistent, at least {SPOT_SHARE:.0%} of spot checks right.",
              "Anchors and spot checks were judged by eye by Claude from contact sheets; the frames stay in runs/ "
              "and are never committed."]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 6: Run the tests to see them pass**

Run: `.venv/Scripts/python -m pytest tests/test_truth_align.py tests/test_truth_spot.py tests/test_truth_report.py -v`
Expected: 12 passed.

- [ ] **Step 7: Commit**

```bash
git add src/spv/truth/align.py src/spv/truth/spot.py src/spv/truth/report.py tests/test_truth_align.py tests/test_truth_spot.py tests/test_truth_report.py
git commit -m "feat(truth): alignment records, spot checks and the P0 report"
```

---

### Task 5: The `spv truth` command

**Files:**
- Create: `src/spv/truth/cli.py`
- Modify: `src/spv/cli.py` (`build_parser`)
- Test: `tests/test_truth_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 1-4.
- Produces: `register_truth(sub: argparse._SubParsersAction) -> None` and these commands (every one prints a one-line error and returns 1 on bad input):

| Command | Does |
| --- | --- |
| `spv truth add mNN VIDEO EVENTS` | register a match |
| `spv truth inventory` | write and print `tests/truth/inventory.md` |
| `spv truth split [--force]` | choose and save the held-out split |
| `spv truth events mNN [--kind K]` | list kept rows: id, half, time, kind, team, zone |
| `spv truth sheet mNN --row R [--around=-3:3:0.5] [--base S] [--columns 4]` | contact sheet around a row; base defaults to the half's saved offset, else 0 |
| `spv truth mark mNN --row R --offset S` | record the offset at which row R happens in the video |
| `spv truth kit mNN --team A --looks "..."` | record what a team wears |
| `spv truth attack mNN --row R --goal left/right` | record which side of the picture the row's team attacks |
| `spv truth spots mNN` | choose the 20 spot-check rows (once) and make a sheet for each |
| `spv truth spot mNN --row R --moment ok/off --kind ok/wrong --place ok/wrong/unsure --team ok/wrong/unsure` | record a verdict |
| `spv truth report` | write and print `tests/truth/p0_report.md`; exit 0 on GO, 1 on STOP |

`--around` values start with `-`, so they are always written `--around=-60:60:4`.

- [ ] **Step 1: Write the failing test**

`tests/test_truth_cli.py`:

```python
import json

import pytest

from spv import config
from spv.cli import main
from truth_samples import EYEBALL_TIMED


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    return tmp_path


def test_truth_flow(repo, tiny_video, capsys):
    events = repo / "e.csv"
    events.write_text(EYEBALL_TIMED, encoding="utf-8-sig")
    assert main(["truth", "add", "m01", str(tiny_video), str(events)]) == 0
    assert main(["truth", "add", "bohs", str(tiny_video), str(events)]) == 1
    assert main(["truth", "inventory"]) == 0
    assert "| m01 | eyeball |" in (repo / "tests/truth/inventory.md").read_text(encoding="utf-8")
    assert main(["truth", "split"]) == 0
    assert json.loads((repo / "tests/truth/split.json").read_text())["p0"] == ["m01"]
    assert main(["truth", "split"]) == 1  # fixed once made

    capsys.readouterr()
    assert main(["truth", "events", "m01", "--kind", "corner"]) == 0
    listed = capsys.readouterr().out.strip().splitlines()
    assert len(listed) == 1 and listed[0].startswith("3\t")

    assert main(["truth", "sheet", "m01", "--row", "1", "--base", "-29", "--around=-0.5:0.5:0.5"]) == 0
    assert len(list((repo / "runs/truth/m01").glob("*.png"))) == 1
    assert main(["truth", "mark", "m01", "--row", "1", "--offset", "-29"]) == 0
    assert main(["truth", "mark", "m01", "--row", "99", "--offset", "0"]) == 1
    assert main(["truth", "kit", "m01", "--team", "A", "--looks", "white shirts"]) == 0
    assert main(["truth", "attack", "m01", "--row", "4", "--goal", "right"]) == 0
    align = json.loads((repo / "tests/truth/align/m01.json").read_text())
    assert align["marks"][0]["offset_s"] == -29.0 and align["kits"] == {"A": "white shirts"}

    assert main(["truth", "spots", "m01"]) == 1  # half 2 has no offset yet
    assert main(["truth", "mark", "m01", "--row", "9", "--offset", "-2999"]) == 0
    assert main(["truth", "spots", "m01"]) == 0
    spot = json.loads((repo / "tests/truth/spot/m01.json").read_text())
    assert spot["rows"] and (repo / f"runs/truth/m01/spot_row{spot['rows'][0]}.png").exists()
    row = spot["rows"][0]
    assert main(["truth", "spot", "m01", "--row", row, "--moment", "ok", "--kind", "ok",
                 "--place", "unsure", "--team", "ok"]) == 0

    assert main(["truth", "report"]) == 1  # far from done: STOP
    assert "**Verdict:** STOP" in (repo / "tests/truth/p0_report.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the test to see it fail**

Run: `.venv/Scripts/python -m pytest tests/test_truth_cli.py -v`
Expected: FAIL (`argument command: invalid choice: 'truth'`, exit code 2 raised as `SystemExit`).

- [ ] **Step 3: Write `src/spv/truth/cli.py`**

```python
"""`spv truth`: phase P0, checking event files against their videos."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from spv import config


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
    from spv.truth.spot import load_spot, sample_spot_rows, save_spot

    match, events = _match(a.match)
    alignment = load_alignment(a.match)
    base = {h: half_offset(alignment, h) for h in (1, 2)}
    missing = [h for h in (1, 2) if base[h] is None]
    if missing:
        raise ValueError(f"align half {missing[0]} first (spv truth mark)")
    data = load_spot(a.match)
    if not data["rows"]:
        data["rows"] = sample_spot_rows(list(events.values()))
        save_spot(a.match, data)
    kits = alignment.get("kits", {})
    for row in data["rows"]:
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
    from spv.truth import truth_dir
    from spv.truth.align import load_alignment
    from spv.truth.report import match_result, p0_report
    from spv.truth.split import load_split

    split = load_split()
    if not split:
        raise ValueError("no split yet: run spv truth split first")
    results = {m: match_result(load_alignment(m), _load_spot(m)) for m in split["p0"]}
    text = p0_report(results)
    (truth_dir() / "p0_report.md").write_text(text, encoding="utf-8")
    print(text)
    return 0 if results and all(r["usable"] for r in results.values()) else 1


def _load_spot(match_id: str) -> dict:
    from spv.truth.spot import load_spot

    return load_spot(match_id)


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
    command("spots", "choose the 20 spot-check rows and make their sheets", _spots)
    p = command("spot", "record a spot-check verdict", _spot)
    p.add_argument("--row", required=True)
    p.add_argument("--moment", choices=["ok", "off"], required=True)
    p.add_argument("--kind", choices=["ok", "wrong"], required=True)
    p.add_argument("--place", choices=["ok", "wrong", "unsure"], required=True)
    p.add_argument("--team", choices=["ok", "wrong", "unsure"], required=True)
    command("report", "write tests/truth/p0_report.md with the go / stop verdict", _report, match=False)
```

- [ ] **Step 4: Register it in `src/spv/cli.py`**

In `build_parser()`, after the `data_sub` / `fetch.set_defaults(func=_data_fetch)` lines and before `return parser`, add:

```python
    from spv.truth.cli import register_truth

    register_truth(sub)
```

- [ ] **Step 5: Run the test to see it pass, then the whole suite**

Run: `.venv/Scripts/python -m pytest tests/test_truth_cli.py -v`
Expected: 1 passed.

Run: `.venv/Scripts/python -m pytest -q`
Expected: everything passes, including `tests/test_privacy.py` and `tests/test_cli.py`.

- [ ] **Step 6: Commit**

```bash
git add src/spv/truth/cli.py src/spv/cli.py tests/test_truth_cli.py
git commit -m "feat(truth): spv truth commands for P0"
```

---

### Task 6: README section

**Files:**
- Modify: `README.md` (on this branch, from `main`'s version)

- [ ] **Step 1: Add a "Checking event files (P0)" section** after the existing usage section:

```markdown
## Checking event files (P0)

Before anything is trained, `spv truth` checks that Thomas's event files (Eyeball files or StatPadder
exports with `video_ms`) line up with their videos. Matches are registered under anonymous ids; their
paths stay in `local.config.json`. Contact sheets go to `runs/truth/` and are never committed. The
records in `tests/truth/` hold ids and numbers only.

    spv truth add m01 <video> <events file>
    spv truth inventory
    spv truth split
    spv truth events m01 --kind corner
    spv truth sheet m01 --row 312 --around=-60:60:4 --base 0
    spv truth mark m01 --row 312 --offset 14.5
    spv truth spots m01
    spv truth spot m01 --row 312 --moment ok --kind ok --place ok --team ok
    spv truth report

See `docs/superpowers/plans/2026-11-13-p0-event-file-trust.md` for the full procedure.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README section for spv truth"
```

---

### Task 7: Run P0 on the real matches (on the RTX 2060 computer)

This task makes judgements by eye. The executing agent opens each contact sheet with the Read tool, which shows the image, and records what it sees. Thomas is only asked to confirm which video goes with which event file.

**Files:**
- Create (committed): `tests/truth/inventory.md`, `tests/truth/split.json`, `tests/truth/align/mNN.json` and `tests/truth/spot/mNN.json` for the 3 P0 matches, `tests/truth/p0_report.md`
- Never committed: anything in `runs/`, `local.config.json`

- [ ] **Step 1: Pair videos with event files**

List the candidates (videos and event files live under `D:/spv-data` and `OneDrive/Bohs/...` on this machine):

```bash
find /d/spv-data "<personal OneDrive>/Bohs" -maxdepth 3 \( -iname "*.mp4" -o -iname "*.csv" \) 2>/dev/null
```

Pair each video with its event file by date and opponent in the names. Show Thomas the pairing as a numbered list (`m01: <video name> + <event file name>`) and get a yes before registering. Don't put the names anywhere in the repo.

- [ ] **Step 2: Register, inventory and split**

```bash
spv truth add m01 "<video>" "<events>"     # once per pair
spv truth inventory
spv truth split
```

Expected: `inventory.md` lists every match. The split names 5 held-out matches, the first 3 being the P0 matches. Check that the hand-coded matches show `Timed` at or near 100%; if not, they can't be used and the report says so (spec 6.1 asks whether hand-coded matches carry `video_ms`).

- [ ] **Step 3: For each P0 match, find the half 1 offset from the kick-off**

```bash
spv truth events m01 --kind kick_off       # first row is half 1's kick-off
spv truth sheet m01 --row <R> --around=-60:60:4 --base 0
```

Open the sheet. Look for the frame where the ball is on the centre spot and play starts, with both teams in their own halves. If it isn't there, widen to `--around=-600:600:20` (the video may have warm-up footage first) and then look again near the frame that's closest. Once the coarse offset `C` is found, refine it:

```bash
spv truth sheet m01 --row <R> --around=-3:3:0.5 --base <C>
spv truth mark m01 --row <R> --offset <offset printed on the frame where the ball is first played>
```

- [ ] **Step 4: Same for half 2's kick-off**

The second half may have its own offset (a separate file, or a cut at half time). Start from half 1's offset plus or minus 20 minutes if `--base 0` shows nothing.

- [ ] **Step 5: At least 3 more anchors per half**

Use corners spread across each half (fall back to goal kicks):

```bash
spv truth events m01 --kind corner
spv truth sheet m01 --row <R> --around=-3:3:0.5      # base is now the half's saved offset
spv truth mark m01 --row <R> --offset <offset of the frame where the corner is struck>
```

Each `mark` prints the half's offset and spread. If the spread goes past 1 s, add 2 more anchors in that half to see whether it's a misjudged frame or real drift: offsets that grow steadily with time mean drift. Write down which in Step 9.

- [ ] **Step 6: Kits**

From a team A corner sheet, note what the kicker's team wears, then do the same for B:

```bash
spv truth kit m01 --team A --looks "white shirts, black shorts"
spv truth kit m01 --team B --looks "red shirts, red shorts"
```

- [ ] **Step 7: Attacking direction**

For at least 3 shots per half (`spv truth events m01 --kind shot`):

```bash
spv truth sheet m01 --row <R> --around=-1:1:1 --columns 3
spv truth attack m01 --row <R> --goal <left|right>   # the side of the picture holding the goal being shot at
```

Expected: every mark in a half agrees, and team A switches ends at half time.

- [ ] **Step 8: Spot checks**

```bash
spv truth spots m01
```

For each sheet it lists, decide:
- **moment:** `ok` if the event visibly happens within the 5 frames (2 s either side); else `off`
- **kind:** `ok` if it's that kind of event (a corner taken from the corner arc, a shot at goal, and so on); else `wrong`
- **place:** compare the file's zone (as the team attacks, using Step 7's direction) with where it happens in the picture: `ok`, `wrong`, or `unsure` when the picture doesn't show enough
- **team:** compare the kit from Step 6 with the player on the ball: `ok`, `wrong`, or `unsure`

```bash
spv truth spot m01 --row <R> --moment ok --kind ok --place ok --team ok
```

Repeat Steps 3-8 for the other two P0 matches.

- [ ] **Step 9: Report**

```bash
spv truth report
.venv/Scripts/python -m pytest -q tests/test_privacy.py
git status --short       # only tests/truth/ files; nothing from runs/, no local.config.json
```

Add a short "Notes" section by hand at the end of `tests/truth/p0_report.md`, including:
- any drift found, and what it looked like
- anything odd about a file (missing rows, a second-half offset far from the first)
- how sure the by-eye judgements felt
- how many hand-coded matches carry `video_ms`

- [ ] **Step 10: Commit, PR, and the decision with Thomas**

```bash
git add tests/truth/
git commit -m "test(truth): P0 records and report for the three P0 matches"
git push -u origin feature/03-event-truth
```

Open the PR to `main` (GitHub REST API with the token from `git credential fill`, as in the StatPadder routine). Wait for CI to pass. Then put the report in front of Thomas:
- **GO:** next is P1, the scorer, then P2.
- **STOP:** go through the reasons with him before anything else. Possible ways forward:
  - per-half drift correction
  - different matches
  - the hand-coded matches only
  - rethinking how far the plan relies on the files

Merge only after he has seen the result.

---

## Self-review notes

- Spec P0 items and where they're covered:
  - inventory: Task 2 and Task 7 Step 2
  - offset per file from kick-offs and goals seen in the picture: Task 7 Steps 3-5 (kick-offs and corners are used, since they're clearer on a wide view than goals)
  - offset constant across each half: the spread check in report.py
  - 20 restarts and shots spot-checked per match: spot.py and Task 7 Step 8
  - attacking direction per half: align.py and Task 7 Step 7
  - whether hand-coded matches carry `video_ms`: the inventory's Timed column and the report notes
  - gate: report.py constants
- The scorer (P1), the view-position test (P1b) and everything after them are separate plans.
- Kick-offs after a goal count as kick-offs, so a sample with a goal has more kick-offs than halves: the tests allow for this (`kick_off == 3` in the sample).
