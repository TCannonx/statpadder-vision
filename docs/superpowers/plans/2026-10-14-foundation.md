# Foundation (build step 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The skeleton every later stage plugs into: the `spv` package and CLI, the job file and
lineup, the stage cache and resumable pipeline, the `.sptrack` format with its reader, the
simulator (public tracking data seen through a simulated ball-following camera), the regression
check, and `<club folder>\clip1.mp4` registered as the first reference clip.

**Architecture:** A Python package `spv` (src layout). `spv process --job job.json` runs a list of
stages through a cache that fingerprints each stage's inputs; this step ships only two real
stages (`probe`, `export`), so the exported file holds every slot as unknown. The simulator turns
Metrica Sports' open tracking data into truth + simulated detections, and `spv check` scores
outputs against truth and saved baselines. Later build steps add stages and measures without
changing these interfaces.

**Tech Stack:** Python 3.10, numpy, scipy (assignment), shapely 2 (view polygons), pytest,
ffprobe (ffmpeg) for video metadata, Docker, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-14-vision-module-design.md`

## Global Constraints

- Footage shows minors: no video, frame, image or local path is ever committed. Clip paths live
  only in the git-ignored `local.config.json`. Committed clip metadata holds names, sizes and
  hashes, never paths.
- Output rate: "10 positions a second. The rate is a field in the file, so 25 needs no format change."
- Coordinates: "metres from the corner flag on the camera's near-left, x along the near
  touchline, y towards the far touchline."
- Positions: "x and y in centimetres (16-bit), uncertainty (8-bit, 0.25 m steps) and a state
  (seen, predicted, not on the pitch, unknown)". The ball adds on the ground / in the air.
- Fixed slots: 11 + 11 players and a ball that always exist.
- Everything runs locally; no cloud AI service is called.
- CI has no graphics card and no video: unit tests + simulator suite only.
- Every change runs `spv check` before it is called done; the results table goes in the change
  description; a better result updates the baseline in the same change.
- Work on branch `feature/01-foundation`, one commit per task, merged by PR (once the GitHub repo
  exists). Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Lineup with fewer than 11 a side** (academy 9 v 9) or a red card: the unused slots are
   "not on the pitch" for those moments, never "unknown". Test in Task 2 and Task 5.
2. **Video paths with spaces and dots** (`Home Vs. Away 20s - Tactical.mp4`): probe and
   cache work unchanged. Test in Task 5.
3. **A run stopped mid-stage**: the half-written stage is redone on the next run, never treated as
   done. Test in Task 4.
4. **Job edited after a run** (new lineup or pitch size): stages that read the changed field
   re-run; stages that don't stay cached. Test in Task 4.
5. **A position outside the 16-bit range or a NaN in a "seen" slot**: writing fails loudly instead
   of wrapping or writing garbage. Test in Task 3.

---

## File Structure

```
pyproject.toml                  package, deps, `spv` entry point
Dockerfile, .dockerignore       image with ffmpeg + spv
.github/workflows/ci.yml        tests, sim suite, docker build
README.md                       what it is, how to run, where data lives
src/spv/__init__.py             __version__
src/spv/cli.py                  argparse: process, check, clip add, data fetch
src/spv/lineup.py               lineup file, slot occupancy over time
src/spv/job.py                  job file
src/spv/sptrack.py              tracking file format: write/read, encode helpers
src/spv/cache.py                RunCache
src/spv/pipeline.py             Stage protocol, run_pipeline, RunReport
src/spv/stages/probe.py         ffprobe metadata
src/spv/stages/export.py        builds the .sptrack
src/spv/config.py               local.config.json, data dir
src/spv/sim/tracks.py           PitchTracks + Metrica loader/downloader
src/spv/sim/camera.py           simulated ball-following camera
src/spv/sim/detections.py       simulated detections
src/spv/sim/scenes.py           scene finder, null solver
src/spv/check/score.py          scoring an output against truth
src/spv/check/measures.py       Measure, compare, baselines
src/spv/check/suites.py         sim + clips suites
tests/...                       mirrors src; fixtures in tests/fixtures
tests/baselines/sim.json, clips.json
tests/clips/clip1.json, clip1.lineup.json   committed clip metadata (no path)
tests/results/sim.md, clips.md              latest results tables
```

---

### Task 1: Package skeleton and CLI

**Files:**
- Create: `pyproject.toml`, `src/spv/__init__.py`, `src/spv/cli.py`, `tests/test_cli.py`,
  `.github/workflows/ci.yml`

**Interfaces:**
- Produces: `spv.__version__ = "0.1.0"`; `spv.cli.main(argv: list[str] | None = None) -> int`
  with subparsers `process`, `check`, `clip`, `data` (later tasks fill them in; unfilled ones
  print "not implemented yet" and return 2). Console script `spv = "spv.cli:main"`.

- [ ] **Step 1: Branch.** `git switch -c feature/01-foundation`
- [ ] **Step 2: Write the failing test** `tests/test_cli.py`:

```python
def test_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "spv 0.1.0"
```

- [ ] **Step 3: Run** `python -m pytest tests/test_cli.py -v` → FAIL (no module `spv`).
- [ ] **Step 4: Implement.** `pyproject.toml` (setuptools, `requires-python = ">=3.10"`, deps
  `numpy>=1.26`, `scipy>=1.11`, `shapely>=2.0`; extra `dev = ["pytest>=8"]`), the package and
  `main`. Create a venv: `python -m venv .venv` then `.venv/Scripts/python -m pip install -e .[dev]`.
  All later commands use `.venv/Scripts/python`.
- [ ] **Step 5: CI.** `ci.yml`: on push and pull_request, ubuntu-latest, Python 3.10,
  `pip install -e .[dev]`, `pytest -q`.
- [ ] **Step 6: Run** the test → PASS.
- [ ] **Step 7: Commit** `feat: package skeleton and spv CLI`.

### Task 2: Lineup and job files

**Files:**
- Create: `src/spv/lineup.py`, `src/spv/job.py`, `tests/test_lineup.py`, `tests/test_job.py`,
  `tests/fixtures/lineup_11.json`, `tests/fixtures/lineup_9_red.json`, `tests/fixtures/job.json`

**Interfaces:**
- Produces:
  - `SLOTS_PER_TEAM = 11`; `slot_ids() -> list[str]` → `["home_01", …, "home_11", "away_01", …, "away_11"]`.
  - `Lineup` (frozen dataclass): `home: Team`, `away: Team`, `events: tuple[Event, ...]`;
    `Team(name: str, players: tuple[Player, ...])`; `Player(id: str, number: int | None, starter: bool)`;
    `Event(type: Literal["sub", "red"], team: Literal["home", "away"], time_s: float, off: str | None, on: str | None, player: str | None)`.
  - `load_lineup(path: Path) -> Lineup`, raising `LineupError` naming the bad field.
  - `Lineup.on_pitch(team: str, time_s: float) -> int` — starters, minus red cards at or before `time_s`; subs don't change the count.
  - `slot_occupancy(lineup: Lineup, times_s: np.ndarray) -> np.ndarray` — bool `(T, 22)`, in `slot_ids()` order; for each team the first `on_pitch` slots are True. (Which player owns a slot is decided by stage 4 and naming, not here.)
  - `Job` (frozen dataclass): `video: Path`, `lineup: Path`, `output: Path`, `cache_dir: Path`,
    `pitch: tuple[float, float] | None` (length, width m), `rate: float`, `options: dict`.
  - `load_job(path: Path) -> Job`, raising `JobError`. Relative paths resolve against the job
    file's folder. Defaults: `rate` 10, `cache_dir` = `output.parent / (output.stem + ".spv-cache")`.

Lineup file (StatPadder's export will produce this in build step 7). **Event times are seconds of
the video**, not match clock:

```json
{"home": {"name": "Home", "players": [{"id": "h1", "number": 1, "starter": true}]},
 "away": {"name": "Away", "players": []},
 "events": [{"type": "sub", "team": "home", "time_s": 2700, "off": "h4", "on": "h15"},
            {"type": "red", "team": "away", "time_s": 3100, "player": "a6"}]}
