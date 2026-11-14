# P0: can the event files be trusted?

| Match | Offset h1 (s) | Spread h1 (s) | Offset h2 (s) | Spread h2 (s) | A attacks (h1/h2) | Spot checks right | Not visible (replaced) | Usable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| m01 | +0.25 | 0.50 | +0.50 | 0.50 | left/right | 19/20 | 20 | yes |
| m03 | +0.50 | 0.50 | +0.50 | 0.50 | left/right | 20/20 | 30 | yes |
| m13 | +0.50 | 0.00 | +0.50 | 0.00 | right/left | 13/15 | 54 | not testable: camera too far from most restarts; only 15 visible rows |

**Verdict:** GO

Not testable (excluded from the verdict, decided by Thomas): m13.

Gate: anchors within 1 s per half (at least 3), attacking direction consistent, at least 90% of spot checks right.
Anchors and spot checks were judged by eye by Claude from contact sheets; the frames stay in runs/ and are never committed.

## Notes

**How the spot checks were judged (strict rubric).** A row counts only if the event itself is visible in the frames: the throw being taken, the keeper striking a goal kick, the box reacting to a corner delivery, a kick-off starting, or a goal celebration. A row whose event is off camera or too small to see is marked not visible and replaced by another row, so each match is meant to be judged on 20 rows that could actually be seen. After the first round, replacements were drawn only from corners, throw-ins, kick-offs and goals, because replacement free kicks, goal kicks and shots were almost never visible on this camera. Alignment anchor rows were never used as replacements.

| Match | Visible rows | Right | Not visible | Team confirmed | Place confirmed |
| --- | --- | --- | --- | --- | --- |
| m01 | 20 | 19 | 20 | 8 | 14 |
| m03 | 20 | 20 | 30 | 10 | 9 |
| m13 | 15 | 13 | 54 | 1 | 9 |

**Why m13 is excluded.** m01 and m03 pass. Thomas decided (2026-11-14) to accept GO on those two and record m13 as not testable: it fails on coverage, not on coding: its camera sits far from most of the action, and only 15 rows could be judged before the useful candidates ran out (most remaining rows are far-side throw-ins). Of the 15, 13 are right.

**What the files got wrong where it could be seen.** Three misses in 55 visible rows:
- m01, a shot logged about 2.5 to 3 s before the strike (the goal row for the same attack is on time).
- m13, a free kick logged before the foul that leads to it.
- m13, a free kick taken about 4 s after its logged time.

**Timing: strong.** Every half of every P0 match lines up within 1 s, with no drift. Kick-offs sit at about 0.0 s and corners at +0.5 s; that half-second is the delay of judging a corner from the box's reaction, not drift.

**Which videos.** P0 was run against the cut videos the event files were coded on, downloaded from the event supplier, not the Hudl copies. On m03 the Hudl copy did not line up with the file inside half 1: a corner the file places at 27:28 was confirmed in the supplier's cut (by Thomas) but was not at the matching point in the Hudl copy. The Hudl copies used for training matches need their own alignment before anything trains on them.

**Team and place.** Mostly unconfirmed: team on 8, 10 and 1 rows and place on 14, 9 and 9. Kit reads from contact sheets were unreliable (m03's teams were first read the wrong way round and corrected by Thomas). P1 should not lean on these files for team or zone accuracy until those fields are checked another way.

**Hand-coded matches.** Every StatPadder export checked carries `video_ms` on all rows. The older hand-coded files carry video seconds from 2024 onwards; the two from 2023 carry none.
