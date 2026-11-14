"""Score predicted events against trusted truth events, per event type."""

from __future__ import annotations

import math
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


def score_match(
    truth: list[TruthEvent],
    pred: list[TruthEvent],
    offsets: dict[int, float],
    mapping: dict[str, str] | None,
    halves: list[int] | None = None,
    teams_given: bool = False,
) -> dict:
    """Score only the halves the prediction covers (or the given ones). An empty mapping counts as unverified."""
    scored = sorted(set(halves) if halves is not None else {e.half for e in pred})
    truth_v = to_video([e for e in truth if e.half in scored], offsets)
    pred = [e for e in pred if e.half in scored]
    if not mapping:
        label = "unverified"
    else:
        label = "given" if teams_given else "by name"
    return {
        "at_2s": per_group(truth_v, pred, 2.0),
        "at_5s": per_group(truth_v, pred, 5.0),
        "accuracy": accuracy(match(truth_v, pred, 5.0), mapping or {"A": "A", "B": "B"}),
        "team_mapping": label,
        "halves": scored,
    }


def _ratio(k: int, n: int) -> float | None:
    return k / n if n else None


def bar(result: dict) -> list[dict]:
    at = result["at_5s"]
    acc = result["accuracy"]
    rows: list[tuple[str, float | None, float]] = [("goal recall", at["goal"]["recall"], 0.90)]
    for g in BAR_KINDS[1:]:
        rows.append((f"{g} recall", at[g]["recall"], 0.75))
        rows.append((f"{g} precision", at[g]["precision"], 0.70))
    rows.append(("team", _ratio(acc["team_right"], acc["team_of"]), 0.90))
    rows.append(("zone", _ratio(acc["zone_right"], acc["zone_of"]), 0.70))
    out = [{"test": t, "value": v, "need": n, "pass": v is not None and v >= n} for t, v, n in rows]
    if result["team_mapping"] == "unverified":
        for r in out:
            if r["test"] == "team":
                r["pass"] = False
                r["note"] = "team mapping unverified"
    return out


def pool(results: list[dict]) -> dict:
    out: dict = {}
    for key in ("at_2s", "at_5s"):
        groups = {}
        for g in BAR_KINDS:
            n = sum(r[key][g]["truth"] for r in results)
            m = sum(r[key][g]["pred"] for r in results)
            k = sum(r[key][g]["matched"] for r in results)
            groups[g] = {"truth": n, "pred": m, "matched": k, "recall": _ratio(k, n), "precision": _ratio(k, m)}
        out[key] = groups
    out["accuracy"] = {f: sum(r["accuracy"][f] for r in results) for f in ("team_right", "team_of", "zone_right", "zone_of")}
    kinds = {r["team_mapping"] for r in results}
    out["team_mapping"] = "unverified" if "unverified" in kinds else ("given" if "given" in kinds else "by name")
    return out


def _pct(v: float | None) -> str:
    return "-" if v is None else f"{math.floor(v * 100 + 1e-9)}%"


def score_markdown(match_id: str, label: str, result: dict) -> str:
    lines = [
        f"# Score {match_id} ({label})",
        "",
        "| group | truth | predicted | matched | recall 2s | precision 2s | recall 5s | precision 5s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for g in BAR_KINDS:
        a, b = result["at_2s"][g], result["at_5s"][g]
        lines.append(
            f"| {g} | {b['truth']} | {b['pred']} | {b['matched']} | "
            f"{_pct(a['recall'])} | {_pct(a['precision'])} | {_pct(b['recall'])} | {_pct(b['precision'])} |"
        )
    acc = result["accuracy"]
    lines += [
        "",
        f"Accuracy at 5s: team {acc['team_right']}/{acc['team_of']} "
        f"({_pct(_ratio(acc['team_right'], acc['team_of']))}), "
        f"zone {acc['zone_right']}/{acc['zone_of']} ({_pct(_ratio(acc['zone_right'], acc['zone_of']))}). "
        f"Team mapping: {result['team_mapping']}.",
        *([f"halves scored: {', '.join(str(h) for h in result['halves'])}"] if result.get("halves") else []),
        "",
        "## Bar (at 5s)",
        "",
        "| test | value | need | result |",
        "| --- | --- | --- | --- |",
    ]
    for r in bar(result):
        value = "n/a (no events)" if r["value"] is None else _pct(r["value"])
        verdict = "unverified" if r.get("note") else ("PASS" if r["pass"] else "FAIL")
        lines.append(f"| {r['test']} | {value} | {_pct(r['need'])} | {verdict} |")
    return "\n".join(lines) + "\n"