```

Job file:

```json
{"video": "clip1.mp4", "lineup": "lineup.json", "output": "out/clip1.sptrack",
 "pitch": {"length_m": 100, "width_m": 64}, "rate": 10, "options": {}}
```

- [ ] **Step 1: Write failing tests:**
  - `test_on_pitch_counts_starters_and_reds`: `lineup_9_red.json` (9 starters a side, away red at 100 s) → `on_pitch("home", 0) == 9`, `on_pitch("away", 99.9) == 9`, `on_pitch("away", 100) == 8`.
  - `test_sub_keeps_count`: `lineup_11.json` has a home sub at 50 s → `on_pitch("home", 60) == 11`.
  - `test_slot_occupancy_shape_and_unused_slots`: 9 v 9 with red, `times = np.arange(0, 200, 0.1)` → shape `(2000, 22)`; `occ[0, 9:11].any() == False`; `occ[999, 11:20].all()` (t = 99.9 s); `occ[1000, 11:22].sum() == 8`.
  - `test_more_than_11_starters_rejected` → `LineupError` mentioning `"starters"`.
  - `test_event_unknown_player_rejected` → `LineupError` mentioning the player id.
  - `test_job_resolves_relative_paths(tmp_path)`: `job.video == tmp_path / "clip1.mp4"`; `cache_dir == tmp_path / "out" / "clip1.spv-cache"`; `pitch == (100.0, 64.0)`; `rate == 10.0`.
  - `test_job_missing_video_field` → `JobError` with `"video"` in the message.
  - `test_job_pitch_optional`: no `pitch` key → `job.pitch is None`.
- [ ] **Step 2: Run** `pytest tests/test_lineup.py tests/test_job.py -v` → FAIL.
- [ ] **Step 3: Implement** both modules. `load_job` doesn't check that the video exists (the
  probe stage does, with a clear message).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: lineup and job files`.

