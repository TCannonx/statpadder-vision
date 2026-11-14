# P2: Gemini on One Half, End to End — Implementation Plan (draft, waiting on Thomas)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Do not start Task 3 or later until the "Before any upload" list below is ticked by Thomas.

**Goal:** Send one half of a held-out match to Gemini (Flash and Pro), get restarts, shots and goals back with times, team and zone, write them as an Eyeball-shaped file the StatPadder app imports unchanged, and score that file with P1.

**Spec:** `docs/superpowers/specs/2026-11-13-events-first-action-plan.md`, sections 2 (minors and AI), 5 (output), 6.1 (P2), 6.3 (cost), 9 (risks).

## Before any upload (Thomas)

1. The Gemini plan's terms keep uploaded data out of training, confirmed for the exact product and plan used (spec 2). Record where it was confirmed.
2. A Gemini API key is available on this machine, in an environment variable, never in the repo.
3. The Privacy Notice line about match video being processed this way exists (spec 2, StatPadder open decision 1).
4. Which match and half go first. Suggested: m03 half 1. Its event file was coded on the uploaded video, and it was the clearest P0 match.
5. Whether team names go in the prompt (spec 2 says no names in requests). If not, every score run needs `--teams same|swapped`, decided once per match from the kit colours Thomas confirms.

## Global constraints

- No player names, team names or drive paths in requests, file names or committed files. Teams are described by kit only ("white shirts", "maroon shirts").
- Uploaded video is a cut of one half, made locally with ffmpeg, under an anonymous file name such as `m03-h1.mp4`.
- Output rows follow `docs/eyeball-events-file.md` in the StatPadder repo: semicolon-separated, UTF-8 with BOM, columns `ID;Half;Event;Player;Team;Video time;Football time;X coordinate;Y coordinate;Details`. Player is `-. - -`. Team is the match's team names as the user set the match up in the app; these are supplied at write time from local config, never committed.
- Every row's Details carries `"source": "vision"`, the run version and a confidence.
- Cost: log the tokens and dollars per call; stop if a single half would exceed $5.

## Tasks

1. **Half cutter.** `spv vision cut mNN --half H`: cuts the half from the registered video. The start and end come from the truth file's half boundaries plus the P0 offset, with 30 s of margin. Writes `runs/vision/mNN-hH.mp4`. Tests on the tiny video.
2. **Eyeball writer.** `spv.vision.eyeball.write(events, path, team_names, run)`: writes the layout above from a list of `{time_s, half, kind, team: "A"|"B", zone or x/y, outcome}`. Corners go at the corner spot, penalties at the spot, others at the zone's centre. Round-trips through `read_events` to the same kinds, teams and times (test). Includes `goal` and `goal_conceded` rows after a scoring shot, as the app expects.
3. **Gemini client** (after the upload list is ticked). `spv vision gemini mNN --half H --model flash|pro`: uploads the cut, asks for JSON (schema: list of events with time in seconds from the start of the clip, kind in {corner, free_kick, throw_in, goal_kick, penalty, shot, goal}, team as kit colour, third and flank as the attacking team sees it, confidence 0-1), maps kit colours to A/B with the match's kit record (`tests/truth/align/mNN.json` kits, confirmed by Thomas), converts clip time to video time, writes `runs/vision/mNN-hH-<model>.csv` via Task 2, and logs cost to `runs/vision/costs.jsonl`. The prompt is kept in the repo (`src/spv/vision/prompts/half_v1.txt`) and versioned.
4. **Score it.** `spv truth score mNN runs/vision/mNN-hH-<model>.csv --label gemini-<model>-v1 --half H --teams same|swapped`. Commit only the score files.
5. **Import into the app** (Thomas, in the app): import the CSV, check it imports with no hand editing and with no question per row about unknown players. Note how long a look-through takes, as the "usable" bar in spec 6.4 requires.
6. **Write-up**: a short `tests/truth/p2_report.md`. It gives the scores for Flash and Pro, the cost per half, what the import did, and what to try first in P3.

## Self-review notes

- Spec P2 says "whole half to Gemini (Flash and Pro)" (Task 3, both models), "write the Eyeball-shaped file" (Task 2), "import it into the app" (Task 5). It is the first thing Thomas sees.
- The import check in spec 5 (unknown players, shape estimate) is Task 5. If it fails, the fix is a small app change in the StatPadder repo: a separate plan.
