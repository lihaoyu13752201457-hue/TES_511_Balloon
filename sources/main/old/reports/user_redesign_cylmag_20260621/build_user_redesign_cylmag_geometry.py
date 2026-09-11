#!/usr/bin/env python3
"""Build the user-requested cylindrical magnetic/cryostat redesign geometry.

This is a geometry-redesign candidate, not a prompt-511 minimal-addition
candidate. It intentionally modifies and removes existing baseline volumes in a
new output directory only.
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/user_redesign_cylmag_20260621"
BASE_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUT_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_20260621_megalib_proxy"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
GEO = OUT_DIR / f"{STEM}.geo"
DET = OUT_DIR / f"{STEM}.det"
SETUP = OUT_DIR / f"{STEM}.geo.setup"
MATERIALS = OUT_DIR / "Materials_DEMO2_DR_v3p5.geo"
MANIFEST = WORK / "user_cylmag_redesign_manifest.json"
MASS_CSV = WORK / "user_cylmag_redesign_mass_delta.csv"
SCHEMATIC_PNG = WORK / "user_cylmag_redesign_xz_schematic.png"
SCHEMATIC_SVG = WORK / "user_cylmag_redesign_xz_schematic.svg"
WRL = WORK / "user_cylmag_redesign.wrl"
SUMMARY_MD = WORK / "USER_CYLMAG_REDESIGN_SUMMARY.md"
OVERLAP_SOURCE = OUT_DIR / "overlap_check.source"


DENSITY = {
    "Aluminium": 2.70,
    "Copper": 8.96,
    "W": 19.30,
    "Nb": 8.57,
    "MuMetal": 8.70,
}


REMOVED_PREFIXES = (
    "ActiveShield_Al_Backplane_detector_bay_",
    "Passive_Cu_Liner_detector_bay_",
    "Passive_W_Liner_detector_bay_",
    "Nb_SideEntry_Sample_Can_with_side_aperture_",
    "Cryoperm_Horizontal_Sleeve_1p2mm_",
    "Al_50mK_Local_Can_side_entry_",
)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def volume_blocks(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^Volume\s+(\S+)\s*$", text))
    blocks: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        prefix_start = text.rfind("\n// Volume ", 0, start)
        if prefix_start != -1 and prefix_start >= text.rfind("\n\n", 0, start):
            start = prefix_start + 1
        blocks[match.group(1)] = text[start:end]
    return blocks


def remove_blocks(text: str, names: set[str]) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        maybe_comment = re.match(r"^// Volume\s+(\S+)", line)
        if maybe_comment and i + 1 < len(lines):
            maybe_volume = re.match(r"^Volume\s+(\S+)\s*$", lines[i + 1])
            if maybe_volume and maybe_volume.group(1) in names:
                i += 2
                while i < len(lines) and not re.match(r"^(// Volume\s+|Volume\s+)", lines[i]):
                    i += 1
                continue

        maybe_volume = re.match(r"^Volume\s+(\S+)\s*$", line)
        if maybe_volume and maybe_volume.group(1) in names:
            i += 1
            while i < len(lines) and not re.match(r"^(// Volume\s+|Volume\s+)", lines[i]):
                i += 1
            continue

        out.append(line)
        i += 1
    return "".join(out)


def replace_shape(text: str, name: str, shape: str, position: str | None = None) -> str:
    text, count = re.subn(
        rf"(?m)^({re.escape(name)}\.Shape)\s+.+$",
        rf"\1 {shape}",
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"shape line not found for {name}")
    if position is not None:
        text, pcount = re.subn(
            rf"(?m)^({re.escape(name)}\.Position)\s+.+$",
            rf"\1 {position}",
            text,
            count=1,
        )
        if pcount != 1:
            raise RuntimeError(f"position line not found for {name}")
    return text


def pcon(phi0: float, dphi: float, z0: float, rin: float, rout: float, z1: float) -> str:
    return f"PCON {phi0:g} {dphi:g} 2 {z0:g} {rin:g} {rout:g} {z1:g} {rin:g} {rout:g}"


def x_tube_volume(name: str, material: str, rin: float, rout: float, x0: float, x1: float) -> str:
    return "\n".join(
        [
            f"// User cylindrical redesign: {name}; material={material}",
            f"Volume {name}",
            f"{name}.Material {material}",
            f"{name}.Visibility 1",
            f"{name}.Shape {pcon(0, 360, x0, rin, rout, x1)}",
            f"{name}.Position 0 0 -5.2",
            f"{name}.Rotation 0 90 0",
            f"{name}.Mother InstrumentFrame",
            "",
        ]
    )


def scintillator_block(volume: str) -> str:
    name = f"{volume}_SD"
    return "\n".join(
        [
            f"Scintillator {name}",
            f"{name}.SensitiveVolume {volume}",
            f"{name}.DetectorVolume {volume}",
            f"{name}.TriggerThreshold 0.001",
            f"{name}.EnergyResolution Gauss 0.001 0.001 1",
            f"{name}.EnergyResolution Gauss 3000 3000 1",
            "",
        ]
    )


def append_mumetal_material() -> None:
    text = MATERIALS.read_text(encoding="utf-8")
    if re.search(r"(?m)^Material\s+MuMetal\s*$", text):
        return
    insert = "\n".join(
        [
            "",
            "Material MuMetal",
            "MuMetal.Density 8.7",
            "MuMetal.Component Ni 4",
            "MuMetal.Component Fe 1",
            "",
        ]
    )
    marker = "Material Cryoperm\n"
    idx = text.find(marker)
    if idx == -1:
        text += insert
    else:
        text = text[:idx] + insert + text[idx:]
    MATERIALS.write_text(text, encoding="utf-8")


def remove_inherited_validation_artifacts() -> None:
    for name in ("cosima_overlap.log", "cosima_overlap_user_redesign_20260621.log", "geometry_proxy_validation.json"):
        path = OUT_DIR / name
        if path.exists():
            path.unlink()


def write_overlap_source() -> None:
    OVERLAP_SOURCE.write_text(
        "\n".join(
            [
                "Version                     1",
                f"Geometry                    {SETUP}",
                "CheckForOverlaps            10000 0.0001",
                "PhysicsListEM               LivermorePol",
                "Run Minimum",
                "Minimum.FileName            /tmp/DelMe_user_cylmag_redesign_overlap",
                "Minimum.NEvents             1",
                "Minimum.Source MinimumS",
                "MinimumS.ParticleType       1",
                "MinimumS.Beam               PointSource 0 0 0",
                "MinimumS.Spectrum           Mono 511",
                "MinimumS.Flux               1.0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def modify_geo() -> dict[str, object]:
    text = GEO.read_text(encoding="utf-8")
    blocks = volume_blocks(text)
    removed = {
        name
        for name in blocks
        if any(name.startswith(prefix) for prefix in REMOVED_PREFIXES)
    }
    text = remove_blocks(text, removed)
    remaining_removed_prefix_hits = [
        name
        for name in volume_blocks(text)
        if any(name.startswith(prefix) for prefix in REMOVED_PREFIXES)
    ]
    if remaining_removed_prefix_hits:
        raise RuntimeError(
            "failed to remove requested baseline volumes: "
            + ", ".join(sorted(remaining_removed_prefix_hits)[:20])
        )

    # Outer room-temperature mechanical shell: keep inner radius/joins, thicken outward.
    text = replace_shape(
        text,
        "Outer_Al_Mechanical_Shell_detector_bay_bottom_cap",
        pcon(0, 360, -0.4, 0, 19.1, 0.4),
        "0 0 -21.1",
    )
    for name in (
        "Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port",
        "Outer_Al_Mechanical_Shell_detector_bay_side_wall_above_side_port",
        "Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_00",
        "Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_01",
    ):
        old_line = re.search(rf"(?m)^{re.escape(name)}\.Shape\s+PCON\s+(.+)$", text)
        if old_line is None:
            raise RuntimeError(f"missing outer shell shape: {name}")
        vals = old_line.group(1).split()
        vals[-1] = "19.1"
        vals[-4] = "19.1"
        text = replace_shape(text, name, "PCON " + " ".join(vals))
    text = replace_shape(
        text,
        "Outer_Al_Mechanical_Shell_detector_bay_top_annulus",
        pcon(0, 360, -0.4, 13.7, 19.1, 0.4),
        "0 0 5.6",
    )

    # Existing nested z-axis cryostat shells, thickened by preserving inner radii.
    shell_updates = [
        ("Vacuum_Jacket_Al_266mmClass_side_port", 12.9, 13.4, 0.25, {"bottom_cap": "0 0 -13.85"}),
        ("Shield_60K_Al_side_window", 11.4, 11.7, 0.15, {"bottom_cap": "0 0 -12.55"}),
        ("Shield_4K_Al_side_window", 9.9, 10.2, 0.15, {"bottom_cap": "0 0 -11.55"}),
        ("Still_Shield_Al_side_window", 8.5, 8.8, 0.15, {"bottom_cap": "0 0 -10.55"}),
    ]
    for prefix, rin, rout, cap_half, cap_positions in shell_updates:
        for name in list(volume_blocks(text)):
            if not name.startswith(prefix):
                continue
            old_line = re.search(rf"(?m)^{re.escape(name)}\.Shape\s+PCON\s+(.+)$", text)
            if old_line is None:
                continue
            vals = [float(v) for v in old_line.group(1).split()]
            n = int(vals[2])
            rest = vals[3:]
            if name.endswith("bottom_cap") and cap_half is not None:
                # Bottom caps are disks; thicken in z and extend to the new outer radius.
                vals[3] = -cap_half
                vals[4] = 0.0
                vals[6] = cap_half
                vals[7] = 0.0
                vals[5] = rout
                vals[8] = rout
                pos = cap_positions.get("bottom_cap") if cap_positions else None
                text = replace_shape(text, name, "PCON " + " ".join(f"{v:g}" for v in vals), pos)
                continue
            for j in range(n):
                rest[3 * j + 1] = rin
                rest[3 * j + 2] = rout
            vals[3:] = rest
            text = replace_shape(text, name, "PCON " + " ".join(f"{v:g}" for v in vals))

    new_block = "\n".join(
        [
            "// User redesign replaces the BRIK panel proxies with open x-axis cylindrical sleeves.",
            x_tube_volume("Nb_MagShield_Inner_Cylinder_2mm", "Nb", 4.00, 4.20, -5.8, 5.5),
            x_tube_volume("MuMetal_MagShield_Outer_Cylinder_2mm", "MuMetal", 4.25, 4.45, -6.1, 5.5),
            x_tube_volume("Cu_50mK_Local_Can_Cylinder_2mm", "Copper", 4.50, 4.70, -6.6, 5.5),
            "// End caps/feedthroughs are represented as open ends in this MEGAlib proxy.",
            "// The +x side stops before the existing Cu_ColdFinger_* vertical stems and remains open for feedthrough clearance.",
            "",
        ]
    )
    marker = "// Volume ColdPlate_MXC_50mK_SD_anchor; material=Copper"
    if marker not in text:
        raise RuntimeError("cold plate insertion marker not found")
    text = text.replace(marker, new_block + marker, 1)
    GEO.write_text(text, encoding="utf-8")

    return {
        "removed_volumes": sorted(removed),
        "added_volumes": [
            "Nb_MagShield_Inner_Cylinder_2mm",
            "MuMetal_MagShield_Outer_Cylinder_2mm",
            "Cu_50mK_Local_Can_Cylinder_2mm",
        ],
    }


def modify_det(removed_volumes: set[str], added_volumes: list[str]) -> dict[str, object]:
    text = DET.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(?ms)^Scintillator\s+\S+\n.*?(?=\n\n(?:Scintillator|MDCalorimeter)\s+|\n// Native|\Z)"
    )
    removed_blocks: list[str] = []

    def repl(match: re.Match[str]) -> str:
        block = match.group(0)
        for volume in removed_volumes:
            if f".SensitiveVolume {volume}" in block:
                removed_blocks.append(volume)
                return ""
        return block

    text = pattern.sub(repl, text)
    missing_removed_refs = [
        volume
        for volume in removed_volumes
        if re.search(rf"(?m)\.SensitiveVolume\s+{re.escape(volume)}\s*$", text)
    ]
    if missing_removed_refs:
        raise RuntimeError(
            "failed to remove detector blocks for deleted volumes: "
            + ", ".join(sorted(missing_removed_refs)[:20])
        )

    new_blocks = "\n".join(scintillator_block(volume) for volume in added_volumes)
    marker = "// Native MEGAlib Trigger/Veto blocks intentionally absent in this proxy scaffold."
    if marker not in text:
        text = text.rstrip() + "\n\n" + new_blocks
    else:
        text = text.replace(marker, new_blocks + "\n" + marker, 1)
    DET.write_text(text, encoding="utf-8")
    return {
        "removed_detector_blocks": sorted(set(removed_blocks)),
        "added_detector_blocks": added_volumes,
    }


def cylindrical_shell_volume(rin: float, rout: float, length: float, phi_fraction: float = 1.0) -> float:
    return math.pi * (rout * rout - rin * rin) * length * phi_fraction


def write_mass_delta() -> list[dict[str, object]]:
    rows = [
        {
            "component": "Outer_Al_Mechanical_Shell_detector_bay",
            "material": "Aluminium",
            "change": "thickened 0.30 -> 0.80 cm radial side wall; caps adjusted",
            "baseline_mass_kg": 3.7150947907323237,
            "candidate_mass_kg_est": 3.7150947907323237 * (0.8 / 0.3),
        },
        {
            "component": "ActiveShield_Al_Backplane_detector_bay",
            "material": "Aluminium",
            "change": "removed",
            "baseline_mass_kg": 0.5097183814966909,
            "candidate_mass_kg_est": 0.0,
        },
        {
            "component": "Passive_Cu_Liner_detector_bay",
            "material": "Copper",
            "change": "removed",
            "baseline_mass_kg": 0.9820598126804904,
            "candidate_mass_kg_est": 0.0,
        },
        {
            "component": "Passive_W_Liner_detector_bay",
            "material": "W",
            "change": "removed",
            "baseline_mass_kg": 1.8681419579178224,
            "candidate_mass_kg_est": 0.0,
        },
        {
            "component": "Vacuum_Jacket_Al_266mmClass_side_port",
            "material": "Aluminium",
            "change": "side wall 0.40 -> 0.50 cm",
            "baseline_mass_kg": 5.292726280663645,
            "candidate_mass_kg_est": 5.292726280663645 * (0.5 / 0.4),
        },
        {
            "component": "Shield_60K_Al_side_window",
            "material": "Aluminium",
            "change": "side wall 0.15 -> 0.30 cm",
            "baseline_mass_kg": 1.3684070740690064,
            "candidate_mass_kg_est": 1.3684070740690064 * (0.3 / 0.15),
        },
        {
            "component": "Shield_4K_Al_side_window",
            "material": "Aluminium",
            "change": "side wall 0.12 -> 0.30 cm",
            "baseline_mass_kg": 0.732781568290092,
            "candidate_mass_kg_est": 0.732781568290092 * (0.3 / 0.12),
        },
        {
            "component": "Still_Shield_Al_side_window",
            "material": "Aluminium",
            "change": "side wall 0.10 -> 0.30 cm",
            "baseline_mass_kg": 0.36878496426033225,
            "candidate_mass_kg_est": 0.36878496426033225 * (0.3 / 0.10),
        },
        {
            "component": "Nb_SideEntry_Sample_Can_with_side_aperture",
            "material": "Nb",
            "change": "BRIK panel proxy replaced by 2 mm x-axis open cylinder",
            "baseline_mass_kg": 0.16908262541027136,
            "candidate_mass_kg_est": cylindrical_shell_volume(4.0, 4.2, 11.3) * DENSITY["Nb"] / 1000,
        },
        {
            "component": "Cryoperm/MuMetal magnetic shield",
            "material": "MuMetal",
            "change": "1.2 mm BRIK Cryoperm proxy replaced by 2 mm x-axis MuMetal open cylinder",
            "baseline_mass_kg": 0.469025473854738,
            "candidate_mass_kg_est": cylindrical_shell_volume(4.25, 4.45, 11.6) * DENSITY["MuMetal"] / 1000,
        },
        {
            "component": "Al_50mK_Local_Can_side_entry / Cu_50mK_Local_Can_Cylinder_2mm",
            "material": "Copper",
            "change": "0.8 mm Al BRIK panel proxy replaced by 2 mm Cu x-axis open cylinder",
            "baseline_mass_kg": 0.10968516629684871,
            "candidate_mass_kg_est": cylindrical_shell_volume(4.5, 4.7, 12.1) * DENSITY["Copper"] / 1000,
        },
    ]
    for row in rows:
        row["delta_kg_est"] = row["candidate_mass_kg_est"] - row["baseline_mass_kg"]
    MASS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MASS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_wrl() -> None:
    def cyl(name: str, radius: float, length: float, x: float, z: float, color: tuple[float, float, float], alpha: float) -> str:
        r, g, b = color
        return f"""