### Task 3: Tracking file format

**Files:**
- Create: `src/spv/sptrack.py`, `tests/test_sptrack.py`

**Interfaces:**
- Consumes: `slot_ids()` (Task 2).
- Produces:
  - `FORMAT_VERSION = "1.0"`; `POS_DTYPE = np.dtype([("x", "<i2"), ("y", "<i2"), ("unc", "u1"), ("state", "u1")])` (6 bytes).
  - `class State(IntEnum): SEEN = 0; PREDICTED = 1; NOT_ON_PITCH = 2; UNKNOWN = 3`.
  - `Manifest` dataclass: `format_version: str`, `module_version: str`, `rate: float`,
    `pitch_length_m: float`, `pitch_width_m: float`, `pitch_source: Literal["job", "default", "solved"]`,
    `coordinate_system: str`, `teams: dict[str, str]`, `slots: list[str]`,
    `substitutions: list[dict]`, `quality: dict[str, float]` (keys `camera_share`, `seen_share`,
    `mean_uncertainty_m`), `n_moments: int`.
  - `TrackFile` dataclass: `manifest: Manifest`, `positions: np.ndarray` (`(T, 22)` POS_DTYPE),
    `ball: np.ndarray` (`(T,)` POS_DTYPE), `ball_in_air: np.ndarray` (`(T,)` bool),
    `view: list[np.ndarray]` (T arrays `(k, 2)` float metres; `(0, 2)` when no camera),
    `pieces: list[dict]`, `corrections: list[dict]`.
  - `encode(xy_m: np.ndarray, unc_m: np.ndarray, state: np.ndarray) -> np.ndarray` (POS_DTYPE);
    `decode(pos: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]` → xy metres (NaN where
    state is NOT_ON_PITCH or UNKNOWN), unc metres, state.
  - `write_sptrack(path: Path, track: TrackFile) -> None`; `read_sptrack(path: Path) -> TrackFile`.
  - `SptrackError`, `SptrackVersionError(SptrackError)`.

Zip members (deflate): `manifest.json`, `positions.npy`, `ball.npy`, `ball_in_air.npy`,
`view.npz` (`offsets` int64 `(T+1,)`, `points` int16 cm `(K, 2)`), `pieces.json`,
`corrections.jsonl`. `.npy` written with `allow_pickle=False`.

Encoding rules: x, y rounded to the nearest cm; outside −32768…32767 cm → `SptrackError`.
Uncertainty rounded to 0.25 m steps and saturated at 255 (63.75 m). For SEEN or PREDICTED a NaN
x/y → `SptrackError`; for NOT_ON_PITCH/UNKNOWN x, y, unc are stored as 0.

- [ ] **Step 1: Write failing tests:**
  - `test_dtype_is_six_bytes`: `POS_DTYPE.itemsize == 6`.
  - `test_roundtrip(tmp_path)`: random track (T=50, seed 0), positions in 0–105 × 0–68, mixed states, 3 view polygons, one piece, one correction → read back: `manifest == original manifest`, max abs xy error ≤ 0.005 m for SEEN/PREDICTED, states equal, decoded NaN exactly where NOT_ON_PITCH/UNKNOWN, `ball_in_air` equal, view points within 0.005 m, pieces/corrections equal.
  - `test_uncertainty_steps`: `encode` of unc `[0.1, 0.13, 70.0]` decodes to `[0.0, 0.25, 63.75]`.
  - `test_out_of_range_raises`: x = 400 m → `SptrackError`.
  - `test_nan_seen_raises`: NaN xy with state SEEN → `SptrackError`.
  - `test_newer_major_version_rejected(tmp_path)`: manifest `format_version` "2.0" → `read_sptrack` raises `SptrackVersionError`; "1.3" reads fine.
  - `test_size_full_match`: T = 54,000, 22 slots, all UNKNOWN → written file < 7.5 MB.
