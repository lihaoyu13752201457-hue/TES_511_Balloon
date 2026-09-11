#!/usr/bin/env python3
"""Build an inner active-CsI shroud prompt-511 geometry candidate.

This candidate tests an old-like active material column in the clean vacuum
gap between the 60 K shield and the vacuum jacket. It keeps the side signal
port open and is only a design smoke, not an authority CAD model.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_inner_csi_shroud_20260620"
SRC_GEOM = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SRC_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUT_GEOM = WORK / "geometry_inner_csi_shroud"
OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_inner_csi_shroud_r11p6_12p8"
SRC_SETUP = SRC_GEOM / f"{SRC_NAME}.geo.setup"
OUT_SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
SOURCE_IN = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT = WORK / "source_cards_inner_csi_shroud"
MANIFEST = WORK / "prompt511_inner_csi_shroud_manifest.json"
README = WORK / "README_inner_csi_shroud.md"

R_IN_CM = 11.60
R_OUT_CM = 12.80
Z_MIN_CM = -13.0
Z_MAX_CM = 13.35
PORT_PHI_DEG = (171.0, 189.0)
PORT_Z_CM = (-7.2, -3.2)
CSI_DENSITY_G_CM3 = 4.51


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
        raise FileNotFoundError(f"inner-CsI-shroud inputs are missing:\n{joined}")


def replace_geometry_names(text: str) -> str:
    return text.replace(SRC_NAME, OUT_NAME)


def pcon_volume(name: str, phi0: float, dphi: float, z0: float, z1: float) -> list[str]:
    return [
        f"// Volume {name}; material=CsI",
        f"Volume {name}",
        f"{name}.Material CsI",
        f"{name}.Visibility 1",
        (
            f"{name}.Shape PCON {fmt(phi0)} {fmt(dphi)} 2 "
            f"{fmt(z0)} {fmt(R_IN_CM)} {fmt(R_OUT_CM)} "
            f"{fmt(z1)} {fmt(R_IN_CM)} {fmt(R_OUT_CM)}"
        ),
        f"{name}.Position 0 0 0",
        f"{name}.Mother InstrumentFrame",
        "",
    ]


def shroud_geo_block() -> str:
    lines = [
        "",
        "// Prompt-511 inner active-CsI shroud candidate (2026-06-20).",
        "// Active material in the 60 K shield / vacuum-jacket gap, with the true side signal port open.",
        "// This tests old-like active side-column closure without adding a large W-only shadow.",
    ]
    lines.extend(
        pcon_volume(
            "CsI_InnerShroud_Prompt511_NonPortArc",
            PORT_PHI_DEG[1],
            360.0 - (PORT_PHI_DEG[1] - PORT_PHI_DEG[0]),
            Z_MIN_CM,
            Z_MAX_CM,
        )
    )
    lines.extend(
        pcon_volume(
            "CsI_InnerShroud_Prompt511_PortBelow",
            PORT_PHI_DEG[0],
            PORT_PHI_DEG[1] - PORT_PHI_DEG[0],
            Z_MIN_CM,
            PORT_Z_CM[0],
        )
    )
    lines.extend(
        pcon_volume(
            "CsI_InnerShroud_Prompt511_PortAbove",
            PORT_PHI_DEG[0],
            PORT_PHI_DEG[1] - PORT_PHI_DEG[0],
            PORT_Z_CM[1],
            Z_MAX_CM,
        )
    )
    return "\n".join(lines)


def shroud_det_block() -> str:
    lines = [
        "",
        "// Prompt-511 inner active-CsI shroud sensitive-volume entries.",
        "// Low trigger threshold records deposits; the Step05-like proxy applies the active-veto threshold.",
    ]
    for vol in (
        "CsI_InnerShroud_Prompt511_NonPortArc",
        "CsI_InnerShroud_Prompt511_PortBelow",
        "CsI_InnerShroud_Prompt511_PortAbove",
    ):
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


def shroud_mass_kg() -> float:
    full_volume = math.pi * (R_OUT_CM * R_OUT_CM - R_IN_CM * R_IN_CM) * (Z_MAX_CM - Z_MIN_CM)
    port_gap_volume = (
        math.pi
        * (R_OUT_CM * R_OUT_CM - R_IN_CM * R_IN_CM)
        * ((PORT_PHI_DEG[1] - PORT_PHI_DEG[0]) / 360.0)
        * (PORT_Z_CM[1] - PORT_Z_CM[0])
    )
    return (full_volume - port_gap_volume) * CSI_DENSITY_G_CM3 / 1000.0


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

    setup = replace_geometry_names(OUT_SETUP.read_text(encoding="utf-8"))
    OUT_SETUP.write_text(setup, encoding="utf-8")

    geo_path = OUT_GEOM / f"{OUT_NAME}.geo"
    geo = replace_geometry_names(geo_path.read_text(encoding="utf-8"))
    geo = geo.rstrip() + shroud_geo_block() + "\n"
    geo_path.write_text(geo, encoding="utf-8")

    intro_path = OUT_GEOM / f"Intro_{OUT_NAME}.geo"
    intro_path.write_text(replace_geometry_names(intro_path.read_text(encoding="utf-8")), encoding="utf-8")

    det_path = OUT_GEOM / f"{OUT_NAME}.det"
    det = replace_geometry_names(det_path.read_text(encoding="utf-8"))
    det = det.rstrip() + shroud_det_block() + "\n"
    det_path.write_text(det, encoding="utf-8")

    return {
        "geometry_setup": rel(OUT_SETUP),
        "geometry_geo": rel(geo_path),
        "geometry_det": rel(det_path),
        "added_material": "CsI",
        "added_csi_envelope": {
            "r_cm": [R_IN_CM, R_OUT_CM],
            "z_cm": [Z_MIN_CM, Z_MAX_CM],
            "signal_port_gap": {"phi_deg": list(PORT_PHI_DEG), "z_cm": list(PORT_Z_CM)},
        },
        "estimated_added_csi_mass_kg": shroud_mass_kg(),
        "active_veto_match": "Added volume names start with CsI_ and have low-threshold Scintillator entries.",
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
        "status": "PASS_PROMPT511_INNER_CSI_SHROUD_SOURCE_CARDS",
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
    source = WORK / "overlap_inner_csi_shroud.source"
    log = WORK / "overlap_inner_csi_shroud.log"
    source.write_text(
        f"""Version                     1
