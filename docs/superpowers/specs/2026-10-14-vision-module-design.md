# StatPadder vision module: design

Agreed with Thomas on 2026-10-14 (approach B, section by section in chat). This supersedes the
"separate program, feasibility test first" plan in StatPadder's
`docs/superpowers/specs/2026-10-09-capture-roadmap.md` where the two differ. The roadmap's rules on
footage of minors still apply. The earlier prototype (`OneDrive\claude_development\football_tracker`)
is not built on: it "never worked correctly". Its trained weights may be tried, nothing more.

## Purpose

Turn a downloaded Hudl or Veo **ball-following** recording of a match into **full tracking data**:
where every player and the ball are, 10 times a second, for the whole match. Each position is
marked as **seen** or **predicted**, with an uncertainty in metres. Players who are off screen get
a predicted position worked out from everything else the program knows.

Most analysts only have the ball-following recording, so that is the input the module must work
on. Full-pitch footage is never an input the module relies on. Thomas set the `pats_left` /
`pats_right` recordings aside on 2026-10-14, so full-pitch truth comes from public professional
tracking data through the simulator (see Testing).

## Decisions

| Topic | Decision |
| --- | --- |
| Footage | Hudl/Veo ball-following recordings first. Broadcast TV is out of scope for now. |
| Output | Full tracking data, 10 positions a second. The rate is a field in the file, so 25 needs no format change. |
| Where it runs | On Thomas's own computer with a graphics card. Built as a processing core behind a job interface and a Docker image, so a cloud worker or the app can call the same core later. |
| Code | New repo `statpadder-vision` (Python), its own CI. StatPadder's app changes come later as ordinary StatPadder branches. |
| Who is who | Assisted naming in StatPadder: the module keeps each player as one identity; the analyst names the 22 against the lineup. |
| Lineup first | The match must exist in StatPadder with its lineup, substitutions and red cards before processing. The module reads them to know how many players each team has at each moment. |
| Referees | Detected so they can be excluded. Not in the output. |
| Storage | Tracking files stay on the device in the app. Uploading them is decided later. |
| Licensing | StatPadder is not sold. Public data and models are used under their non-commercial terms, so licences don't block development. |
| Manual work | As little as possible, for the analyst and for building the module. Hand labelling is a last resort. |
| AI services | None. Everything runs locally. The roadmap's optional cloud AI step is not part of this design. |

## How it fits together

```
video ─► 1 camera solver ──► camera per frame + area of pitch in view
      └► 2 detector ───────► people and ball in the picture
            └► 3 appearance ► kit / re-identification features
                     │
   lineup ──────────►▼
              4 match-state solver ◄──► 5 off-screen predictor
                     │     (correction loop over the whole match)
              6 ball │
                     ▼
              7 exporter ─► match.sptrack ─► StatPadder (import, naming, views)
```

Every stage writes its output to a cache folder for the run. A later stage can be re-run without
redoing earlier ones, and each stage can be tested on its own.

## The stages

### 1. Camera solver

- A keypoint model finds the 28 pitch landmarks (box corners, line crossings, centre circle
  points) in each frame. It is trained on Thomas's Roboflow pitch keypoint dataset (about 20,000
  annotated images), with the 9,992 frames already on disk as a fallback.
- The camera on its mast doesn't move. One mast position and lens distortion are solved for the
  whole match. After that, each frame has only pan, tilt and zoom.
- The fit runs over the whole match at once (bundle adjustment with smoothness over time).
  Frames with few landmarks in view are carried by their neighbours. Pans that move the
  background but show no lines are followed by optical flow.
- Pitch size: the penalty box (16.5 m by 40.32 m) and centre circle (9.15 m radius) are the same
  on every full-size pitch, so they fix the scale. The pitch's length and width are solved with
  the camera. The analyst can enter the size if it is known, and that overrides the solved one.
- Output for each frame: the camera, a confidence, and the **area of pitch in view** (a polygon
  in metres). Frames that can't be solved are marked, not guessed.
- Risk to measure first: Hudl's picture is a crop of two stitched lenses, so a single
  pan-tilt-zoom camera may not fit it exactly. If it doesn't, a per-frame correction is added on
  top.

### 2. Detector

- Finds players, goalkeepers, referees and the ball in each frame. Where a person stands is the
  bottom centre of their box.
- The ball is also searched for in overlapping tiles of the picture, so a small, distant ball
  isn't missed.
- Starting point: a YOLO model fine-tuned on Thomas's own Roboflow players and referees dataset
  and the public Roboflow football set, then on frames from his own matches as they are
  corrected.