- [ ] **Step 2: Run** `pytest tests/test_sptrack.py -v` → FAIL.
- [ ] **Step 3: Implement** `sptrack.py`. `coordinate_system` constant: `"metres from the near-left corner flag; x along the near touchline; y towards the far touchline"`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: .sptrack tracking file format`.

### Task 4: Stage cache and pipeline

**Files:**
- Create: `src/spv/cache.py`, `src/spv/pipeline.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `Job` (Task 2).
- Produces:
  - `RunCache(root: Path)`: `lookup(stage: str, fingerprint: str) -> Path | None` (the stage's
    folder if its `done.json` holds this fingerprint); `begin(stage: str) -> Path` (empties and
    returns `root/<stage>.tmp`); `commit(stage: str, fingerprint: str) -> Path` (replaces
    `root/<stage>` with the tmp folder by rename, then writes `done.json`).
  - `class Stage(Protocol)`: `name: str`, `version: str`, `depends_on: tuple[str, ...]`,
    `inputs(self, job: Job) -> dict` (JSON-able: the job fields this stage reads),
    `run(self, job: Job, upstream: dict[str, Path], out_dir: Path) -> None`.
  - `file_identity(path: Path) -> dict` → `{"path": str(resolved), "size": int, "mtime_ns": int}` (videos are never hashed whole).
  - `fingerprint(stage: Stage, job: Job, upstream_fps: dict[str, str]) -> str` — sha256 of
    canonical JSON of `{name, version, inputs, upstream_fps}`.
  - `run_pipeline(job: Job, stages: list[Stage], cache: RunCache) -> RunReport`; stages run in the
    given order and must list dependencies earlier in the list (else `ValueError`).
  - `RunReport` dataclass: `stages: list[StageResult]`, `total_s: float`, `to_json() -> dict`;
    `StageResult(name: str, status: Literal["ran", "cached"], seconds: float)`.

- [ ] **Step 1: Write failing tests** with two fake stages `A` and `B(depends_on=("A",))` that count runs and write a file:
  - `test_second_run_is_cached`: run twice → second report statuses `["cached", "cached"]`, run counts 1 and 1.
  - `test_changed_input_reruns_dependents`: `A.inputs` reads `job.pitch`; change pitch → A and B re-run. Change only a field B reads → A cached, B ran.
  - `test_version_bump_reruns`: bump `B.version` → A cached, B ran.
  - `test_crash_mid_stage_is_redone`: B raises after writing a partial file → `run_pipeline` re-raises; next run with B fixed → B ran, its folder has no partial-file leftovers, A cached.
  - `test_dependency_order_checked`: B before A → `ValueError`.
  - `test_file_identity_changes_with_content(tmp_path)`: rewrite the file with other bytes → identity differs.
