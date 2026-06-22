#!/usr/bin/env python3
"""Build a prompt-511 old-like CsI/material-continuity geometry scaffold.

This is a report-local candidate derived from the current v3p5 geometry.  It
does not modify the authority geometry tree.  The candidate restores an
old-like active/material column inside the thin-Al side-wall leakage radius,
while leaving the current side signal port larger than the present side-window
design.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_oldlike_topology_20260620"
SRC_GEOM = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SRC_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUT_NAME = f"{SRC_NAME}_prompt511_oldlike_csi_material_topology"
OUT_GEOM = WORK / "geometry_oldlike_topology"
OUT_SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
SOURCE_IN = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT = WORK / "source_cards_oldlike_topology"
MANIFEST = WORK / "prompt511_oldlike_topology_manifest.json"
README = WORK / "README_oldlike_topology.md"
OVERLAP_SOURCE = WORK / "overlap_oldlike_topology.source"
OVERLAP_LOG = WORK / "overlap_oldlike_topology.log"
SELECTED_RECS = ROOT / "outputs/reports/prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json"

PRIMARY_ADDED_MATERIAL = "CsI"
CANDIDATE_TAGS = [
    "prompt511",
    "old-like",
    "CsI",
    "active-material-continuity",
    "side-port-keepout-preserved",
]
ROI_SUPPRESSION_ALLOWED = False
SPOT_R90_SUPPRESSION_ALLOWED = False

# Current outer detector-bay side-port gap is narrower than this keepout:
# Vacuum_Jacket_Al_266mmClass side-port band gap phi 170.755682..189.219318,
# and the detector-bay side-port z band is -7.9..-2.5 cm.
BASE_SIDE_PORT_PHI_DEG = (170.755682, 189.219318)
BASE_SIDE_PORT_Z_CM = (-7.9, -2.5)
SIGNAL_KEEP_PHI_DEG = (165.0, 195.0)
SIGNAL_KEEP_Z_CM = (-7.9, -2.5)

# Place the candidate between the 60 K shield outer wall (r ~= 11.55 cm) and
# the vacuum-jacket inner radius (r ~= 12.9 cm).  That puts active material
# between the r ~= 13.3 cm Al annihilation wall and TES without touching the
# current side-window foils.
CSI_R_IN_CM = 11.60
CSI_R_OUT_CM = 12.86
AL_INNER_R_CM = (11.56, 11.58)
AL_OUTER_R_CM = (12.88, 12.89)
# The vacuum-jacket bottom cap occupies roughly z -14.1..-13.6 cm at this
# radius.  Start just above it so the scaffold is overlap-clean.
SIDE_Z_MIN_CM = -13.55
SIDE_Z_LOWER_MAX_CM = SIGNAL_KEEP_Z_CM[0]
SIDE_Z_UPPER_MIN_CM = SIGNAL_KEEP_Z_CM[1]
SIDE_Z_UPPER_MAX_CM = 2.00
UPPER_Z_MIN_CM = 2.00
UPPER_Z_MAX_CM = 28.00
UPPER_PHI_START_DEG = 5.0
UPPER_PHI_DELTA_DEG = 350.0

CSI_DENSITY_G_CM3 = 4.51
AL_DENSITY_G_CM3 = 2.70


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def fmt(x: float) -> str:
    return f"{x:.6g}"


def require_inputs() -> None:
    required = (
        SRC_GEOM,
        SRC_GEOM / f"{SRC_NAME}.geo.setup",
        SRC_GEOM / f"{SRC_NAME}.geo",
        SRC_GEOM / f"{SRC_NAME}.det",
        SRC_GEOM / f"Intro_{SRC_NAME}.geo",
        SOURCE_IN,
        SELECTED_RECS,
    )
    missing = [path for path in required if not path.exists()]
    if missing:
        details = "\n".join(f"- {rel(path)}" for path in missing)
        raise FileNotFoundError(f"old-like topology inputs are missing:\n{details}")


def replace_geometry_names(text: str) -> str:
    return text.replace(SRC_NAME, OUT_NAME)


def pcon_volume(name: str, material: str, phi0: float, dphi: float, z0: float, z1: float, r0: float, r1: float) -> list[str]:
    return [
        f"// Volume {name}; material={material}",
        f"Volume {name}",
        f"{name}.Material {material}",
        f"{name}.Visibility 1",
        f"{name}.Shape PCON {fmt(phi0)} {fmt(dphi)} 2 {fmt(z0)} {fmt(r0)} {fmt(r1)} {fmt(z1)} {fmt(r0)} {fmt(r1)}",
        "",
        f"{name}.Position 0 0 0",
        f"{name}.Mother InstrumentFrame",
        "",
    ]


def topology_regions() -> list[dict[str, float | str]]:
    return [
        {
            "key": "lower_full",
            "phi0": 0.0,
            "dphi": 360.0,
            "z0": SIDE_Z_MIN_CM,
            "z1": SIDE_Z_LOWER_MAX_CM,
            "purpose": "below side signal band, full active/material continuity",
        },
        {
            "key": "side_nonwindow_phi000_165",
            "phi0": 0.0,
            "dphi": SIGNAL_KEEP_PHI_DEG[0],
            "z0": SIGNAL_KEEP_Z_CM[0],
            "z1": SIGNAL_KEEP_Z_CM[1],
            "purpose": "side band non-window arc before the preserved signal keepout",
        },
        {
            "key": "side_nonwindow_phi195_360",
            "phi0": SIGNAL_KEEP_PHI_DEG[1],
            "dphi": 360.0 - SIGNAL_KEEP_PHI_DEG[1],
            "z0": SIGNAL_KEEP_Z_CM[0],
            "z1": SIGNAL_KEEP_Z_CM[1],
            "purpose": "side band non-window arc after the preserved signal keepout",
        },
        {
            "key": "upper_side_full",
            "phi0": 0.0,
            "dphi": 360.0,
            "z0": SIDE_Z_UPPER_MIN_CM,
            "z1": SIDE_Z_UPPER_MAX_CM,
            "purpose": "above side signal band, full active/material continuity to the current top annulus",
        },
        {
            "key": "upper_service_notched",
            "phi0": UPPER_PHI_START_DEG,
            "dphi": UPPER_PHI_DELTA_DEG,
            "z0": UPPER_Z_MIN_CM,
            "z1": UPPER_Z_MAX_CM,
            "purpose": "upper OVC/service column; +x notch avoids the top pump-line proxy",
        },
    ]


def material_volume_specs() -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for region in topology_regions():
        key = str(region["key"])
        specs.append(
            {
                **region,
                "name": f"Prompt511_OldLike_CsI_{key}",
                "material": "CsI",
                "r0": CSI_R_IN_CM,
                "r1": CSI_R_OUT_CM,
                "density": CSI_DENSITY_G_CM3,
                "active": True,
            }
        )
        specs.append(
            {
                **region,
                "name": f"Prompt511_OldLike_AlInnerSkin_{key}",
                "material": "Aluminium",
                "r0": AL_INNER_R_CM[0],
                "r1": AL_INNER_R_CM[1],
                "density": AL_DENSITY_G_CM3,
                "active": False,
            }
        )
        specs.append(
            {
                **region,
                "name": f"Prompt511_OldLike_AlOuterSkin_{key}",
                "material": "Aluminium",
                "r0": AL_OUTER_R_CM[0],
                "r1": AL_OUTER_R_CM[1],
                "density": AL_DENSITY_G_CM3,
                "active": False,
            }
        )
    return specs


def oldlike_topology_geo_block() -> str:
    lines = [
        "",
        "// Prompt-511 old-like CsI/material-continuity candidate (2026-06-20).",
        "// Adds active CsI inside the thin-Al side-wall leakage radius and thin Al skins for material continuity.",
        "// Preserves a side signal keepout larger than the current side-window design: phi 165..195 deg, z -7.9..-2.5 cm.",
        "// Geometry-only material-topology candidate; no analysis-selection mechanism is encoded here.",
        "",
    ]
    for spec in material_volume_specs():
        lines.extend(
            pcon_volume(
                str(spec["name"]),
                str(spec["material"]),
                float(spec["phi0"]),
                float(spec["dphi"]),
                float(spec["z0"]),
                float(spec["z1"]),
                float(spec["r0"]),
                float(spec["r1"]),
            )
        )
    return "\n".join(lines)


def scintillator_det_block(volume: str) -> str:
    return "\n".join(
        [
            "",
            f"Scintillator {volume}_SD",
            f"{volume}_SD.SensitiveVolume {volume}",
            f"{volume}_SD.DetectorVolume {volume}",
            f"{volume}_SD.TriggerThreshold 80",
            f"{volume}_SD.NoiseThresholdEqualsTriggerThreshold true",
            f"{volume}_SD.EnergyResolution Gauss 80 80 1",
            f"{volume}_SD.EnergyResolution Gauss 3000 3000 1",
            "",
        ]
    )


def oldlike_topology_det_block() -> str:
    volumes = [str(spec["name"]) for spec in material_volume_specs() if spec["material"] == "CsI"]
    blocks = ["", "// Prompt-511 old-like native CsI detector entries."]
    blocks.extend(scintillator_det_block(volume) for volume in volumes)
    return "\n".join(blocks)


def pcon_mass_kg(spec: dict[str, object]) -> float:
    r0 = float(spec["r0"])
    r1 = float(spec["r1"])
    dphi = float(spec["dphi"])
    z0 = float(spec["z0"])
    z1 = float(spec["z1"])
    density = float(spec["density"])
    volume_cm3 = math.pi * (r1 * r1 - r0 * r0) * (dphi / 360.0) * (z1 - z0)
    return volume_cm3 * density / 1000.0


def remove_copied_stale_artifacts() -> list[str]:
    removed = []
    patterns = (
        "*validation.json",
        "*bounds.json",
        "geometry_proxy_validation.json",
        "mass_budget.csv",
        "cosima_overlap.log",
        "overlap_check.source",
    )
    for pattern in patterns:
        for path in OUT_GEOM.glob(pattern):
            if path.is_file():
                path.unlink()
                removed.append(rel(path))
    return sorted(set(removed))


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

    stale_removed = remove_copied_stale_artifacts()

    setup = replace_geometry_names(OUT_SETUP.read_text(encoding="utf-8"))
    OUT_SETUP.write_text(setup, encoding="utf-8")

    geo_path = OUT_GEOM / f"{OUT_NAME}.geo"
    geo = replace_geometry_names(geo_path.read_text(encoding="utf-8"))
    geo = geo.rstrip() + oldlike_topology_geo_block() + "\n"
    geo_path.write_text(geo, encoding="utf-8")

    intro_path = OUT_GEOM / f"Intro_{OUT_NAME}.geo"
    intro_path.write_text(replace_geometry_names(intro_path.read_text(encoding="utf-8")), encoding="utf-8")

    det_path = OUT_GEOM / f"{OUT_NAME}.det"
    det = replace_geometry_names(det_path.read_text(encoding="utf-8"))
    det = det.rstrip() + oldlike_topology_det_block() + "\n"
    det_path.write_text(det, encoding="utf-8")

    csi_specs = [spec for spec in material_volume_specs() if spec["material"] == "CsI"]
    al_specs = [spec for spec in material_volume_specs() if spec["material"] == "Aluminium"]
    csi_masses = {str(spec["name"]): pcon_mass_kg(spec) for spec in csi_specs}
    al_masses = {str(spec["name"]): pcon_mass_kg(spec) for spec in al_specs}

    return {
        "geometry_setup": rel(OUT_SETUP),
        "geometry_geo": rel(geo_path),
        "geometry_det": rel(det_path),
        "base_geometry_setup": rel(SRC_GEOM / f"{SRC_NAME}.geo.setup"),
        "primary_added_material": PRIMARY_ADDED_MATERIAL,
        "added_csi_volumes": [str(spec["name"]) for spec in csi_specs],
        "added_al_volumes": [str(spec["name"]) for spec in al_specs],
        "radial_envelope_cm": {
            "csi": [CSI_R_IN_CM, CSI_R_OUT_CM],
            "al_inner_skin": list(AL_INNER_R_CM),
            "al_outer_skin": list(AL_OUTER_R_CM),
        },
        "side_signal_keepout": {
            "phi_deg": list(SIGNAL_KEEP_PHI_DEG),
            "z_cm": list(SIGNAL_KEEP_Z_CM),
            "base_outer_side_port_phi_deg": list(BASE_SIDE_PORT_PHI_DEG),
            "base_outer_side_port_z_cm": list(BASE_SIDE_PORT_Z_CM),
            "policy": "larger_than_current_side_port_gap",
        },
        "upper_service_notch": {
            "phi_deg": [UPPER_PHI_START_DEG, UPPER_PHI_START_DEG + UPPER_PHI_DELTA_DEG],
            "z_cm": [UPPER_Z_MIN_CM, UPPER_Z_MAX_CM],
            "notch_reason": "avoid DR_Still_PumpLine_SS_to_300K_top proxy at +x",
        },
        "estimated_added_csi_mass_kg": sum(csi_masses.values()),
        "estimated_added_al_mass_kg": sum(al_masses.values()),
        "estimated_added_csi_mass_breakdown_kg": csi_masses,
        "estimated_added_al_mass_breakdown_kg": al_masses,
        "optional_w_assist": {
            "enabled": False,
            "reason": "W-only diagnostic passed prompt proxy but carries high activation/neutron risk; this candidate keeps W out of the default topology.",
        },
        "stale_base_artifacts_removed": stale_removed,
        "selected_ray_proxy": selected_ray_proxy(),
    }


def in_phi(phi: float, start: float, delta: float) -> bool:
    if delta >= 360.0:
        return True
    end = start + delta
    if end <= 360.0:
        return start <= phi <= end
    wrapped = end - 360.0
    return phi >= start or phi <= wrapped


def csi_region_at(point: list[float]) -> str | None:
    radius = math.hypot(point[0], point[1])
    if not (CSI_R_IN_CM <= radius <= CSI_R_OUT_CM):
        return None
    phi = math.degrees(math.atan2(point[1], point[0])) % 360.0
    z = point[2]
    for region in topology_regions():
        if float(region["z0"]) <= z <= float(region["z1"]) and in_phi(phi, float(region["phi0"]), float(region["dphi"])):
            return str(region["key"])
    return None


def radius_roots(a: list[float], d: list[float], radius: float) -> list[float]:
    qa = d[0] * d[0] + d[1] * d[1]
    if qa == 0.0:
        return []
    qb = 2.0 * (a[0] * d[0] + a[1] * d[1])
    qc = a[0] * a[0] + a[1] * a[1] - radius * radius
    disc = qb * qb - 4.0 * qa * qc
    if disc < 0.0:
        return []
    root = math.sqrt(disc)
    return [(-qb - root) / (2.0 * qa), (-qb + root) / (2.0 * qa)]


def segment_length(d: list[float]) -> float:
    return math.sqrt(sum(value * value for value in d))


def point_at(a: list[float], d: list[float], s: float) -> list[float]:
    return [a[i] + d[i] * s for i in range(3)]


def solid_csi_path_length_cm(a: list[float], t: list[float]) -> tuple[float, set[str]]:
    d = [t[i] - a[i] for i in range(3)]
    cuts = [0.0, 1.0]
    cuts.extend(radius_roots(a, d, CSI_R_IN_CM))
    cuts.extend(radius_roots(a, d, CSI_R_OUT_CM))
    if abs(d[2]) > 1.0e-12:
        for region in topology_regions():
            cuts.append((float(region["z0"]) - a[2]) / d[2])
            cuts.append((float(region["z1"]) - a[2]) / d[2])
    clipped = sorted({round(max(0.0, min(1.0, s)), 12) for s in cuts if -1.0e-9 <= s <= 1.0 + 1.0e-9})
    length = 0.0
    regions: set[str] = set()
    line_length = segment_length(d)
    for s0, s1 in zip(clipped, clipped[1:]):
        if s1 <= s0:
            continue
        midpoint = point_at(a, d, 0.5 * (s0 + s1))
        region = csi_region_at(midpoint)
        if region is None:
            continue
        length += line_length * (s1 - s0)
        regions.add(region)
    return length, regions


def selected_ray_proxy() -> dict[str, object]:
    records = json.loads(SELECTED_RECS.read_text(encoding="utf-8"))
    caught_rate = 0.0
    missed_rate = 0.0
    caught = 0
    missed = 0
    by_region: dict[str, int] = {}
    lengths: list[tuple[float, float]] = []
    miss_samples = []
    for rec in records:
        weight = float(rec["rate_s-1"])
        length, regions = solid_csi_path_length_cm(rec["annihilation_local_cm"], rec["tes_centroid_local_cm"])
        if length <= 1.0e-9:
            missed += 1
            missed_rate += weight
            if len(miss_samples) < 8:
                a = rec["annihilation_local_cm"]
                miss_samples.append(
                    {
                        "annihilation_r_cm": math.hypot(float(a[0]), float(a[1])),
                        "annihilation_z_cm": float(a[2]),
                        "annihilation_phi_deg": math.degrees(math.atan2(float(a[1]), float(a[0]))) % 360.0,
                    }
                )
            continue
        caught += 1
        caught_rate += weight
        lengths.append((length, weight))
        for region in regions:
            by_region[region] = by_region.get(region, 0) + 1

    sorted_lengths = sorted(length for length, _ in lengths)
    if sorted_lengths:
        stats = {
            "min_cm": min(sorted_lengths),
            "p10_cm": sorted_lengths[len(sorted_lengths) // 10],
            "median_cm": sorted_lengths[len(sorted_lengths) // 2],
            "rate_weighted_mean_cm": sum(length * weight for length, weight in lengths) / caught_rate,
            "max_cm": max(sorted_lengths),
        }
    else:
        stats = {}
    return {
        "selected_records": len(records),
        "ray_trace_method": "straight-line annihilation-to-TES chord through generated CsI PCON regions; phi-boundary intersections are midpoint-sampled",
        "caught_events": caught,
        "caught_rate_s-1": caught_rate,
        "missed_events": missed,
        "missed_rate_s-1": missed_rate,
        "caught_by_region": by_region,
        "solid_csi_path_length_stats_cm": stats,
        "miss_samples": miss_samples,
        "claim_boundary": "Geometry proxy only; it is not a prompt rate, signal throughput, neutron/muon prompt, or activation result.",
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
        "status": "PASS_PROMPT511_OLDLIKE_TOPOLOGY_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT),
        "base_source_dir": rel(SOURCE_IN),
        "geometry_setup": rel(OUT_SETUP),
        "farfield_radius_cm": 60.0,
        "sources": rows,
    }
    (SOURCE_OUT / "source_migration_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_overlap_source() -> dict[str, str]:
    OVERLAP_SOURCE.write_text(
        f"""Version                     1