- Every detection keeps its confidence. Nothing is thrown away at this stage; stage 4 decides.

### 3. Appearance

- A feature for each person detection, for two jobs: which team (kit colours, grouped
  automatically per match with no training per match) and recognising the same player again
  after a gap.
- Goalkeepers and referees are told apart by kit as well as by the detector's class.

### 4. Match-state solver (the core)

The module's model of the match: 11 + 11 players and a ball that **always exist**, moving in
metres on the pitch. Squad numbers come later from naming. Here a player is a slot such as
"home 4".

1. **Project** every person detection to the pitch using its frame's camera.
2. **Short track pieces.** Link detections that are certainly the same person from frame to
   frame (close together, consistent movement, similar appearance). Stop a piece wherever there
   is doubt.
3. **Assign pieces to slots over the whole match.** This is one global optimisation, not a
   frame-by-frame decision. Its costs:
   - movement no person can make (over about 10 m/s, or sudden turns at speed);
   - kit that doesn't match the slot's team;
   - more players on a team than the lineup allows at that moment;
   - a slot whose predicted position is inside the area in view, with no detection to explain
     it;
   - a piece left unassigned. This is allowed, at a cost, for spectators, coaches, substitutes
     warming up and false detections.
4. **Predict** each slot's unseen stretches (stage 5).
5. **Score again** using the predictions, and reassign. Repeat 3 to 5 until the assignment
   stops changing or a set number of rounds is reached.

This loop is the **retrospective correction** Thomas asked for. A detection that looked like a
player on its own frame is dropped if the frames before and after show it can't be one. Two
slots that swapped identity in a crowd are swapped back once later frames show who went where.
A position is moved when the predicted path shows it was wrong. Every change is written to a
**correction log** with the frames, what changed and why, so it can be checked and tested.

Substitutions and red cards from the StatPadder lineup set when a slot is filled, emptied or
taken by a new player.

### 5. Off-screen predictor

For each stretch where a slot isn't seen, it predicts the path from:

- where the player was last seen and where they are next seen (both ends of the gap, since the
  match is processed after the fact);
- the ball;
- every visible teammate and opponent, and so the team's shape;
- the area in view (a predicted path must stay outside it, or it would have been seen).

The output is a position and an uncertainty radius for each moment.

Two versions are built and measured against each other:

- **Baseline.** Smooth movement between the two sightings, held to the player's place in the
  team's shape (their offset from the team's centre and lines), and kept out of the area in view.
- **Learned model.** A model that looks both forwards and backwards in time across players
  (a transformer over time and players). It is trained on public full-pitch professional
  tracking data, with a simulated ball-following camera hiding the players it wouldn't show
  (see Testing). The candidate sources, to be confirmed as available at build time: DFL /
  Bundesliga open tracking data, Metrica Sports sample matches, PFF FC's 2022 World Cup data,
  SkillCorner open data.

The learned model replaces the baseline only if it is more accurate on held-out simulator
matches with the camera tuned to Thomas's clips. Professional movement differs from academy
movement, so if full-pitch footage of his own matches is used later, the measurement on it
decides instead.

### 6. Ball

- Tracked on its own from ball detections, with the camera's movement as a strong clue (the
  camera follows the ball).
- Marked on the ground or in the air. A ball in the air has no true place on the ground; while
  it is in the air its position is the line between where it was kicked and where it next
  touches a player or the ground.
- Short gaps are filled. Long gaps are left as unknown, not invented.

### 7. Exporter: the tracking file

One file per match, `<match>.sptrack`: a zip holding

- `manifest.json`: format version, module version, rate (10 per second), pitch length and
  width, coordinate system, teams, slots and the substitutions applied, and the run's quality
  measures (share of frames with a camera, share of positions seen, mean uncertainty);
- `positions`: for each moment and slot, x and y in centimetres (16-bit), uncertainty (8-bit,
  0.25 m steps) and a state (seen, predicted, not on the pitch, unknown). The ball uses the same
  layout plus on the ground or in the air;
- `view`: the area of pitch in view at each moment;
- `pieces`: which track pieces became which slot, for naming in the app;
- `corrections`: the correction log.

**Coordinates**: metres from the corner flag on the camera's near-left, x along the near
touchline, y towards the far touchline. The app converts these to its own pitch scale using the
manifest's pitch size.

A full match is about 5,400 seconds × 10 × 23 objects × 6 bytes, roughly 7.5 MB before
compression, and much less after. It is a file in the app's local database, never one record per
position.

### 8. Job interface

- `spv process --job job.json`. The job holds the video's path, the StatPadder match's lineup
  export, pitch size if known, and options. The run writes the `.sptrack` file and a run report.
