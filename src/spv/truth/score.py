"""Score predicted events against trusted truth events, per event type."""

from __future__ import annotations

from dataclasses import replace

from spv.truth.events import TruthEvent

BAR_KINDS = ("goal", "corner", "free_kick_final_third", "shot")


def group(e: TruthEvent) -> str | None:
    if e.kind == "goal":
        return "goal"
    if e.kind == "corner":
        return "corner"
    if e.kind == "free_kick":
        return "free_kick_final_third" if e.x is not None and e.x >= 2 / 3 else None
    if e.kind in ("shot", "penalty"):
        return "shot"
    return None


def to_video(events: list[TruthEvent], offsets: dict[int, float]) -> list[TruthEvent]:
    return [replace(e, video_s=e.video_s + offsets.get(e.half, 0.0)) for e in events]


def match(truth: list[TruthEvent], pred: list[TruthEvent], tolerance_s: float) -> list[tuple[TruthEvent, TruthEvent]]:
    pairs: list[tuple[TruthEvent, TruthEvent]] = []
    for g in BAR_KINDS:
        ts = [e for e in truth if group(e) == g]
        ps = [e for e in pred if group(e) == g]
        cand = [(abs(t.video_s - p.video_s), t.row_id, p.row_id, i, j) for i, t in enumerate(ts) for j, p in enumerate(ps)]
        cand = sorted(c for c in cand if c[0] <= tolerance_s)
        used_t: set[int] = set()
        used_p: set[int] = set()
        for _, _, _, i, j in cand:
            if i in used_t or j in used_p:
                continue
            used_t.add(i)
            used_p.add(j)
            pairs.append((ts[i], ps[j]))
    return pairs


def per_group(truth: list[TruthEvent], pred: list[TruthEvent], tolerance_s: float) -> dict[str, dict]:
    matched = match(truth, pred, tolerance_s)
    out: dict[str, dict] = {}
    for g in BAR_KINDS:
        n = sum(1 for e in truth if group(e) == g)
        m = sum(1 for e in pred if group(e) == g)
        k = sum(1 for t, _ in matched if group(t) == g)
        out[g] = {"truth": n, "pred": m, "matched": k, "recall": k / n if n else None, "precision": k / m if m else None}
    return out
