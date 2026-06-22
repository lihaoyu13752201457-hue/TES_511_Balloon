#!/usr/bin/env python3
"""Build a hybrid thin-W + active-CsI prompt-511 geometry candidate."""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_hybrid_w_csi_shroud_20260620"
SRC_GEOM = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SRC_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUT_GEOM = WORK / "geometry_hybrid_w_csi_shroud"
OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_hybrid_w_csi_shroud"
SRC_SETUP = SRC_GEOM / f"{SRC_NAME}.geo.setup"
OUT_SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
SOURCE_IN = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT = WORK / "source_cards_hybrid_w_csi_shroud"
MANIFEST = WORK / "prompt511_hybrid_w_csi_shroud_manifest.json"
README = WORK / "README_hybrid_w_csi_shroud.md"

W_DENSITY_G_CM3 = 19.3
CSI_DENSITY_G_CM3 = 4.51

W_R_IN_CM = 12.35
W_R_OUT_CM = 12.80
W_LOWER_Z_MIN_CM = -13.0
W_LOWER_Z_MAX_CM = 1.0
W_UPPER_Z_MIN_CM = 1.05
W_UPPER_Z_MAX_CM = 13.35
W_UPPER_PHI_START_DEG = 5.0
W_UPPER_PHI_DELTA_DEG = 350.0

CSI_R_IN_CM = 13.6
CSI_R_OUT_CM = 18.0
CSI_Z_MIN_CM = 5.55
CSI_Z_MAX_CM = 15.35
CSI_SEGMENTS = 8

PORT_PHI_DEG = (171.0, 189.0)
PORT_Z_CM = (-7.2, -3.2)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def fmt(x: float) -> str:
    return f"{x:.6g}"


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
        raise FileNotFoundError(f"hybrid inputs are missing:\n{joined}")


def replace_geometry_names(text: str) -> str:
    return text.replace(SRC_NAME, OUT_NAME)


def pcon_volume(name: str, material: str, phi0: float, dphi: float, z0: float, z1: float, r0: float, r1: float) -> list[str]:
    return [
        f"// Volume {name}; material={material}",
        f"Volume {name}",
        f"{name}.Material {material}",
        f"{name}.Visibility 1",
        (
            f"{name}.Shape PCON {fmt(phi0)} {fmt(dphi)} 2 "
            f"{fmt(z0)} {fmt(r0)} {fmt(r1)} "
            f"{fmt(z1)} {fmt(r0)} {fmt(r1)}"
        ),
        f"{name}.Position 0 0 0",
        f"{name}.Mother InstrumentFrame",
        "",
    ]


def geometry_block() -> str:
    lines = [
        "",
        "// Prompt-511 hybrid candidate (2026-06-20): thin W shadow plus active upper CsI shroud.",
        "// The true side signal-port sector is left open at phi[171,189], z[-7.2,-3.2].",
    ]
    lines.extend(
        pcon_volume(
            "HybridW_Prompt511_LowerNonPortArc",
            "W",
            PORT_PHI_DEG[1],
            360.0 - (PORT_PHI_DEG[1] - PORT_PHI_DEG[0]),
            W_LOWER_Z_MIN_CM,
            W_LOWER_Z_MAX_CM,
            W_R_IN_CM,
            W_R_OUT_CM,
        )
    )
    lines.extend(
        pcon_volume(
            "HybridW_Prompt511_PortBelow",
            "W",
            PORT_PHI_DEG[0],
            PORT_PHI_DEG[1] - PORT_PHI_DEG[0],
            W_LOWER_Z_MIN_CM,
            PORT_Z_CM[0],
            W_R_IN_CM,
            W_R_OUT_CM,
        )
    )
    lines.extend(
        pcon_volume(
            "HybridW_Prompt511_PortAbove",
            "W",
            PORT_PHI_DEG[0],
            PORT_PHI_DEG[1] - PORT_PHI_DEG[0],
            PORT_Z_CM[1],
            W_LOWER_Z_MAX_CM,
            W_R_IN_CM,
            W_R_OUT_CM,
        )
    )
    lines.extend(
        pcon_volume(
            "HybridW_Prompt511_UpperNotched",
            "W",
            W_UPPER_PHI_START_DEG,
            W_UPPER_PHI_DELTA_DEG,
            W_UPPER_Z_MIN_CM,
            W_UPPER_Z_MAX_CM,
            W_R_IN_CM,
            W_R_OUT_CM,
        )
    )
    for idx in range(CSI_SEGMENTS):
        lines.extend(
            pcon_volume(
                f"CsI_HybridUpperShroud_Prompt511_Segment_{idx:02d}",
                "CsI",
                45.0 * idx,
                45.0,
                CSI_Z_MIN_CM,
                CSI_Z_MAX_CM,
                CSI_R_IN_CM,
                CSI_R_OUT_CM,
            )
        )
    return "\n".join(lines)


