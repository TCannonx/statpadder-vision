"""Pipeline stages. Later build steps insert their stages into `default_stages`."""

from __future__ import annotations

from spv.pipeline import Stage
from spv.stages.export import ExportStage
from spv.stages.probe import ProbeStage


def default_stages() -> list[Stage]:
    return [ProbeStage(), ExportStage()]
