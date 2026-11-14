# Scorer checks (P1)

Scores of event files against the trusted P0 matches (m01, m03). Ids and numbers only.

- `*-self.*`: each truth file scored against itself. Every group and the team and zone checks are 100%, as they must be. Truth is moved onto the video clock by the P0 offsets (+0.25 to +0.5 s), which is well inside both tolerances.
- `*-degraded.*`: each truth file against a copy made only for this check (never committed): all times +3 s, about 30% of restarts and shots dropped, 5 false shots added. At ±2 s only a couple of shots match (by chance, nearby shots); the +3 s shift is larger than the tolerance. At ±5 s (pool) recall is 100% for goals, 74% corners, 75% final-third free kicks, 64% shots, with shot precision 68%; team 100%, zone 98%. m01's own numbers are lower than the pool for free kicks (57%) and shots (56% recall, 60% precision).
- `pool-*.md`: both matches pooled, with the bar from spec 6.4.

Real predictions arrive in P2 (Gemini on a half, written as an Eyeball-shaped file) and are scored with `spv truth score mNN <file> --label <name>`.
