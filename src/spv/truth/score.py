"""Score predicted events against trusted truth events, per event type."""

from __future__ import annotations

from dataclasses import replace

from spv.truth.events import TruthEvent, zone

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


def _norm(name: str) -> str:
    return " ".join(name.casefold().split())


def _same(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    return bool(a) and bool(b) and (a in b or b in a)


def team_map(truth_names: list[str], pred_names: list[str]) -> dict[str, str] | None:
    """Prediction letter -> truth letter by team name; None when the names do not decide it."""
    if len(truth_names) < 2 or len(pred_names) < 2:
        return None
    t, p = truth_names[:2], pred_names[:2]
    same = _same(t[0], p[0]) and _same(t[1], p[1])
    swap = _same(t[0], p[1]) and _same(t[1], p[0])
    if same == swap:
        return None
    return {"A": "A", "B": "B"} if same else {"A": "B", "B": "A"}


def accuracy(pairs: list[tuple[TruthEvent, TruthEvent]], mapping: dict[str, str]) -> dict:
    team_right = zone_right = zone_of = 0
    for t, p in pairs:
        if mapping.get(p.team) == t.team:
            team_right += 1
        if t.x is not None and t.y is not None and p.x is not None and p.y is not None:
            zone_of += 1
            if zone(t.x, t.y) == zone(p.x, p.y):
                zone_right += 1
    return {"team_right": team_right, "team_of": len(pairs), "zone_right": zone_right, "zone_of": zone_of}
