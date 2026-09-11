#!/usr/bin/env python3
"""Reuse the canonical dashboard with a PARMA511-specific title."""

from __future__ import annotations

import sys
from pathlib import Path


EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
sys.path.insert(0, str(EXECUTOR))

import progress  # noqa: E402


_canonical_render = progress.render


def render(config, plan, snap):
    text = _canonical_render(config, plan, snap)
    old = f"{config['candidate']} corrected-keV background transport"
    return text.replace(old, config.get("display_title", old), 1)


progress.render = render
raise SystemExit(progress.main())
