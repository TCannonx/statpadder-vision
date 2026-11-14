# StatPadder vision: events-first action plan

Written 2026-11-13 at Thomas's request: "a model that takes Hudl match footage and extracts event
data at least, tracking if possible ... can leverage AI credits ... scope how expensive". He asked
for a strict, fresh-eyes view of the existing repo work. Decisions are in section 2. Where this
differs from `2026-10-14-vision-module-design.md` and `2026-10-14-camera-solver-design.md`, this
plan wins. Phase plans follow in `docs/superpowers/plans/`.

**Revised 2026-11-13 (second pass).** Thomas: "get something into the app sooner. the concept needs
to be proven before a long time gets spent on training. the output needs to be usable, accurate (to
a point) and valuable." The plan is now two stages: a **proof of concept** with no training at all
(section 6), and only if it passes, the **build-out** (section 7). The proof of concept also tests
the event files themselves before anything depends on them.

## 1. Where the existing work stands (strict review)

An independent review of `feature/02-camera` (8e7fb19) found:

- **No part of the vision stack has run on real footage.**
  - The keypoint model was never trained.
  - The camera gate was never measured.
  - `tests/results/clips.md` holds one number: 0.09 s of runtime with no camera stage.
  - The simulator's tracking scores are zero because the tracker is a stub
    (`sim/scenes.py:68-71`).
- **The front end is the weak point.**
  - The keypoint model is trained only on game-engine frames.
  - Four of its 28 "landmarks" (12/13/22/23) are not real markings. The solver and the grader
    disagree on where they are.
  - Self-training keeps only the frames the model already gets right, and accepts new weights by
    scoring on clip1, the only test clip.
- **The scope runs ahead of the goal.** It aims at 22 fixed slots, a learned off-screen predictor
  and a correction loop. After four weeks there was no code for detection, ball, teams or events.

| Module | Verdict |
| --- | --- |
| job, lineup, cli, cache, pipeline | Keep |
| check harness | Adapt: add event measures |
| camera model / initial | Keep, for the build-out |
| camera solve, flow, lines | Shelve until the build-out; then adapt as a smoother over an off-the-shelf calibrator |
| keypoints (synthetic YOLO), self_train | Discard |
| label page | Keep (used only if all else fails: Thomas does no labelling) |
| sim | Shelve |
| `.sptrack` | Shelve until tracking is in scope |
| Spec stages 4-5 (slots, learned predictor) | Shelve |

`feature/02-camera` stays unmerged as a parts bin. New work branches from `main`.

## 2. Decisions (Thomas, 2026-11-13)

| Topic | Decision |
| --- | --- |
| Approach | **Prove the concept before training anything.** Something usable goes into the app first; long training only after the proof of concept passes. |
| Bar for the output | Usable, accurate to a point, valuable. Made measurable in section 6.4. |
| Footage | A wide, ball-following view is the expected input. Fisheye, panorama, or left and right recordings are a bonus, never required. |
| Ground truth | About 20-30 matches have both the video and trusted events (Eyeball files or hand-coded against the video clock). |
| Minors and AI | "Whatever is necessary for best results." Short clips or the whole match may go to a hosted model. Still required: the provider's terms must keep the data out of training, confirmed for the provider and plan before the first real upload; no names in requests or file names; and the Privacy Notice line about match video being processed this way. This replaces the 2026-10-09 frames-only rule. |
| Labelling | **None by Thomas.** Training data comes from public labelled datasets, his existing event files, and automatic labels. |
| AI spend | Not capped up front. The proof of concept measures accuracy against cost, and Thomas decides from those numbers. |
| Machine | The RTX 2060 computer, where the clips, event files and `<data folder>` live. Building and running happen there. |
| Turnaround | Overnight is fine. Accuracy and value come before speed. |
| Priorities | Not given. Claude's default, for Thomas to change: (1) restarts, (2) shots and goals, (3) possession by team and third, (4) the team on every event, (5) passes, (6) tracking of visible players, (7) player names. The proof of concept covers (1) and (2) only. |

## 3. The key asset: event files as labels