Geometry                    {OUT_SETUP}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_oldlike_topology_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
""",
        encoding="utf-8",
    )
    return {"overlap_source": rel(OVERLAP_SOURCE), "overlap_log": rel(OVERLAP_LOG)}


def write_readme(payload: dict[str, object]) -> None:
    geometry = payload["geometry"]
    assert isinstance(geometry, dict)
    ray = geometry["selected_ray_proxy"]
    assert isinstance(ray, dict)
    lines = [
        "# Prompt-511 Old-Like CsI/Material Topology Candidate",
        "",
        "Status: load/overlap-ready geometry scaffold; not a promoted MC result.",
        "",
        "Purpose:",
        "",
        "- Restore an old-like active/material column inside the thin-Al side-wall leakage radius using CsI as the primary material.",
        "- Preserve the current side signal port; this candidate leaves a keepout of phi 165..195 deg and z -7.9..-2.5 cm, wider than the current outer side-port gap.",
        "- Avoid ROI, spot-r90, or analysis-window suppression. The geometry must stand on material topology.",
        "- Keep W out of the default candidate because W-only diagnostics carry activation and neutron-prompt risk.",
        "",
        "Generated files:",
        "",
        f"- geometry setup: `{geometry['geometry_setup']}`",
        f"- geometry file: `{geometry['geometry_geo']}`",
        f"- detector map: `{geometry['geometry_det']}`",
        f"- migrated source cards: `{payload['sources']['source_dir']}`",
        f"- overlap source: `{payload['overlap']['overlap_source']}`",
        "",
        "Geometry change:",
        "",
        f"- added active CsI envelope: r `{CSI_R_IN_CM:g}..{CSI_R_OUT_CM:g} cm`.",
        f"- added thin Al skins: inner r `{AL_INNER_R_CM[0]:g}..{AL_INNER_R_CM[1]:g} cm`, outer r `{AL_OUTER_R_CM[0]:g}..{AL_OUTER_R_CM[1]:g} cm`.",
        f"- side lower/full continuity: z `{SIDE_Z_MIN_CM:g}..{SIDE_Z_LOWER_MAX_CM:g} cm`.",
        f"- side signal keepout: phi `{SIGNAL_KEEP_PHI_DEG[0]:g}..{SIGNAL_KEEP_PHI_DEG[1]:g} deg`, z `{SIGNAL_KEEP_Z_CM[0]:g}..{SIGNAL_KEEP_Z_CM[1]:g} cm`.",
        f"- upper service continuity: z `{UPPER_Z_MIN_CM:g}..{UPPER_Z_MAX_CM:g} cm`, phi `{UPPER_PHI_START_DEG:g}..{UPPER_PHI_START_DEG + UPPER_PHI_DELTA_DEG:g} deg` with a +x notch.",
        f"- estimated added CsI mass: `{geometry['estimated_added_csi_mass_kg']:.6g} kg`.",
        f"- estimated added Al mass: `{geometry['estimated_added_al_mass_kg']:.6g} kg`.",
        "",
        "Selected-current-event ray proxy:",
        "",
        f"- intercepted selected events: `{ray['caught_events']}/{ray['selected_records']}`.",
        f"- intercepted selected rate: `{ray['caught_rate_s-1']:.6g} cps`.",
        f"- missed selected rate: `{ray['missed_rate_s-1']:.6g} cps`.",
        f"- path length stats: `{json.dumps(ray['solid_csi_path_length_stats_cm'], sort_keys=True)}`.",
        "",
        "Claim boundary:",
        "",
        "- This scaffold only says the geometry is generated and source cards point at it.",
        "- The straight-line ray proxy is not an MC prompt rate and does not include CsI self-activity, Compton refill, neutron/muon prompt, delayed activation, or signal transport.",
        "- Promotion would require focused-signal preservation, prompt e+/n/mu+ smokes with native CsI detector entries, then separate activation/isotope accounting.",
    ]
    README.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload: dict[str, object] = {
        "status": "PASS_PROMPT511_OLDLIKE_TOPOLOGY_GEOMETRY_READY",
        "claim_level": "LOAD_OVERLAP_READY_SCAFFOLD_NO_RATE_AUTHORITY",
        "candidate_tags": CANDIDATE_TAGS,
        "base_geometry": rel(SRC_GEOM / f"{SRC_NAME}.geo.setup"),
        "geometry": geometry,
        "sources": sources,
        "overlap": overlap,
        "readme": rel(README),
        "constraints": {
            "primary_scintillator": "CsI",
            "roi_suppression_allowed": ROI_SUPPRESSION_ALLOWED,
            "spot_r90_suppression_allowed": SPOT_R90_SUPPRESSION_ALLOWED,
            "window_opening_policy": "not_narrowed",
            "window_keepout_larger_than_current_side_port": True,
            "long_mc_run": False,
        },
        "evidence_inputs": {
            "variant_review": "outputs/reports/prompt511_variant_review_20260620/REVIEW.md",
            "sideport_gap_clarification": "core_md/CLAUDE_PROMPT511_SIDEPORT_GAP_CLARIFICATION_20260620.md",
            "base_geometry_dir": rel(SRC_GEOM),
            "selected_records": rel(SELECTED_RECS),
        },
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_readme(payload)
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