Transform {{
  translation {x:.3f} 0 {z:.3f}
  rotation 0 0 1 1.570796
  children [
    Shape {{
      appearance Appearance {{ material Material {{ diffuseColor {r:g} {g:g} {b:g} transparency {alpha:g} }} }}
      geometry Cylinder {{ radius {radius:.3f} height {length:.3f} }}
    }}
  ]
}}
"""

    lines = [
        "#VRML V2.0 utf8",
        'WorldInfo { title "DEMO2 user cylindrical magnetic redesign" }',
        'Viewpoint { position 34 -58 32 orientation 0.76 0.26 0.59 1.08 description "overview" }',
        cyl("Outer Al", 19.1, 25.9, 0, -7.8, (0.55, 0.62, 0.70), 0.75),
        cyl("CsI", 18.0, 16.2, 0, -6.1, (0.05, 0.62, 0.18), 0.65),
        cyl("Vacuum jacket", 13.4, 51.6, 0, 11.7, (0.45, 0.55, 0.90), 0.80),
        cyl("60K", 11.7, 41.1, 0, 8.15, (0.95, 0.80, 0.25), 0.82),
        cyl("4K", 10.2, 31.1, 0, 4.15, (0.30, 0.55, 0.95), 0.84),
        cyl("Still", 8.8, 21.1, 0, 0.15, (0.80, 0.45, 0.85), 0.86),
        cyl("MuMetal", 4.45, 11.6, -0.3, -5.2, (0.55, 0.30, 0.75), 0.45),
        cyl("Nb", 4.2, 11.3, -0.15, -5.2, (0.25, 0.45, 0.95), 0.45),
        cyl("Cu50mK", 4.7, 12.1, -0.55, -5.2, (0.90, 0.45, 0.20), 0.55),
    ]
    WRL.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_schematic() -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_title("User cylindrical magnetic redesign, x-z schematic (not CAD)")
    ax.set_xlabel("x / side-entry axis (cm)")
    ax.set_ylabel("z (cm)")
    ax.axhline(-5.2, color="black", lw=0.8, ls="--")
    ax.arrow(-24, -5.2, 8, 0, head_width=0.5, head_length=1.0, color="black", length_includes_head=True)
    ax.text(-24, -4.4, "511 side-entry", fontsize=9)
    rows = [
        ("Outer Al shell 0.8 cm", -19.1, 19.1, -20.7, 6.0, "#9aa8b8"),
        ("CsI active shield", -18.0, 18.0, -14.2, 2.0, "#36a852"),
        ("Vacuum jacket Al 0.5 cm", -13.4, 13.4, -13.6, 37.5, "#85a8ff"),
        ("60K Al 0.3 cm", -11.7, 11.7, -12.4, 28.65, "#e0c34f"),
        ("4K Al 0.3 cm", -10.2, 10.2, -11.4, 19.7, "#6ba5ff"),
        ("Still Al 0.3 cm", -8.8, 8.8, -10.4, 10.7, "#ce80d8"),
        ("Cu 50mK tube 2 mm", -6.6, 5.5, -9.9, -0.5, "#cc6f2d"),
        ("MuMetal 2 mm", -6.1, 5.5, -9.65, -0.75, "#7b5aad"),
        ("Nb 2 mm", -5.8, 5.5, -9.45, -0.95, "#4d79d8"),
    ]
    for label, x0, x1, z0, z1, color in rows:
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, facecolor=color, alpha=0.18, edgecolor=color, lw=1.6))
        ax.text(x1 + 0.35, (z0 + z1) / 2, label, va="center", fontsize=8)
    ax.add_patch(Rectangle((-3.2, -7.2), 6.4, 4.0, facecolor="#111111", alpha=0.45, edgecolor="black"))
    ax.text(3.6, -5.2, "TES stack", va="center", fontsize=8)
    ax.set_xlim(-25, 25)
    ax.set_ylim(-23, 40)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(SCHEMATIC_PNG, dpi=180)
    fig.savefig(SCHEMATIC_SVG)
    plt.close(fig)


def write_summary(payload: dict[str, object], rows: list[dict[str, object]]) -> None:
    total_delta = sum(float(row["delta_kg_est"]) for row in rows)
    removed = payload["geometry"]["removed_volumes"]
    added = payload["geometry"]["added_volumes"]
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# User Cylindrical Magnetic/Cryostat Redesign",
                "",
                "Status: `GEOMETRY_BUILT_NOT_MC_VALIDATED`",
                "",
                "This candidate implements the user's geometry-redesign request in a new directory only.",
                "It intentionally modifies/removes baseline structures, so it is not a prompt-511 minimal-addition candidate.",
                "",
                "## Artifacts",
                "",
                f"- Geometry directory: `{payload['geometry_dir']}`",
                f"- Geometry setup: `{payload['setup']}`",
                f"- Detector map: `{payload['det']}`",
                f"- WRL: `{rel(WRL)}`",
                f"- 2D schematic PNG: `{rel(SCHEMATIC_PNG)}`",
                f"- 2D schematic SVG: `{rel(SCHEMATIC_SVG)}`",
                f"- Mass delta CSV: `{rel(MASS_CSV)}`",
                f"- Candidate overlap source: `{rel(OVERLAP_SOURCE)}`",
                "",
                "## Implemented Changes",
                "",
                "- Outer Al detector-bay mechanical shell thickened from 0.30 cm to 0.80 cm, preserving the inner radius and expanding outward.",
                "- `ActiveShield_Al_Backplane_detector_bay_*` volumes removed.",
                "- `Passive_Cu_Liner_detector_bay_*` and `Passive_W_Liner_detector_bay_*` side liner volumes removed.",
                "- Vacuum/60K/4K/Still side walls thickened to 0.50/0.30/0.30/0.30 cm.",
                "- BRIK-panel Nb/Cryoperm/50mK-can proxies replaced by open x-axis cylindrical sleeves:",
                "  - Nb inner magnetic sleeve: r=4.00-4.20 cm, x=-5.8..5.5 cm.",
                "  - MuMetal outer high-mu sleeve: r=4.25-4.45 cm, x=-6.1..5.5 cm.",
                "  - Cu 50mK local can: r=4.50-4.70 cm, x=-6.6..5.5 cm.",
                "- The new x-axis sleeves are open at both ends in this MEGAlib proxy; the +x end stops before the vertical Cu cold-finger stems for feedthrough clearance.",
                "- `.det` blocks referencing deleted volumes were removed, and detector proxy blocks were added for the new Nb/MuMetal/Cu sleeves.",
                "",
                "## Known Contract Boundary",
                "",
                "This redesign violates the prompt-511 refix minimal-change contract because it removes and replaces baseline volumes, including Cryoperm geometry.",
                "That is expected for this user-requested redesign; the original baseline directory is untouched.",
                "",
                "## Mass Estimate",
                "",
                f"Estimated mass delta over listed modified components: `{total_delta:+.3f} kg`.",
                "This is a component-level estimate, not a full regenerated bounds authority.",
                "",
                "| component | material | baseline kg | candidate kg est. | delta kg |",
                "|---|---:|---:|---:|---:|",
                *[
                    f"| {row['component']} | {row['material']} | {float(row['baseline_mass_kg']):.4g} | {float(row['candidate_mass_kg_est']):.4g} | {float(row['delta_kg_est']):+.4g} |"
                    for row in rows
                ],
                "",
                "## Review Checklist",
                "",
                "- Original baseline directory was not edited.",
                "- TES and Cu_ColdFinger volumes were not removed or rewritten.",
                "- This build deliberately replaces Cryoperm panel proxies with a MuMetal cylindrical proxy, per user request.",
                "- No prompt, delayed, neutron, or signal MC closure has been run.",
                "",
                f"Removed volume count: `{len(removed)}`. Added volume count: `{len(added)}`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_readme(payload: dict[str, object]) -> None:
    text = (
        "\n".join(
            [
                "# DEMO2 DR v3p5 User Cylindrical Magnetic Redesign",
                "",
                "This directory is a derived geometry candidate built from the baseline",
                "`DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy` directory.",
                "",
                "It implements a user-requested redesign of the mechanical shell, cryostat",
                "shell thicknesses, 50mK can, and magnetic shielding proxy. It is not a",
                "minimal prompt-511 refix candidate.",
                "",
                f"- Manifest: `{rel(MANIFEST)}`",
                f"- Summary: `{rel(SUMMARY_MD)}`",
                f"- WRL: `{rel(WRL)}`",
                f"- 2D schematic: `{rel(SCHEMATIC_PNG)}`",
                f"- Candidate overlap source: `{rel(OVERLAP_SOURCE)}`",
                "",
                "The original baseline geometry directory is unchanged.",
            ]
        )
        + "\n"
    )
    (OUT_DIR / "README.md").write_text(text, encoding="utf-8")
    (OUT_DIR / "README_USER_CYLMAG_REDESIGN.md").write_text(text, encoding="utf-8")


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    shutil.copytree(BASE_DIR, OUT_DIR)

    remove_inherited_validation_artifacts()
    append_mumetal_material()
    geometry_payload = modify_geo()
    det_payload = modify_det(set(geometry_payload["removed_volumes"]), geometry_payload["added_volumes"])
    rows = write_mass_delta()
    write_wrl()
    write_schematic()
    write_overlap_source()

    payload = {
        "status": "GEOMETRY_BUILT_NOT_MC_VALIDATED",
        "baseline_dir": rel(BASE_DIR),
        "geometry_dir": rel(OUT_DIR),
        "setup": rel(SETUP),
        "geo": rel(GEO),
        "det": rel(DET),
        "materials": rel(MATERIALS),
        "geometry": geometry_payload,
        "detector_map": det_payload,
        "artifacts": {
            "wrl": rel(WRL),
            "schematic_png": rel(SCHEMATIC_PNG),
            "schematic_svg": rel(SCHEMATIC_SVG),
            "mass_delta_csv": rel(MASS_CSV),
            "summary_md": rel(SUMMARY_MD),
            "overlap_source": rel(OVERLAP_SOURCE),
        },
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_summary(payload, rows)
    write_readme(payload)
    print(json.dumps({"status": payload["status"], "geometry_dir": payload["geometry_dir"], "summary": rel(SUMMARY_MD)}, indent=2))


if __name__ == "__main__":
    main()