An Eyeball file has about 2,500 rows per match (see StatPadder `docs/eyeball-events-file.md`).
Each row has a video time in seconds, the half, the team, the player, x and y in the acting team's
attacking frame, and details such as pass length, restart type, shot outcome and xG. Hand-coded
StatPadder matches carry `video_ms` and a location on each event.

Over 20-30 matches that is roughly 50,000-75,000 events, coded by professionals and placed on the
video's clock. **Whether they are as good as that is not yet known**: step P0 checks it before
anything depends on it. If they hold up, they give, with no hand labelling:

| Use | How |
| --- | --- |
| Scoring | The truth every result is measured against, in both stages. |
| Event spotter training (build-out) | Every row is a timestamped label: pass, shot, restart type, foul, out of play. |
| Calibration check (build-out) | At each event the acting player stands at a known pitch spot, to the coder's accuracy. Restarts at fixed spots are exact anchors. |
| Ball and team labels (build-out) | At pass, shot and reception times the ball is at the acting player's feet; the row's team gives colour labels. |
| Identity (later) | The player's name, at the acting position, gives per-player appearance samples. |

**Data split.** About 5 matches are **held out**: never trained on, never tuned on. The proof of
concept is scored on 3 of them. clip1 stops being special.

## 4. What the outside world does (research summary)

- **Veo** has a patent (WO2019141813 / EP3741101B1).
  - The ball is a probability map from 11 stacked frames (past and future), fed to a 3D particle
    filter.
  - Players are tracked with Kalman filters.
  - Set pieces come from a **state machine over player positions**.
  - Identity comes from shirt numbers mapped to a lineup.
  - Customers can download only the follow-cam MP4.
- **Hudl.** Assist's soccer data is tagged by human analysts (12-24 h). There is no automated soccer
  event product.
- **Metrica (Smart Tagging) and FIFA/MIT** derive events from tracking. A study with truly
  independent data found pass F1 about 0.71 and shot F1 about 0.65.
- **SkillCorner** tracks from one moving camera (about 14 of 22 players in view) and flags each
  position `is_detected` or extrapolated.