- [ ] **Step 2: Run** `pytest tests/test_pipeline.py -v` → FAIL.
- [ ] **Step 3: Implement** `cache.py` and `pipeline.py`. Log one line per stage to stderr (`probe: cached`, `export: ran in 0.4 s`).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: stage cache and resumable pipeline`.

### Task 5: Probe and export stages, `spv process`

**Files:**
- Create: `src/spv/stages/__init__.py`, `src/spv/stages/probe.py`, `src/spv/stages/export.py`,
  `tests/test_process.py`, `tests/conftest.py`
- Modify: `src/spv/cli.py` (`process`)

**Interfaces:**
- Consumes: `Job`, `load_lineup`, `slot_occupancy`, `slot_ids` (Task 2); `TrackFile`, `Manifest`,
  `encode`, `write_sptrack`, `State` (Task 3); `Stage`, `run_pipeline`, `RunCache`,
  `file_identity` (Task 4).
- Produces:
  - `ProbeStage` (name `"probe"`): writes `probe.json` `{"duration_s", "fps", "width", "height"}`
    via `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate:format=duration -of json`.
    Missing ffprobe → `RuntimeError("ffprobe not found: install ffmpeg")`; missing video →
    `FileNotFoundError` naming the path.
  - `ExportStage` (name `"export"`, depends on `probe`): writes `match.sptrack`. Moments
    `t_i = i / rate` for `t_i < duration_s` (45.0 s at 10 → 450 moments). Occupied slots
    UNKNOWN, unoccupied NOT_ON_PITCH, ball UNKNOWN, `ball_in_air` False, empty views. Pitch from
    the job (`pitch_source "job"`) or 105 × 68 (`"default"`). Quality all 0.0. Substitutions =
    the lineup's sub events as dicts.
  - `default_stages() -> list[Stage]` → `[ProbeStage(), ExportStage()]` (later steps insert stages here).
  - `spv process --job PATH`: runs `default_stages()`, copies `match.sptrack` to `job.output`,
    writes `<output stem>.run_report.json` beside it, returns 0; errors print one line and return 1.
  - `tests/conftest.py` fixture `tiny_video(tmp_path_factory) -> Path`: 3.0 s, 25 fps, 320×180
    from `ffmpeg -f lavfi -i testsrc=duration=3:size=320x180:rate=25`, saved under a folder
    named `with spaces. dots` as `Home Vs. test - Tactical.mp4`; tests using it skip when
    ffmpeg isn't on PATH.

- [ ] **Step 1: Write failing tests:**
  - `test_process_writes_unknown_track(tiny_video, tmp_path)`: job with `lineup_11.json`, no pitch → exit 0; read output: `n_moments == 30`, all 22 slot states UNKNOWN, ball UNKNOWN, `pitch_source == "default"`, `(pitch_length_m, pitch_width_m) == (105.0, 68.0)`; run report exists with stages `probe`, `export`.
  - `test_nine_a_side_red_card(tiny_video, tmp_path)`: lineup 9 v 9 with an away red at 1.0 s → at moment 0 slots `home_10`, `home_11`, `away_10`, `away_11` NOT_ON_PITCH; at moment 10 `away_09` is NOT_ON_PITCH too, `away_08` UNKNOWN.
  - `test_rerun_is_cached(tiny_video, tmp_path)`: second `process` → report statuses all `"cached"`.
  - `test_pitch_change_reruns_export_only`: add pitch to job → `probe` cached, `export` ran, manifest `pitch_source == "job"`.
  - `test_missing_video_message(tmp_path, capsys)`: exit 1 and stderr contains the video path.
- [ ] **Step 2: Run** `pytest tests/test_process.py -v` → FAIL.
- [ ] **Step 3: Implement** the two stages and the `process` subcommand. `ProbeStage.inputs` = `{"video": file_identity(job.video)}`; `ExportStage.inputs` = `{"lineup": file_identity(job.lineup), "pitch": job.pitch, "rate": job.rate}`.
- [ ] **Step 4: Run** → PASS. Then manually: a job for `<club folder>\clip1.mp4` (personal OneDrive) in the scratchpad with `tests/clips/clip1.lineup.json` (created in Task 10; for now a copy of `lineup_11.json`), `spv process` → reports 450-ish moments. Don't commit the job.
- [ ] **Step 5: Commit** `feat: probe and export stages, spv process`.

### Task 6: Public tracking data (simulator truth)

**Files:**
- Create: `src/spv/config.py`, `src/spv/sim/__init__.py`, `src/spv/sim/tracks.py`,
  `tests/sim/test_tracks.py`, `tests/fixtures/metrica_home.csv`, `tests/fixtures/metrica_away.csv`
- Modify: `src/spv/cli.py` (`data fetch metrica`)

**Interfaces:**
- Produces:
  - `config.load_local_config(repo_root: Path | None = None) -> dict` (reads `local.config.json`
    if present, else `{}`); `config.data_dir() -> Path` = env `SPV_DATA_DIR`, else config
    `data_dir`, else `<repo>/data` (git-ignored).
  - `PitchTracks` dataclass: `rate: float`, `pitch: tuple[float, float]`, `times_s: np.ndarray (T,)`,
    `ids: list[str]` (e.g. `"home_p11"`, `"away_p25"` from jersey numbers), `teams: list[str]`
    (`"home"`/`"away"` per id), `xy: np.ndarray (T, N, 2)` metres, NaN when not on the pitch,
    `ball_xy: np.ndarray (T, 2)`, NaN when unknown.
  - `load_metrica(home_csv: Path, away_csv: Path, rate: float = 10.0) -> PitchTracks` — Metrica
    "RawTrackingData" CSVs (3 header rows: team, jersey numbers, column names; then
    `Period, Frame, Time [s]`, x/y pairs per player, `Ball` x/y; coordinates 0–1 from the top-left,
    25 Hz). Pitch 105 × 68. Converts to spv axes: `x = u * 105`, `y = (1 - v) * 68` (the near
    touchline is Metrica's bottom edge). Resamples to `rate` by linear interpolation on
    `Time [s]`; a NaN neighbour gives NaN (no interpolation across absences).
  - `ensure_metrica(game: int, data_dir: Path) -> tuple[Path, Path]` downloads
    `https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_{game}/Sample_Game_{game}_RawTrackingData_{Home,Away}_Team.csv`
    into `data_dir/metrica/` if absent (download to `.part`, then rename).
  - `spv data fetch metrica [--game N]` calls it (default games 1 and 2).

- [ ] **Step 1: Write the fixtures:** two tiny CSVs in Metrica's layout (made up, not copied): 3 home players (one NaN for the first 10 frames = a substitute coming on), 2 away players, ball, 50 frames at 25 Hz.
- [ ] **Step 2: Write failing tests:**
  - `test_axes`: a fixture player at (u, v) = (0.0, 1.0) → (0, 0) m; (1.0, 0.0) → (105, 68).
  - `test_resample_rate`: 50 frames at 25 Hz (0.04–2.0 s) → `rate == 10`, times on a 0.1 s grid inside the source span, `len(times) == 20`.
  - `test_absent_player_stays_nan`: the substitute is NaN for times before frame 10 and not NaN after.
  - `test_ids_and_teams`: ids built from jersey numbers, `teams.count("home") == 3`.
  - `test_ensure_metrica_skips_existing(tmp_path, monkeypatch)`: pre-created files → no network call (urlopen patched to raise).
- [ ] **Step 3: Run** `pytest tests/sim/test_tracks.py -v` → FAIL.
- [ ] **Step 4: Implement.** Then run `spv data fetch metrica` once locally and load game 2: print T, N and the first time a substitute appears (expect a full match, ~5,500 s; note the time in the commit message).
- [ ] **Step 5: Run** tests → PASS.
- [ ] **Step 6: Commit** `feat: Metrica tracking data loader for the simulator`.

### Task 7: Simulated ball-following camera

**Files:**
- Create: `src/spv/sim/camera.py`, `tests/sim/test_camera.py`

**Interfaces:**
- Consumes: `PitchTracks` (Task 6).
- Produces:
  - `CameraParams` (frozen dataclass) with defaults: `mast_back_m=3.0`, `mast_height_m=8.0`,
    `lag_s=0.7`, `view_width_m=35.0`, `hfov_min_deg=20.0`, `hfov_max_deg=70.0`, `aspect=16/9`,
    `margin_m=5.0`. These are starting values; build step 2 tunes them to clip1's solved camera.
  - `CameraPath` dataclass: `mast: tuple[float, float, float]`, `aim_xy (T, 2)`, `hfov_deg (T,)`,
    `footprint: list[shapely.Polygon]`.
  - `simulate_camera(tracks: PitchTracks, params: CameraParams = CameraParams()) -> CameraPath`.
  - `in_view(path: CameraPath, t: int, xy: np.ndarray) -> np.ndarray` (bool per point; NaN → False).

Algorithm (not determined by the signature):
- Mast at `(L/2, -mast_back_m, mast_height_m)`.
- Aim: `aim[0]` = first known ball position (pitch centre if none); then
  `aim[t] = aim[t-1] + (ball[t] - aim[t-1]) * (1 - exp(-dt / lag_s))`; a NaN ball holds the aim.
- Zoom: `hfov = 2 * atan(view_width_m / 2 / ground_distance(mast, aim))`, clipped to the min/max.
- Footprint: camera looks from the mast at the aim point on the ground; cast the four image-corner
  rays (vertical FOV from `aspect`); each ray meets z = 0, or, if it points at or above the
  horizon, is cut at 200 m horizontal distance; the quadrilateral is intersected with the pitch
  rectangle grown by `margin_m`.

- [ ] **Step 1: Write failing tests** (synthetic `PitchTracks`, no download):
  - `test_static_ball_in_view`: ball fixed at the centre spot for 10 s → for t ≥ 30, `in_view` of the ball is True and the aim is within 0.01 m of it.
  - `test_lag`: ball jumps 30 m at t = 5 s → aim has moved 63 % ± 3 % of the way after `lag_s`.
  - `test_far_ball_zooms_in`: ball on the far touchline → smaller `hfov` than on the near one.
  - `test_footprint_inside_grown_pitch`: every footprint is within the pitch rectangle grown by `margin_m` (+1e-6).
  - `test_near_horizon_does_not_crash`: `mast_height_m=0.5`, ball at the far corner → a valid, non-empty polygon.
  - `test_ball_nan_holds_aim`: NaN ball for 2 s → aim unchanged during it.
- [ ] **Step 2: Run** `pytest tests/sim/test_camera.py -v` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: simulated ball-following camera`.

