"""The P0 verdict: are the event files good enough to be the truth?"""

from __future__ import annotations

import math

from spv.truth.align import attack_consistent, attack_summary, half_offset, half_spread
from spv.truth.spot import SAMPLE_SIZE, spot_score

SPREAD_LIMIT_S = 1.0  # anchors in one half must agree within this
SPOT_SHARE = 0.9  # 18 of 20
MIN_MARKS = 3  # anchors per half
MIN_TESTABLE = 2  # P0 matches that must be testable for a GO


def match_result(alignment: dict, spot: dict) -> dict:
    marks = {h: sum(1 for m in alignment["marks"] if m["half"] == h) for h in (1, 2)}
    spreads = {h: half_spread(alignment, h) for h in (1, 2)}
    summary = attack_summary(alignment)
    right, checked, total = spot_score(spot)
    reasons = []
    for h in (1, 2):
        if marks[h] < MIN_MARKS:
            reasons.append(f"half {h}: {marks[h]} anchors, need {MIN_MARKS}")
        elif spreads[h] > SPREAD_LIMIT_S:
            reasons.append(f"half {h}: anchors spread {spreads[h]} s")
    if not attack_consistent(summary):
        reasons.append("attacking direction not settled")
    need = math.ceil(SPOT_SHARE * total)
    if total == 0 or checked < total:
        reasons.append(f"spot checks: {checked} of {total} done")
    elif right < need:
        reasons.append(f"spot checks: {right} of {total} right, need {need}")
    if 0 < total < SAMPLE_SIZE and checked == total:
        reasons.append(f"spot checks: only {total} visible rows, need {SAMPLE_SIZE}")
    return {"offsets": {h: half_offset(alignment, h) for h in (1, 2)}, "spreads": spreads, "marks": marks,
            "attack": summary, "spot": (right, checked, total),
            "unseen": sum(1 for v in spot["verdicts"].values() if v["moment"] == "unseen"), "usable": not reasons, "reasons": reasons}


def _signed(value: float | None) -> str:
    return "-" if value is None else f"{value:+.2f}"


def _plain(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def p0_report(results: dict[str, dict], untestable: dict[str, str] | None = None) -> str:
    untestable = untestable or {}
    lines = ["# P0: can the event files be trusted?", "",
             "| Match | Offset h1 (s) | Spread h1 (s) | Offset h2 (s) | Spread h2 (s) | A attacks (h1/h2) "
             "| Spot checks right | Not visible (replaced) | Usable |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for match_id, r in sorted(results.items()):
        attack = "/".join(r["attack"][h]["A"] if h in r["attack"] else "-" for h in (1, 2))
        right, _, total = r["spot"]
        usable = f"not testable: {untestable[match_id]}" if match_id in untestable else "yes" if r["usable"] else "no: " + "; ".join(r["reasons"])
        lines.append(f"| {match_id} | {_signed(r['offsets'][1])} | {_plain(r['spreads'][1])} "
                     f"| {_signed(r['offsets'][2])} | {_plain(r['spreads'][2])} | {attack} | {right}/{total} | {r['unseen']} | {usable} |")
    testable = [r for m, r in results.items() if m not in untestable]
    go = len(testable) >= MIN_TESTABLE and all(r["usable"] for r in testable)
    verdict = "GO" if go else "STOP: talk it through with Thomas before P2"
    lines += ["", f"**Verdict:** {verdict}", ""]
    skipped = sorted(m for m in results if m in untestable)
    if skipped:
        lines += [f"Not testable (excluded from the verdict, decided by Thomas): {', '.join(skipped)}.", ""]
    lines += [
              f"Gate: anchors within {SPREAD_LIMIT_S:g} s per half (at least {MIN_MARKS}), attacking direction "
              f"consistent, at least {SPOT_SHARE:.0%} of spot checks right.",
              "Anchors and spot checks were judged by eye by Claude from contact sheets; the frames stay in runs/ "
              "and are never committed."]
    return "\n".join(lines) + "\n"
