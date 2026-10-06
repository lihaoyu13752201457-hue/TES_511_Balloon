#!/usr/bin/env python3
"""Build a non-overwriting SG3 minimal-SD paired alpha pilot.

The physical .geo is copied byte-for-byte from the retained SG3B geometry.
Only the detector map and the simulation-information storage policy differ.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ORIGINAL_GEOMETRY = Path(
    "/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/"
    "geometry"
)
BASE_SOURCE = Path(
    "/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260815/"
    "67_m05new_zero_prompt_statistics_20260823/bundles/sg3/alpha/generated/sources/"
    "m05z_sg3_instant_alpha_shard0001.source"
)
BASELINE_SIM = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/m05new_zero_prompt_supplement_20260823_v1/"
    "alpha/run/jobs/m05z_sg3_instant_alpha_shard0001/attempts/attempt02/"
    "m05z_sg3_instant_alpha_shard0001.inc1.id1.sim.gz"
)
PILOT_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/"
    "m05new_minimal_sd_alpha_pilot_20260823_v1"
)
PILOT_EVENTS = 100
PILOT_SEED = 707_270_754

DETECTORS = (
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm_SD",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm_SD",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm_SD",
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_SD",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm_SD",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm_SD",
)


def first_definition(block: str) -> str | None:
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        match = re.match(r"^(?:MDCalorimeter|Scintillator)\s+(\S+)$", stripped)
        return match.group(1) if match else None
    return None


def patch_source(base: str, *, job_id: str, setup: Path, store: str) -> str:
    old_job = "m05z_sg3_instant_alpha_shard0001"
    output_prefix = PILOT_ROOT / job_id / "active" / job_id
    text = base.replace(old_job, job_id)
    text = re.sub(r"(?m)^Geometry\s+\S+\s*$", f"Geometry {setup}", text, count=1)
    text = re.sub(
        r"(?m)^StoreSimulationInfo\s+\S+\s*$",
        f"StoreSimulationInfo {store}",
        text,
        count=1,
    )
    text = re.sub(
        rf"(?m)^{re.escape(job_id)}\.Events\s+\d+\s*$",
        f"{job_id}.Events {PILOT_EVENTS}",
        text,
        count=1,
    )
    text = re.sub(
        rf"(?m)^{re.escape(job_id)}\.FileName\s+\S+\s*$",
        f"{job_id}.FileName {output_prefix}",
        text,
        count=1,
    )
    text = re.sub(
        rf"(?m)^{re.escape(job_id)}\.IsotopeProductionFile\s+\S+\s*$",
        f"{job_id}.IsotopeProductionFile {output_prefix}.dat",
        text,
        count=1,
    )
    if f"Seed {PILOT_SEED}" not in text:
        raise RuntimeError("pilot seed changed unexpectedly")
    if "cosima_spectra_dp_2602units" in text:
        raise RuntimeError("forbidden legacy spectrum token")
    return text


def main() -> int:
    if PACKAGE.exists() and any(PACKAGE.iterdir()):
        # The checked-in builder itself is expected; generated targets are not.
        unexpected = [p for p in PACKAGE.iterdir() if p.name != "code"]
        if unexpected:
            raise FileExistsError(f"non-overwrite package gate: {unexpected}")
    if PILOT_ROOT.exists():
        raise FileExistsError(f"non-overwrite pilot gate: {PILOT_ROOT}")
    if not BASE_SOURCE.is_file() or not BASELINE_SIM.is_file():
        raise FileNotFoundError("baseline source/SIM is unavailable")

    geometry = PACKAGE / "geometry"
    sources = PACKAGE / "pilot_sources"
    geometry.mkdir(parents=True, exist_ok=False)
    sources.mkdir(parents=True, exist_ok=False)

    for name in (
        "DEMO2_DR_v3p5_SG3B.geo",
        "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
        "Materials_DEMO2_DR_v3p5.geo",
    ):
        shutil.copy2(ORIGINAL_GEOMETRY / name, geometry / name)

    original_det = (ORIGINAL_GEOMETRY / "DEMO2_DR_v3p5_SG3B.det").read_text(
        encoding="utf-8"
    )
    selected: dict[str, str] = {}
    for block in re.split(r"\n\s*\n", original_det):
        name = first_definition(block)
        if name in DETECTORS:
            selected[name] = block.strip()
    missing = sorted(set(DETECTORS) - set(selected))
    if missing or len(selected) != 12:
        raise RuntimeError(f"minimal detector extraction failed; missing={missing}")
    det_text = (
        "// SG3B minimal prompt detector map: physical geometry unchanged.\n"
        "// Retains 6 TES layers, 3 plastic veto volumes, and 3 BGO veto volumes.\n\n"
        + "\n\n".join(selected[name] for name in DETECTORS)
        + "\n"
    )
    det_path = geometry / "DEMO2_DR_v3p5_SG3B_MINIMAL.det"
    det_path.write_text(det_text, encoding="utf-8")

    setup_path = geometry / "DEMO2_DR_v3p5_SG3B_MINIMAL.geo.setup"
    setup_path.write_text(
        "Name DEMO2_DR_v3p5_SG3B_MINIMAL\n"
        "Version 1\n"
        "Include DEMO2_DR_v3p5_SG3B.geo\n"
        "Include DEMO2_DR_v3p5_SG3B_MINIMAL.det\n"
        "SurroundingSphere 60 5 0 9 60\n",
        encoding="utf-8",
    )

    base = BASE_SOURCE.read_text(encoding="utf-8")
    jobs = []
    for storage in ("all", "init-only"):
        suffix = storage.replace("-", "")
        job_id = f"m05z_sg3_minimal_alpha_{suffix}_{PILOT_EVENTS}"
        source = sources / f"{job_id}.source"
        source.write_text(
            patch_source(base, job_id=job_id, setup=setup_path, store=storage),
            encoding="utf-8",
        )
        jobs.append(
            {
                "job_id": job_id,
                "source": str(source),
                "store_simulation_info": storage,
                "output_root": str(PILOT_ROOT / job_id),
            }
        )

    manifest = {
        "schema_version": 1,
        "status": "PREPARED__PAIRED_PILOT_NOT_YET_RUN",
        "physical_geometry_policy": "BYTE_IDENTICAL_GEO__MINIMAL_DETECTOR_MAP_ONLY",
        "setup": str(setup_path),
        "detectors": list(DETECTORS),
        "detector_count": len(DETECTORS),
        "seed": PILOT_SEED,
        "events": PILOT_EVENTS,
        "baseline_sim": str(BASELINE_SIM),
        "baseline_store_simulation_info": "all",
        "jobs": jobs,
    }
    (PACKAGE / "PILOT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