- **Open-source parts** (all broadcast-trained):

  | Need | Option | Licence |
  | --- | --- | --- |
  | Calibration | PnLCalib / NBJW | GPL-2.0, weights CC-BY |
  | Detection, teams | roboflow/sports | MIT, models AGPL |
  | Event spotter | T-DEED / dude.k | GPL-3.0 |
  | Ball | WASB-SBDT | not checked |
  | Event formats | kloppy, socceraction (SPADL) | open |

  The closest public data to this footage is SoccerTrack v2 (10 university matches, panoramic,
  ground-truth positions). Transfer from broadcast to AI-camera footage drops clearly ("Beyond
  the Premier", CVPRW 2024).
- **Hosted AI.** The best zero-shot result is GPT-5.5 on broadcast 15 s clips with commentary:
  F1 72% (goals, shots, corners, kick-offs, cards) at about $18 a match. It falls to 64% with
  frames only. No result exists for passes or pitch location. Because it needs no training,
  **hosted AI is the detector in the proof of concept**; in the build-out it moves to checking
  candidates from the trained parts, if the numbers say so.

## 5. Output: into the app with no app changes

The app's Eyeball import already does everything the proof of concept needs: it reads a
semicolon-separated file of rows with a video time, half, team, event, x/y and details, accepts an
unknown player (`-. - -`), and keeps the video time on every event.

So the proof of concept writes an **Eyeball-shaped file**:
- Rows: `pass` with `restart` set (corner-kick, free-kick, goal-kick, throw-in) for restarts,
  `shot` with `on_target`, `goal` + `goal_conceded` after a scoring shot.
- Team names as the user set the match up; player always `-. - -`.
- x/y: a coarse zone (for example the centre of the third and flank the AI names, or the fixed
  spot for corners and penalties). Marked as coarse in the vision run's own report.
- `Details` also carries `"source": "vision"`, the run version and a confidence, so the rows can
  be told apart in `supplied`.

To check during P2, not assumed: that the import's player check handles a file whose every player
is unknown without asking a question per row, and that the estimated shape step copes with no
named starters. If either fails, the fix is a small app change (a `vision` reader beside
`eyeball.ts`), still far short of a review queue.

**Reviewing in the app** uses what exists: the events list with video times, and the Hudl/Veo
time-reader to jump the video. A proper review queue (accept / fix / delete per event) is
build-out work, only if the proof of concept passes.

## 6. Stage 1: proof of concept (no training)

The question it answers: **from one match video, with no training, can we produce restarts, shots
and goals that are worth importing?** Aim: days of build, not weeks. Nothing in it is trained,
and nothing is built that the build-out depends on except the scorer and the alignment.

### 6.1 Steps

| # | Step | Work | Stop or go |
| --- | --- | --- | --- |
| P0 | **Can the event files be trusted?** | On 3 matches: inventory video + file; find each file's offset to its video from kick-offs and goals seen in the picture; check the offset is constant across each half; spot-check 20 restarts and shots per match by eye (right moment, right team, roughly the right place); set attacking direction per half. Check whether hand-coded matches carry `video_ms`. | **Go** if offsets are constant and 18 of 20 spot-checks are right. **Stop and rethink** if offsets drift or the coding is loose: the whole plan depends on these files. |
| P1 | **Scorer** | Recall and precision per event type at ±2 s and ±5 s, team accuracy, zone accuracy. Reads an Eyeball-shaped file on both sides. | Runs on the 3 matches. |
| P1b | **Where is the camera looking?** (runs alongside P2; see 6.2) | (a) Coarse: a view-position model learned from the event files, with no hand labels. (b) Fine: an off-the-shelf pitch calibrator, untrained, on a few hundred frames. Both scored against event-file positions on the held-out matches. | (a) Third right on at least 80% of event frames. (b) No pass mark; the rate of frames where the pitch is found and the error in metres decide whether the build-out can promise real locations. Both reported at the decision in 6.5. |
| P2 | **End-to-end, one match** | Whole half to Gemini (Flash and Pro) with a prompt for restarts, shots, goals, team and zone, returning JSON with times. Write the Eyeball-shaped file. Import it into the app. | It imports and shows in the app. This is the first thing Thomas sees. |
| P3 | **Improve the cheap way** | Tried in order, each scored, kept only if it helps: (a) a second pass on 10-20 s clips around each candidate to fix the time, type and team; (b) whistle onsets from the audio to snap times; (c) a pretrained, off-the-shelf player/ball detector (roboflow/sports or YOLO11) to say which half the ball is in and who is nearer, as a check on team and zone; (d) Claude on cropped stills for the hard cases. | Scores on the 3 held-out matches, with cost per match. |
| P4 | **Thomas tries it** | One full match imported; Thomas looks through it in the app against the video. | His verdict, against 6.4. |

### 6.2 How the program knows where the camera is looking (P1b)

Spotting an event, its type and its team needs no calibration: it is recognition from the picture.
Locations do, and the build-out's value (real locations, possession by third) depends on them, so
the proof of concept tests this early instead of leaving it to the build-out.

**(a) Coarse view position from the event files.** Hudl and Veo cameras follow the ball, so the
centre of the picture is roughly where the ball is. At every event row the acting player has the
ball, at a position the file gives; with the attacking direction per half from P0, that is a pitch
position. So every row is a free label: "at this video time, the view is centred near here".
- Take each event-time frame's embedding from an off-the-shelf image model (SigLIP).
- Fit a small regressor from embedding to view position along the pitch, and flank, on the training
  matches. Minutes on the RTX 2060; not the long training the plan defers.
- Between events, follow the camera's pan from the picture's global motion (optical flow) and
  correct it at each event or fixed-spot restart.
- Limits: the camera lags the ball, and the acting player is not always at the centre of the
  frame. This gives a third and a flank, not metres.

**(b) Off-the-shelf calibrator, untrained.** PnLCalib / NBJW as published, on a few hundred frames
spread over the 3 held-out matches. Measure the share of frames where it finds the pitch, and the
error of projected player positions against the event-file positions. This is the "can the pitch
be identified at a repeatable rate" test. Hours of work, no training.

The coarse model's zones replace the AI-read zones in P3 if they score better. If (a) misses the
bar and (b) rarely finds the pitch, locations are the build-out's weak point and the decision in
6.5 says so before any training money is spent.

### 6.3 What it costs

- AI: P2-P3 run on 3 matches, several variants each: about **$20-50 in all**.
- Compute: the RTX 2060 for whistle and the pretrained detector; no rented GPU.
- No labelling.

### 6.4 The bar (agreed by Thomas, 2026-11-13)

Scored on 3 held-out matches.

| Test | Bar to pass |
| --- | --- |
| **Usable** | Imports into the app with no hand editing of the file. Thomas can look through a match's vision events in under 20 minutes. |
| **Accurate, to a point** | Goals: 90% found. Corners, free kicks in the final third, and shots: 75% found, 70% of what is listed is real, at ±5 s. Team right on 90% of real events. Zone right (third and flank) on 70%. |
| **Valuable** | Thomas would rather start from it than from nothing: fixing it is quicker than coding those events himself, and the match report it gives says something true about the match. Running cost under $2 a match. |

### 6.5 The decision at the end

A short write-up: the scores, cost per match, what Thomas saw. Then one of:
- **Go:** passes the bar, or close to it with a clear reason why training would close the gap.
  Start the build-out.
- **Use as is:** good enough for restarts and shots with AI alone; run it on matches, put effort
  into the review queue, and keep training for later.
- **Stop:** far short. Nothing lost but days and tens of dollars; the event files still serve the
  app.

## 7. Stage 2: build-out (only after a "go")

Phases written in detail only when stage 1 is done, using what it measured. The likely shape:

| # | Phase | Work |
| --- | --- | --- |
| B1 | Review queue in the app | Accept / fix / delete per event, source and version on each. Comes first, so every later gain shows up in the app straight away. |
| B2 | Calibration on real footage | Off-the-shelf per-frame calibrator, then the fixed-mast smoother, graded on event-file positions and fixed-spot restarts. Below 60% of moments solved: stop and decide. Gives real locations instead of zones. |
| B3 | Detection, teams, ball | Public datasets first, then automatic labels from our footage kept only where the event files agree. |
| B4 | Trained event spotter | T-DEED family on the event files, rented GPU (about $20-60). Fused with the AI step; AI moves to checking low-confidence candidates if that is cheaper for the same accuracy. |
| B5 | Possession by team and third, passes | Rules on tracking plus the spotter. |
| B6 | Tracking of visible players, then names | Decided then. |

Every change runs `spv check` with the event measures on the held-out matches, and the results
tables go in the change, as the 2026-10-14 working style requires.

## 8. Cost scoping (prices checked 2026-11-13)

Batch processing halves all AI figures.

**AI per 90-minute match**

| Design | Cheap model | Mid model | Top model |
| --- | --- | --- | --- |
| A. Whole match to Gemini, 1 frame a second | Flash-Lite about $0.14 | Flash about $0.40 ($0.80 from January 2027) | Pro $1.10-2.10 |
| B. 150 clips of 8 s to Gemini | about $0.21 | about $0.57 | about $1.70 |
| C. 900 cropped stills at 960×540 | Haiku 5.5 about $0.11 | Sonnet 5.5 about $2.20 | Opus 5.5 about $4.30 |

**Proof of concept:** about $20-50 of AI, no rented GPU, no labelling.
**Build-out, one-off:** about $20-60 of rented GPU for training.
**Running cost:** proof of concept design (A then B) about $0.50-4 a match; target under $2.

## 9. Risks

1. **Event-file quality.** Offsets may drift and coders may be loose; P0 measures this first and
   can stop the plan.
2. **Hosted AI timing.** Whole-match models give times to a few seconds at best; P3 (a) and (b)
   exist to tighten them. The bar uses ±5 s for this reason.
3. **Team and zone from a ball-following view.** The AI may confuse teams with similar kits or
   misread the third when no lines are in view. P1b tests the view position directly. Scored,
   not assumed.
4. **Import edge cases.** A file with no named players may trip the player check or the shape
   estimate (section 5).
5. **Minors.** The section 2 conditions must hold before any upload, and the proof of concept
   uploads in P2. The Privacy Notice is still a draft (StatPadder open decision 1).

## 10. Still open

- The priority order in section 2 is Claude's default until Thomas changes it.
- Gemini is agreed for P2 (Thomas, 2026-11-13). Its plan's no-training terms are confirmed before
  the first upload.