### Task 8: Simulated detections, scenes, scoring

**Files:**
- Create: `src/spv/sim/detections.py`, `src/spv/sim/scenes.py`, `src/spv/check/__init__.py`,
  `src/spv/check/score.py`, `tests/sim/test_detections.py`, `tests/sim/test_scenes.py`,
  `tests/check/test_score.py`

**Interfaces:**
- Consumes: `PitchTracks` (6), `CameraPath`, `in_view` (7), `TrackFile`, `decode`, `State`, `slot_ids` (2, 3).
- Produces:
  - `DetectionParams` defaults: `miss_rate=0.05`, `crowd_radius_m=1.0`, `crowd_miss_rate=0.30`,
    `noise_base_m=0.3`, `noise_per_m=0.01` (× distance from the mast), `false_per_moment=0.5`,
    `team_flip_rate=0.03`, `ball_miss_rate=0.30`. Starting values, to be measured on clips in step 3.
  - `Detections` dataclass: `moment (D,) int`, `xy (D, 2)`, `team (D,) int8` (0 home, 1 away),
    `is_ball (D,) bool`, `conf (D,) float`, `truth (D,) int` (index into `tracks.ids`, −2 for the
    ball, −1 for a false detection).
  - `simulate_detections(tracks, camera, params=DetectionParams(), seed=0) -> Detections`. Only
    in-view objects can be detected; false detections uniform in the footprint, team random.
  - `Scene(name: str, start: int, stop: int)`; `find_scenes(tracks, camera, length_s=60.0) -> list[Scene]`
    returning, in this order: `crowded_box` (window with the most moments having ≥ 10 players
    within 20 m of a goal line), `long_out_of_view` (window holding the longest out-of-view stretch
    of any one player), `substitution` (window starting 10 s before the first substitute
    appears). Deterministic for given inputs. No substitute → `ValueError`.
  - `null_solver(detections: Detections, n_moments: int, rate: float, pitch: tuple[float, float]) -> TrackFile`
    — every slot UNKNOWN; the placeholder stage 4 replaces.
  - `score_positions(track: TrackFile, truth: PitchTracks, start: int, stop: int) -> dict[str, float]`:
    slots are matched to truth players per team by `scipy.optimize.linear_sum_assignment` on mean
    distance over the moments both have positions (a slot with no positions matches nobody);
    returns `within_2m` (share of truth player-moments whose matched slot is SEEN/PREDICTED and
    within 2 m), `seen_share`, `false_players` (share of slot-moments with a position but no
    truth player on the pitch).
  - `track_from_truth(truth: PitchTracks, start: int, stop: int, unc_m: float = 0.0) -> TrackFile`:
    every on-pitch truth player SEEN in a slot of its team; a substitute takes the first slot
    freed in its team. Known limit: a slot that changed player at a substitution is scored
    against one of them only; identity scoring arrives with stage 4.

