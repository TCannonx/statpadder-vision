# Scorer checks (P1)

Scores of event files against the trusted P0 matches (m01, m03). Ids and numbers only.

- `*-self.*`: each truth file scored against itself. Every group and the team and zone checks are 100%, as they must be. Truth is moved onto the video clock by the P0 offsets (+0.25 to +0.5 s), which is well inside both tolerances.
- `*-degraded.*`: each truth file against a copy made only for this check (never committed): all times +3 s, about 30% of restarts and shots dropped, 5 false shots added. Expected and seen: nothing matches at ±2 s (the shift is larger than the tolerance), recall about 70-75% at ±5 s, shot precision lowered by the false shots, team and zone still near 100%.
- `pool-*.md`: both matches pooled, with the bar from spec 6.4.

Real predictions arrive in P2 (Gemini on a half, written as an Eyeball-shaped file) and are scored with `spv truth score mNN <file> --label <name>`.