Geometry                    {OUT_SETUP}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_inner_csi_shroud_overlap
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
    lines = [
        "# Prompt-511 Inner Active-CsI Shroud Candidate",
        "",
        "Status: geometry/source-card candidate for prompt mechanism testing.",
        "",
        "Purpose:",
        "",
        "- Restore an old-like active material column in the non-signal side-port solid angle.",
        "- Avoid the large W-only mass/neutron/activation risk of the upper-W-shadow diagnostic.",
        "- Keep the physical side signal port open; no ROI or focal-spot cut is introduced.",
        "",
        "Geometry change:",
        "",
        f"- base setup: `{payload['base_geometry']}`",
        f"- candidate setup: `{geometry['geometry_setup']}`",
        f"- active CsI shroud: r `{R_IN_CM:g}..{R_OUT_CM:g} cm`, z `{Z_MIN_CM:g}..{Z_MAX_CM:g} cm`.",
        f"- open signal port: phi `{PORT_PHI_DEG[0]:g}..{PORT_PHI_DEG[1]:g} deg`, z `{PORT_Z_CM[0]:g}..{PORT_Z_CM[1]:g} cm`.",
        f"- estimated added CsI mass: `{geometry['estimated_added_csi_mass_kg']:.6g} kg`.",
        "",
        "Claim boundary:",
        "",
        "- This is not an authority geometry, delayed-source result, Step06/07/08 result, or final sensitivity.",
        "- Added active CsI has native `.det` entries, but prompt suppression must be demonstrated by MC.",
        "- Activation/isotope recording is required if prompt e+/n/mu gates pass.",
    ]
    README.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload = {
        "status": "PASS_PROMPT511_INNER_CSI_SHROUD_GEOMETRY_READY",
        "claim_level": "PROMPT511_INNER_CSI_SHROUD_DESIGN_SMOKE_NO_RATE_AUTHORITY",
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