- [ ] **Step 1: Write failing tests:**
  - `test_rates` (synthetic tracks, 20 players spread out, 2,000 moments, all in view): recall 0.95 ± 0.02, false detections per moment 0.5 ± 0.1, team flips 0.03 ± 0.01.
  - `test_crowding_raises_misses`: two players 0.5 m apart → miss rate 0.30 ± 0.03.
  - `test_out_of_view_never_detected`: truth index of every detection is in view at its moment.
  - `test_seed_reproducible`: same seed → identical arrays.
  - `test_scenes_on_synthetic`: synthetic match with a planted crowd at 120 s and a substitute at 300 s → `crowded_box` covers 120 s, `substitution.start == round(290 * rate)`.
  - `test_score_perfect`: a `TrackFile` built from truth (all SEEN) → `within_2m == 1.0`, `false_players == 0.0`.
  - `test_score_null`: `null_solver` output → `within_2m == 0.0`, `seen_share == 0.0`.
  - `test_score_slot_order_irrelevant`: truth with slots shuffled → still 1.0.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: simulated detections, scenes and position scoring`.

### Task 9: Regression check and the simulator suite

**Files:**
- Create: `src/spv/check/measures.py`, `src/spv/check/suites.py`, `tests/check/test_measures.py`,
  `tests/baselines/sim.json`, `tests/results/sim.md`
- Modify: `src/spv/cli.py` (`check`)

**Interfaces:**
- Consumes: Tasks 3, 6–8.
- Produces:
  - `Measure` (frozen): `name: str`, `value: float`, `better: Literal["higher", "lower"]`,
    `margin: float`, `relative: bool = False` (margin as a fraction of the baseline).
  - `Outcome` (frozen): `name`, `baseline: float | None`, `current: float | None`,
    `status: Literal["same", "better", "worse", "new", "missing"]`.
    "worse" only beyond the margin; "better" when beyond the margin the right way; `"missing"`
    when a baselined measure was not produced.
  - `compare(measures: list[Measure], baseline: dict[str, float]) -> list[Outcome]`.
  - `load_baseline(path: Path) -> dict[str, float]`; `save_baseline(path, measures)`;
    `results_table(outcomes) -> str` (markdown: measure | baseline | now | status).
  - `sim_suite(data_dir: Path) -> list[Measure]`: Metrica game 2 → camera → detections (seed 0)
    → for each scene: `null_solver` → `score_positions`. Measures per scene `s`:
    `sim.{s}.within_2m` (higher, margin 0.01), `sim.{s}.false_players` (lower, 0.01),
    `sim.{s}.ball_in_view` (higher, 0.02); plus `sptrack.roundtrip_max_error_m` (lower, 0.001)
    from writing and reading the truth of the first scene.
  - `spv check [--suite sim|clips|all] [--update-baselines]` → prints the table, writes
    `tests/results/<suite>.md`, exit 1 if any outcome is "worse" or "missing".
    `--update-baselines` writes new and better values only, and refuses (exit 1) if anything is worse.
    `all` is the default; a suite without its data (no clips configured) is reported as skipped.

- [ ] **Step 1: Write failing tests:**
  - `test_compare_statuses`: lower-better margin 0.1, baseline 1.0 → current 1.05 "same", 1.2 "worse", 0.8 "better"; unknown name "new"; baselined name absent "missing".
  - `test_relative_margin`: relative 0.5, baseline 10 → 14 "same", 16 "worse".
  - `test_update_refuses_when_worse(tmp_path)`.
  - `test_table_has_every_measure`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: First baseline.** `spv check --suite sim --update-baselines`, then `spv check --suite sim` → exit 0. Expected: `within_2m` 0.0 for every scene (null solver), round-trip error ≤ 0.005, `ball_in_view` near 1.
- [ ] **Step 6: CI.** Add to `ci.yml`: cache `data/metrica` (key on the URL list), `spv data fetch metrica --game 2`, `spv check --suite sim`.
- [ ] **Step 7: Commit** `feat: spv check and simulator suite` with the results table in the message.

### Task 10: First reference clip

**Files:**
- Create: `tests/clips/clip1.json`, `tests/clips/clip1.lineup.json`, `tests/baselines/clips.json`,
  `tests/results/clips.md`, `tests/check/test_clips.py`
- Modify: `src/spv/config.py`, `src/spv/check/suites.py`, `src/spv/cli.py` (`clip add`)

**Interfaces:**
- Consumes: `ProbeStage`, `default_stages`, `run_pipeline` (5); `Measure` (9); `load_local_config` (6).
- Produces:
  - `clip_identity(path: Path) -> dict` → `{"size": int, "sha256_head_tail": str}` (sha256 of the
    first and last 16 MB), plus probe fields `duration_s`, `fps`, `width`, `height`.
  - `spv clip add NAME PATH`: writes `clips.NAME = PATH` into `local.config.json` (creating it)
    and `tests/clips/NAME.json` = `{"name", **clip_identity}` — no path. If
    `tests/clips/NAME.lineup.json` is missing, writes a generic 11 v 11 lineup (ids `h1`…`h11`,
    `a1`…`a11`, no names: the clips show minors).
  - `clips_suite(repo_root: Path) -> list[Measure] | None` (None when no clips are configured):
    for each configured clip, checks identity against `tests/clips/NAME.json` (mismatch →
    `RuntimeError` saying the file changed), runs `default_stages()` with a fresh cache in a temp
    folder and measures `clip.NAME.runtime_s_per_video_min` (lower, relative margin 0.5).
    Later steps add the stage measures (camera, detector, …) and their known answers here.
    The spec puts "the first reference clip with its known answers" in the foundation; each
    answer needs the stage that produces it (held-out landmarks need the keypoint model, the
    offline player pass needs the detector), so this step registers the clip and its run-time
    measure, and each later plan adds its own known answers for clip1 as its first task.

- [ ] **Step 1: Write failing tests** (tmp folder as repo root, the `tiny_video` fixture as the clip):
  - `test_clip_add_writes_config_and_metadata`: config holds the path; `tests/clips/x.json` has no `"path"` key and no string containing the clip's folder.
  - `test_clips_suite_detects_changed_file`: append bytes to the video → `RuntimeError` mentioning "changed".
  - `test_clips_suite_none_without_config` → `None`.
  - `test_clips_suite_runtime_measure`: returns one measure named `clip.x.runtime_s_per_video_min`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Register clip1.** `spv clip add clip1 "<path to clip1.mp4>"`, then
  `spv check --suite clips --update-baselines`, then `spv check` (all) → exit 0. Check
  `git status` shows no `local.config.json` and no video.
- [ ] **Step 6: Commit** `feat: reference clip registration and clips suite` with both results tables.

### Task 11: Docker image, README, PR

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `README.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: image `statpadder-vision` whose entrypoint is `spv`, running the same job file:
  `docker run --rm -v <folder>:/work statpadder-vision process --job /work/job.json`.

