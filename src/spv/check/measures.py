"""Measures, saved baselines and the comparison that makes `spv check` fail on a regression."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Measure:
    name: str
    value: float
    better: Literal["higher", "lower"]
    margin: float
    relative: bool = False


@dataclass(frozen=True)
class Outcome:
    name: str
    baseline: float | None
    current: float | None
    status: Literal["same", "better", "worse", "new", "missing"]


def _status(measure: Measure, baseline: float) -> str:
    allowed = measure.margin * abs(baseline) if measure.relative else measure.margin
    gain = measure.value - baseline if measure.better == "higher" else baseline - measure.value
    if gain < -allowed - 1e-12:
        return "worse"
    if gain > allowed + 1e-12:
        return "better"
    return "same"


def compare(measures: list[Measure], baseline: dict[str, float]) -> list[Outcome]:
    outcomes = [Outcome(m.name, baseline.get(m.name), m.value,
                        _status(m, baseline[m.name]) if m.name in baseline else "new")
                for m in measures]
    produced = {m.name for m in measures}
    outcomes += [Outcome(name, value, None, "missing") for name, value in baseline.items() if name not in produced]
    return outcomes


def load_baseline(path: Path) -> dict[str, float]:
    path = Path(path)
    return json.loads(path.read_text())["measures"] if path.exists() else {}


def save_baseline(path: Path, measures: list[Measure]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    values = {m.name: m.value for m in sorted(measures, key=lambda m: m.name)}
    path.write_text(json.dumps({"measures": values}, indent=1) + "\n")


def update_baseline(path: Path, measures: list[Measure]) -> list[Outcome]:
    """Write new and better values; refuse if anything is worse or missing."""
    baseline = load_baseline(path)
    outcomes = compare(measures, baseline)
    bad = [o.name for o in outcomes if o.status in ("worse", "missing")]
    if bad:
        raise ValueError(f"not updating the baseline, worse or missing: {', '.join(bad)}")
    keep = {m.name: m for m in measures if m.name in baseline}
    for o, m in zip(outcomes, measures):
        if o.status == "same":
            keep[m.name] = Measure(m.name, baseline[m.name], m.better, m.margin, m.relative)
        else:
            keep[m.name] = m
    save_baseline(path, list(keep.values()))
    return outcomes


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.4g}"


def results_table(outcomes: list[Outcome]) -> str:
    lines = ["| measure | baseline | now | status |", "| --- | --- | --- | --- |"]
    lines += [f"| {o.name} | {_fmt(o.baseline)} | {_fmt(o.current)} | {o.status} |"
              for o in sorted(outcomes, key=lambda o: o.name)]
    return "\n".join(lines) + "\n"
