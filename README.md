# statpadder-vision

StatPadder's vision module. It turns a downloaded Hudl or Veo **ball-following** recording of a
match into full tracking data: where every player and the ball are, 10 times a second, each
position marked as seen or predicted, written to one `<match>.sptrack` file that StatPadder
imports. Everything runs locally. The design is in
[`docs/superpowers/specs/2026-10-14-vision-module-design.md`](docs/superpowers/specs/2026-10-14-vision-module-design.md).

Build step 1 (foundation) is in place: the job interface, stage cache, tracking file format,
simulator and regression check. The vision stages themselves come in the following steps.

## Install

```
python -m venv .venv
.venv/Scripts/python -m pip install -e .[dev]     # Linux/macOS: .venv/bin/python
```

ffmpeg (`ffprobe`) must be on the PATH.

## Use

```
spv process --job job.json          # writes the .sptrack file and a run report
spv data fetch metrica              # public tracking data for the simulator
spv check                           # regression check: simulator + reference clips
spv check --update-baselines        # after an improvement: save new and better values
spv clip add clip1 <path to video>  # register a reference clip
```

A job file:

```json
{"video": "match.mp4", "lineup": "lineup.json", "output": "out/match.sptrack",
 "pitch": {"length_m": 100, "width_m": 64}, "rate": 10}
```

Paths are relative to the job file. `pitch` is optional. Lineup event times are seconds of the
video. The same job runs in Docker:

```
docker build -t statpadder-vision .
docker run --rm -v <folder>:/work statpadder-vision process --job /work/job.json
```

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

## Where data lives

The footage shows minors, so **no video, frame, image or clip path is ever committed**.

- `local.config.json` (git-ignored) holds reference clip paths and, optionally, `data_dir`.
- Public data downloads to `SPV_DATA_DIR`, else `data_dir` from the config, else `data/`
  (git-ignored).
- Reference clips and labelled datasets stay in personal OneDrive. The repo keeps only clip
  metadata (`tests/clips/`), baselines (`tests/baselines/`) and results (`tests/results/`).

## Every change

Run `pytest` and `spv check` before calling a change done. Put the results tables from
`tests/results/` in the change's description, and update the baselines in the same change when
a result improves. CI runs the tests, the simulator suite and the Docker image on every push.