- The same core ships as a Docker image with the same job file. A cloud worker or a later
  in-app trigger calls that image and nothing else.
- Each stage's cache makes a run resumable after a crash or a stop.

## Testing

Thomas asked that every addition be tested on a short video before it counts as done, with as
little manual work as possible. Three layers do that.

### Simulator (no video, perfect answers)

Takes public full-pitch tracking data and plays it through a **simulated ball-following
camera**: it pans and zooms after the ball with a realistic lag. The camera's behaviour is tuned
to match Thomas's clips (how much of the pitch is in view, how fast it pans). From that it makes
the detections stages 2 and 3 would give, with misses, false detections, crowding and position
noise added at measured rates.

The match-state solver and the predictor run on this with the true answer known for every
player at every moment. It needs no labelling, runs in CI without a graphics card, and covers
every kind of failure on demand (a crowded corner, a long stretch out of view, a substitution).

### Reference clips (real video)

Short clips from Thomas's recordings: 30 to 60 seconds each, with pans, zooms, a crowded box
and play at both ends. They live in personal OneDrive, never in the repo, because they show
minors. A git-ignored local config file holds their paths.

The first reference clip is `<club folder>\clip1.mp4` (45 s, May 2026). More are added as they are
needed. Their known answers come with as little hand work as possible:

- **Camera**: landmarks Thomas has already labelled where the clip overlaps them. Otherwise
  landmarks are held back from the solve and measured.
- **Detector**: measured on the held-out part of Thomas's Roboflow datasets, which are already
  labelled.
- **Players and ball in view**: a slow, high-accuracy offline pass (the largest detector and
  tracker that fit) proposes the answers. They are checked by eye on a sample of frames and
  corrected only where clearly wrong.
- **Off-screen positions**: these can't be known from a ball-following clip, so they are
  measured on the simulator only. On the reference clip the predictor is checked for staying
  outside the area in view and for consistency with the next sighting.
- **Hand labelling** is used only if these fail.

### The regression check

- `spv check` runs every stage on every reference clip and on the simulator scenes. It compares
  each measure with the saved baseline in `tests/baselines/` and fails if one gets worse by more
  than its allowed margin.
- Measures:

| Stage | Measures |
| --- | --- |
| Camera | landmark error in pixels; position error in metres; share of frames solved |
| Detector | hits and misses of people and the ball |
| Match-state solver | identity switches; positions correct within 2 m; false players kept |
| Predictor | error in metres for unseen positions, by length of the gap; how often the truth falls within the uncertainty radius |
| Whole run | run time per minute of video |

- **Every change runs the check before it is called done.** The results table goes in the
  change's description, and a better result updates the baseline in the same change.
- **CI** (no graphics card, no video) runs unit tests and the simulator scenes on every push.
  The reference clips run on Thomas's computer, and their results file is committed with the
  change.

## Build order

Each is its own plan and set of changes, and each has to pass the check before the next starts.

1. **Foundation.** Repo, job interface, stage cache, tracking file format and its reader, the
   regression check, the simulator, and the first reference clip with its known answers.
2. **Camera solver.** Gate: at least 80% of frames solved on the reference clips, with half of
   position errors within 3 m (the roadmap's gate 1). Below 60%, stop and rethink with Thomas.
3. **Detector and appearance.**
4. **Match-state solver** with the correction loop, first on the simulator, then on clips.
5. **Off-screen predictor**: baseline, then the learned model, measured against each other.
6. **Ball.**
7. **StatPadder**: importing a `.sptrack` file into a match, naming the slots against the
   lineup, and a first view (play-back on the pitch, seen and predicted drawn differently).
   This is designed in StatPadder's own repo when it comes.

## Open items

- **Roboflow datasets**: Thomas has two in Roboflow: about 20,000 images annotated with pitch
  keypoints, and one annotated with players and referees. He will give their URLs for export.
  The local fallback is 9,992 frames of landmark labels
  (`<club folder>\statpadder\Automation\football_analysis\coco_keypoints_annotations.json`, and the same
  as YOLO files in `yolo_dataset`). Downloaded datasets stay in personal OneDrive, never in the
  repo.
- **Graphics card**: NVIDIA GeForce RTX 2060, 6 GB (driver 595.95, CUDA 13.2), read on
  2026-10-14. Small and medium YOLO and keypoint models train locally with modest batch sizes;
  the learned predictor is kept small, or trained elsewhere if 6 GB proves too tight.
- **Academy pitches** with several sets of markings and no full-size boxes: the camera solver
  will need a fallback. Measured on the reference clips before deciding how.