- [ ] **Step 1: Dockerfile**: `python:3.10-slim`, `apt-get install -y --no-install-recommends ffmpeg`, copy `pyproject.toml` + `src/`, `pip install .`, `ENTRYPOINT ["spv"]`. `.dockerignore` excludes `data/`, `.venv/`, `tests/`, `*.mp4`, `local.config.json`.
- [ ] **Step 2: CI job `docker`**: build the image; make a 3 s `testsrc` video and a job in `$RUNNER_TEMP`, copy `tests/fixtures/lineup_11.json` beside it; `docker run` the job; assert the `.sptrack` exists. (Docker isn't installed locally; CI is the check.)
- [ ] **Step 3: README**: purpose (one paragraph from the spec), install (`python -m venv .venv`, `pip install -e .[dev]`), `spv process`, `spv check`, `spv clip add`, where data lives (`local.config.json`, `SPV_DATA_DIR`, clips in personal OneDrive, never in the repo), link to the spec.
- [ ] **Step 4: Full check locally**: `pytest -q` and `spv check` → both pass.
- [ ] **Step 5: Commit** `chore: Docker image, README, CI docker job`.
- [ ] **Step 6: Push and PR** (once `TCannonx/statpadder-vision` exists): push
  `feature/01-foundation`, open a PR through the REST API whose description holds both results
  tables, wait for CI (tests, sim suite, docker), merge after it passes.
