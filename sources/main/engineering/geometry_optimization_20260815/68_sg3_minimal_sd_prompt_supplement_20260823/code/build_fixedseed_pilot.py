#!/usr/bin/env python3
"""Build the non-overwriting CLI-fixed-seed paired pilot sources."""

from __future__ import annotations

import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
OLD_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/m05new_minimal_sd_alpha_pilot_20260823_v1"
)
NEW_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/"
    "m05new_minimal_sd_alpha_fixedseed_pilot_20260823_v1"
)
SEED = 707_270_754
EVENTS = 100


def main() -> int:
    source_root = PACKAGE / "pilot_sources_fixedseed"
    manifest_path = PACKAGE / "FIXEDSEED_PILOT_MANIFEST.json"
    if source_root.exists() or manifest_path.exists() or NEW_ROOT.exists():
        raise FileExistsError("non-overwrite fixed-seed pilot gate")
    source_root.mkdir()
    jobs = []
    for storage in ("all", "init-only"):
        compact = storage.replace("-", "")
        old_job = f"m05z_sg3_minimal_alpha_{compact}_{EVENTS}"
        new_job = f"m05z_sg3_minimal_fixedseed_alpha_{compact}_{EVENTS}"
        old_source = PACKAGE / "pilot_sources" / f"{old_job}.source"
        text = old_source.read_text(encoding="utf-8")
        text = text.replace(old_job, new_job).replace(str(OLD_ROOT), str(NEW_ROOT))
        new_source = source_root / f"{new_job}.source"
        new_source.write_text(text, encoding="utf-8")
        jobs.append(
            {
                "job_id": new_job,
                "source": str(new_source),
                "store_simulation_info": storage,
                "output_root": str(NEW_ROOT / new_job),
            }
        )
    base = json.loads((PACKAGE / "PILOT_MANIFEST.json").read_text())
    manifest = {
        **base,
        "status": "PREPARED__CLI_FIXED_SEED_PAIRED_PILOT_NOT_YET_RUN",
        "seed": SEED,
        "events": EVENTS,
        "jobs": jobs,
        "seed_policy": "COSIMA_COMMAND_LINE_-s_OVERRIDES_SOURCE_AND_IS_REQUIRED",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