def det_block() -> str:
    lines = [
        "",
        "// Prompt-511 hybrid active upper-CsI shroud sensitive-volume entries.",
    ]
    for idx in range(CSI_SEGMENTS):
        vol = f"CsI_HybridUpperShroud_Prompt511_Segment_{idx:02d}"
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


def shell_mass_kg(r0: float, r1: float, z0: float, z1: float, dphi: float, density: float) -> float:
    volume_cm3 = math.pi * (r1 * r1 - r0 * r0) * (z1 - z0) * (dphi / 360.0)
    return volume_cm3 * density / 1000.0


def mass_breakdown() -> dict[str, float]:
    w_lower = shell_mass_kg(W_R_IN_CM, W_R_OUT_CM, W_LOWER_Z_MIN_CM, W_LOWER_Z_MAX_CM, 342.0, W_DENSITY_G_CM3)
    w_port_below = shell_mass_kg(W_R_IN_CM, W_R_OUT_CM, W_LOWER_Z_MIN_CM, PORT_Z_CM[0], 18.0, W_DENSITY_G_CM3)
    w_port_above = shell_mass_kg(W_R_IN_CM, W_R_OUT_CM, PORT_Z_CM[1], W_LOWER_Z_MAX_CM, 18.0, W_DENSITY_G_CM3)
    w_upper = shell_mass_kg(W_R_IN_CM, W_R_OUT_CM, W_UPPER_Z_MIN_CM, W_UPPER_Z_MAX_CM, W_UPPER_PHI_DELTA_DEG, W_DENSITY_G_CM3)
    csi_upper = shell_mass_kg(CSI_R_IN_CM, CSI_R_OUT_CM, CSI_Z_MIN_CM, CSI_Z_MAX_CM, 360.0, CSI_DENSITY_G_CM3)
    return {
        "w_lower_nonport_arc_kg": w_lower,
        "w_port_below_kg": w_port_below,
        "w_port_above_kg": w_port_above,
        "w_upper_notched_kg": w_upper,
        "csi_upper_shroud_kg": csi_upper,
        "total_w_kg": w_lower + w_port_below + w_port_above + w_upper,
        "total_csi_kg": csi_upper,
        "total_added_kg": w_lower + w_port_below + w_port_above + w_upper + csi_upper,
    }


