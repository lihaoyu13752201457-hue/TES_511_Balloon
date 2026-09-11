#!/usr/bin/env python3
"""Build a local active-CsI collar prompt-511 geometry candidate."""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_active_csi_collar_20260620"
BASE_WORK = ROOT / "outputs/reports/prompt511_repack_smoke_20260617"
SRC_GEOM = BASE_WORK / "geometry_repack"
SRC_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_repack_r4p25_5p95"
OUT_GEOM = WORK / "geometry_active_csi_collar"
OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_csi_collar_r4p25_5p95"
SRC_SETUP = SRC_GEOM / f"{SRC_NAME}.geo.setup"
OUT_SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
SOURCE_IN = BASE_WORK / "source_cards"
SOURCE_OUT = WORK / "source_cards_active_csi_collar"
MANIFEST = WORK / "prompt511_active_csi_collar_manifest.json"
README = WORK / "README_active_csi_collar.md"

CSI_DENSITY_G_CM3 = 4.51
W_R0_CM = 4.25
W_R1_CM = 5.95
W_Z_SEGS_CM = [(-8.75, -0.65), (0.65, 4.65)]
SIGNAL_GAP_DEG = (160.0, 200.0)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def require_inputs() -> None:
    missing = [
        path
        for path in (
            SRC_GEOM,
            SRC_SETUP,
            SRC_GEOM / f"{SRC_NAME}.geo",
            SRC_GEOM / f"{SRC_NAME}.det",
            SOURCE_IN,
        )
        if not path.exists()
    ]
    if missing:
        joined = "\n".join(f"- {rel(path)}" for path in missing)
        raise FileNotFoundError(f"active-CsI collar inputs are missing:\n{joined}")


def replace_geometry_names(text: str) -> str:
    return text.replace(SRC_NAME, OUT_NAME)


def replace_liner_volumes(text: str) -> tuple[str, list[dict[str, str]]]:
    """Replace W shadow liner volumes with active CsI collar volumes."""
    rows = []
    for old in sorted(set(re.findall(r"\b(Prompt511_Repack_W_Liner_z\d+_[ab])\b", text))):
        new = old.replace("Prompt511_Repack_W_Liner", "CsI_Active_Shield_Prompt511_Collar")
        text = text.replace(old, new)
        rows.append({"old": old, "new": new})

    text = re.sub(
        r"^(CsI_Active_Shield_Prompt511_Collar_z\d+_[ab]\.Material)\s+W\s*$",
        r"\1 CsI",
        text,
        flags=re.MULTILINE,
    )
    text = text.replace(
        "// Prompt-511 repack smoke: segmented W shadow liner.",
        "// Prompt-511 active-CsI collar smoke: segmented active veto collar.",
    )
    text = text.replace(
        "// This is a local design-smoke volume, not authority CAD.",
        "// This is a local active-veto design-smoke volume, not authority CAD.",
    )
    return text, rows


def det_block(rows: list[dict[str, str]]) -> str:
    lines = ["", "// Prompt-511 active-CsI collar sensitive-volume entries."]
    for row in rows:
        vol = row["new"]
        sd = f"{vol}_SD"
        lines.extend(
            [
                f"Scintillator {sd}",
                f"{sd}.SensitiveVolume {vol}",
                f"{sd}.DetectorVolume {vol}",
                f"{sd}.TriggerThreshold 0.001",
                f"{sd}.EnergyResolution Gauss 0.001 0.001 1",
                f"{sd}.EnergyResolution Gauss 3000 3000 1",
                "",
            ]
        )
    return "\n".join(lines)


def collar_volume_cm3() -> float:
    phi_fraction = ((SIGNAL_GAP_DEG[0] - 0.05) + (360.0 - SIGNAL_GAP_DEG[1] - 0.05)) / 360.0
    dz = sum(z1 - z0 for z0, z1 in W_Z_SEGS_CM)
    return math.pi * (W_R1_CM * W_R1_CM - W_R0_CM * W_R0_CM) * dz * phi_fraction


