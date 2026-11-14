# P0: can the event files be trusted?

| Match | Offset h1 (s) | Spread h1 (s) | Offset h2 (s) | Spread h2 (s) | A attacks (h1/h2) | Spot checks right | Usable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| m01 | +0.25 | 0.50 | +0.50 | 0.50 | left/right | 19/20 | yes |
| m03 | +0.50 | 0.50 | +0.50 | 0.50 | left/right | 20/20 | yes |
| m13 | +0.50 | 0.00 | +0.50 | 0.00 | right/left | 19/20 | yes |

**Verdict:** GO

Gate: anchors within 1 s per half (at least 3), attacking direction consistent, at least 90% of spot checks right.
Anchors and spot checks were judged by eye by Claude from contact sheets; the frames stay in runs/ and are never committed.

## Notes

**Which videos.** P0 was run against the cut videos the event files were coded on, downloaded from the event supplier, not the Hudl copies. On m03 the Hudl copy did not line up with the file inside half 1: a corner the file places at 27:28 was confirmed in the supplier's cut but was not at the matching point in the Hudl copy. The Hudl copies used for the eight training matches will need their own alignment, ideally an automatic one with drift detection, before anything trains on them.

**Timing: strong.** Every half of every P0 match lines up at an offset of about +0.5 s with a spread of at most 0.5 s. No drift was seen. Anchors were kick-offs, which are the clearest moment on this camera, plus corners judged from the reaction in the box, because the corner flag is rarely in shot.

**Spot checks: what "right" means here.** The gate passes, but the place and team verdicts are weak, because the wide, ball-following view seldom shows the taker or the touchline at contact-sheet size.

| Match | Moment off | Place confirmed | Place unsure | Team confirmed | Team unsure |
| --- | --- | --- | --- | --- | --- |
| m01 | 1 | 6 | 14 | 3 | 17 |
| m03 | 0 | 6 | 14 | 5 | 15 |
| m13 | 1 | 6 | 14 | 0 | 20 |

- "Unsure" counts as right under the gate, so the 19/20 and 20/20 scores test timing and event type far more than place and team.
- On several free kicks, goal kicks and throw-ins the restart itself is off camera. These were marked as right on context, because play is stopped and players are waiting where the file puts the restart.
- Kit reads from contact sheets were unreliable. On m03 the first read had the two teams the wrong way round and was corrected by Thomas. On m13 the kits were not settled by eye, so no team verdict there is confirmed.

**The two misses.**
- m01, a shot logged about 2.5 to 3 s before the strike. The goal row for the same attack is on time.
- m13, a free kick logged before the foul that leads to it. The free kick is not taken within 2 s of the logged time.

**Hand-coded matches.** Every StatPadder export checked carries `video_ms` on all rows. The older hand-coded files carry video seconds from 2024 onwards, and the two from 2023 carry none.

**How sure.** High confidence in timing and in the type of event. Low confidence in place and team. P1 should not lean on these files for team or zone accuracy until those fields are checked another way, for example against detected kits and camera position.