def build_geometry() -> dict[str, object]:
    require_inputs()
    if OUT_GEOM.exists():
        shutil.rmtree(OUT_GEOM)
    shutil.copytree(SRC_GEOM, OUT_GEOM)

    for old in (
        OUT_GEOM / f"{SRC_NAME}.geo.setup",
        OUT_GEOM / f"{SRC_NAME}.geo",
        OUT_GEOM / f"{SRC_NAME}.det",
        OUT_GEOM / f"Intro_{SRC_NAME}.geo",
    ):
        old.rename(OUT_GEOM / old.name.replace(SRC_NAME, OUT_NAME))

    OUT_SETUP.write_text(replace_geometry_names(OUT_SETUP.read_text(encoding="utf-8")), encoding="utf-8")

    geo_path = OUT_GEOM / f"{OUT_NAME}.geo"
    geo_path.write_text(replace_geometry_names(geo_path.read_text(encoding="utf-8")).rstrip() + geometry_block() + "\n", encoding="utf-8")

    intro_path = OUT_GEOM / f"Intro_{OUT_NAME}.geo"
    intro_path.write_text(replace_geometry_names(intro_path.read_text(encoding="utf-8")), encoding="utf-8")

    det_path = OUT_GEOM / f"{OUT_NAME}.det"
    det_path.write_text(replace_geometry_names(det_path.read_text(encoding="utf-8")).rstrip() + det_block() + "\n", encoding="utf-8")

    return {
        "geometry_setup": rel(OUT_SETUP),
        "geometry_geo": rel(geo_path),
        "geometry_det": rel(det_path),
        "added_materials": ["W", "CsI"],
        "w_envelope": {
            "r_cm": [W_R_IN_CM, W_R_OUT_CM],
            "lower_z_cm": [W_LOWER_Z_MIN_CM, W_LOWER_Z_MAX_CM],
            "upper_notched_z_cm": [W_UPPER_Z_MIN_CM, W_UPPER_Z_MAX_CM],
            "upper_notched_phi_deg": [W_UPPER_PHI_START_DEG, W_UPPER_PHI_START_DEG + W_UPPER_PHI_DELTA_DEG],
            "signal_port_gap": {"phi_deg": list(PORT_PHI_DEG), "z_cm": list(PORT_Z_CM)},
        },
        "csi_upper_shroud": {
            "segments": CSI_SEGMENTS,
            "r_cm": [CSI_R_IN_CM, CSI_R_OUT_CM],
            "z_cm": [CSI_Z_MIN_CM, CSI_Z_MAX_CM],
        },
        "mass_breakdown_kg": mass_breakdown(),
        "active_veto_match": "Hybrid upper CsI volumes start with CsI_ and have low-threshold Scintillator entries.",
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
        "status": "PASS_PROMPT511_HYBRID_W_CSI_SHROUD_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT),
        "base_source_dir": rel(SOURCE_IN),
        "geometry_setup": rel(OUT_SETUP),
        "farfield_radius_cm": 60.0,
        "sources": rows,
    }
    (SOURCE_OUT / "source_migration_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_overlap_source() -> dict[str, str]:
    source = WORK / "overlap_hybrid_w_csi_shroud.source"
    log = WORK / "overlap_hybrid_w_csi_shroud.log"
    source.write_text(
        f"""Version                     1
Geometry                    {OUT_SETUP}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_hybrid_w_csi_shroud_overlap
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
    assert isinstance(geometry, dict)
    mass = geometry["mass_breakdown_kg"]
    assert isinstance(mass, dict)
    lines = [
        "# Prompt-511 Hybrid Thin-W + Active-CsI Shroud Candidate",
        "",
        "Status: geometry/source-card candidate for prompt mechanism testing.",
        "",
        "Purpose:",
        "",
        "- Use a thin inner W shadow only through the upper-z leakage region that VariantB missed.",
        "- Add old-like active CsI above the current top annulus for veto/material continuity.",
        "- Keep the physical side signal port open; no ROI or focal-spot cut is introduced.",
        "",
        "Geometry change:",
        "",
        f"- base setup: `{payload['base_geometry']}`",
        f"- candidate setup: `{geometry['geometry_setup']}`",
        f"- thin W: r `{W_R_IN_CM:g}..{W_R_OUT_CM:g} cm`, z `{W_LOWER_Z_MIN_CM:g}..{W_UPPER_Z_MAX_CM:g} cm`, with true side signal gap open.",
        f"- active CsI upper shroud: r `{CSI_R_IN_CM:g}..{CSI_R_OUT_CM:g} cm`, z `{CSI_Z_MIN_CM:g}..{CSI_Z_MAX_CM:g} cm`, 8 native sensitive segments.",
        f"- estimated added W mass: `{mass['total_w_kg']:.6g} kg`; CsI mass: `{mass['total_csi_kg']:.6g} kg`; total: `{mass['total_added_kg']:.6g} kg`.",
        "",
        "Claim boundary:",
        "",
        "- This is not an authority geometry, delayed-source result, Step06/07/08 result, or final sensitivity.",
        "- Prompt-only e+ must pass before n/mu/isotope budget is spent.",
        "- Added W and CsI activation must be inspected separately if prompt gates pass.",
    ]
    README.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload = {
        "status": "PASS_PROMPT511_HYBRID_W_CSI_SHROUD_GEOMETRY_READY",
        "claim_level": "PROMPT511_HYBRID_W_CSI_SHROUD_DESIGN_SMOKE_NO_RATE_AUTHORITY",
        "base_geometry": rel(SRC_SETUP),
        "geometry": geometry,
        "sources": sources,
        "overlap": overlap,
        "required_next_gates": [
            "cosima overlap check",
            "prompt-only eplus L1 proxy without ROI or isotope store",
            "prompt-only n and muplus L1 proxy if eplus passes",
            "isotope-record buildup smoke only after prompt gate",
            "focused signal replay before promotion",
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_readme(payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
