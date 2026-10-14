"""Per-run stage cache: each stage's output folder, marked done with the fingerprint it was made from."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


class RunCache:
    def __init__(self, root: Path):
        self.root = Path(root)

    def lookup(self, stage: str, fingerprint: str) -> Path | None:
        done = self.root / stage / "done.json"
        try:
            if json.loads(done.read_text())["fingerprint"] == fingerprint:
                return done.parent
        except (OSError, ValueError, KeyError):
            pass
        return None

    def begin(self, stage: str) -> Path:
        tmp = self.root / f"{stage}.tmp"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        return tmp

    def commit(self, stage: str, fingerprint: str) -> Path:
        final = self.root / stage
        if final.exists():
            shutil.rmtree(final)
        os.replace(self.root / f"{stage}.tmp", final)
        (final / "done.json").write_text(json.dumps({"fingerprint": fingerprint}))
        return final