def build_geometry() -> dict[str, object]:
    require_inputs()
    WORK.mkdir(parents=True, exist_ok=True)
    if OUT_GEOM.exists():
        shutil.rmtree(OUT_GEOM)
    shutil.copytree(SRC_GEOM, OUT_GEOM)

    for old in (
        OUT_GEOM / f"{SRC_NAME}.geo.setup",
        OUT_GEOM / f"{SRC_NAME}.geo",
        OUT_GEOM / f"{SRC_NAME}.det",
    ):
        old.rename(OUT_GEOM / old.name.replace(SRC_NAME, OUT_NAME))

    OUT_SETUP.write_text(replace_geometry_names(OUT_SETUP.read_text(encoding="utf-8")), encoding="utf-8")

    geo_path = OUT_GEOM / f"{OUT_NAME}.geo"
    geo, rows = replace_liner_volumes(replace_geometry_names(geo_path.read_text(encoding="utf-8")))
    geo_path.write_text(geo, encoding="utf-8")

    det_path = OUT_GEOM / f"{OUT_NAME}.det"
    det = replace_geometry_names(det_path.read_text(encoding="utf-8")).rstrip() + det_block(rows) + "\n"
    det_path.write_text(det, encoding="utf-8")

    volume_cm3 = collar_volume_cm3()
    return {
        "geometry_setup": rel(OUT_SETUP),
        "geometry_geo": rel(geo_path),
        "geometry_det": rel(det_path),
        "base_geometry": rel(SRC_SETUP),
        "collar_material": "CsI",
        "collar_volume_cm3": volume_cm3,
        "collar_mass_kg": volume_cm3 * CSI_DENSITY_G_CM3 / 1000.0,
        "collar_r_cm": [W_R0_CM, W_R1_CM],
        "collar_z_segments_cm": [list(seg) for seg in W_Z_SEGS_CM],
        "signal_gap_phi_deg": list(SIGNAL_GAP_DEG),
        "collar_active_veto_match": "volume names start with CsI_Active_Shield and have Scintillator entries",
        "replaced_volumes": rows,
    }


def migrate_sources() -> dict[str, object]:
    if SOURCE_OUT.exists():
        shutil.rmtree(SOURCE_OUT)
    SOURCE_OUT.mkdir(parents=True)
    rows = []
    for src in sorted(SOURCE_IN.glob("Background_*_fullsphere20.source")):
        text = re.sub(
            r"^Geometry\s+.+$",
            f"Geometry {OUT_SETUP}",
            src.read_text(encoding="utf-8"),
            count=1,
            flags=re.MULTILINE,
        )
        out = SOURCE_OUT / src.name
        out.write_text(text, encoding="utf-8")
        rows.append({"source": rel(out), "base_source": rel(src)})
    manifest = {
        "status": "PASS_PROMPT511_ACTIVE_CSI_COLLAR_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT),
        "base_source_dir": rel(SOURCE_IN),
        "geometry_setup": rel(OUT_SETUP),
        "farfield_radius_cm": 60.0,
        "sources": rows,
    }
    (SOURCE_OUT / "source_migration_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_overlap_source() -> dict[str, str]:
    source = WORK / "overlap_active_csi_collar.source"
    log = WORK / "overlap_active_csi_collar.log"
    source.write_text(
        f"""Version                     1
Geometry                    {OUT_SETUP}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_active_csi_collar_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
""",
        encoding="utf-8",
    )
    return {"overlap_source": rel(source), "overlap_log": rel(log)}


def write_readme(payload: dict[str, object]) -> None:
    geometry = payload["geometry"]
    README.write_text(
        "\n".join(
            [
                "# Prompt-511 Active-CsI Collar Candidate",
                "",
                "This is a local prompt-511 geometry candidate, not a rate authority.",
                "It reuses the prompt511 repack local collar envelope and replaces",
                "the W liner with active CsI collar volumes.",
                "",
                f"- setup: `{geometry['geometry_setup']}`",
                f"- source cards: `{payload['sources']['source_dir']}`",
                f"- collar mass: `{geometry['collar_mass_kg']:.6g} kg`",
                f"- collar r: `{geometry['collar_r_cm']}` cm",
                f"- z segments: `{geometry['collar_z_segments_cm']}` cm",
                f"- signal gap: `{geometry['signal_gap_phi_deg']}` deg",
                "",
                "Boundaries:",
                "",
                "- no ROI/source-spot restriction is used;",
                "- prompt-only L1 proxy must pass before n/mu/isotope budget;",
                "- isotope smoke, if run, is not a delayed-rate authority.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload: dict[str, object] = {
        "status": "PASS_PROMPT511_ACTIVE_CSI_COLLAR_GEOMETRY_READY",
        "claim_level": "PROMPT511_ACTIVE_CSI_COLLAR_DESIGN_SMOKE_NO_RATE_AUTHORITY",
        "geometry": geometry,
        "sources": sources,
        "overlap": overlap,
        "constraints": [
            "uses full-sphere far-field source cards, no ROI or spot source",
            "keeps the repack side signal gap phi=160..200 deg",
            "prompt and isotope smoke only; no delayed/time-axis promotion",
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_readme(payload)
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
