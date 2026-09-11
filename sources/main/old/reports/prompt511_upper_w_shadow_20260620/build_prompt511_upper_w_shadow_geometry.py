#!/usr/bin/env python3
"""Build an upper-W-shadow prompt-511 geometry candidate.

This candidate is a diagnostic old-like passive-column test.  It extends the
inner-jacket W shadow into the upper OVC/service leakage z-range that VariantB
missed, while leaving the real side signal-port sector open at z ~= -5.2 cm.
It is not an authority CAD model.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_upper_w_shadow_20260620"
SRC_GEOM = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
SRC_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUT_GEOM = WORK / "geometry_upper_w_shadow"
OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_upper_w_shadow_r12p35_12p8"
SRC_SETUP = SRC_GEOM / f"{SRC_NAME}.geo.setup"
OUT_SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
SOURCE_IN = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT = WORK / "source_cards_upper_w_shadow"
MANIFEST = WORK / "prompt511_upper_w_shadow_manifest.json"
README = WORK / "README_upper_w_shadow.md"
SELECTED_RECS = ROOT / "outputs/reports/prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json"

W_DENSITY_G_CM3 = 19.3
W_MU_RHO_511_CM2_G = 0.0918
R_IN_CM = 12.35
R_OUT_CM = 12.80

# Keep the real side signal aperture open only around the actual side-entry z.
LOWER_Z_MIN_CM = -13.0
LOWER_Z_MAX_CM = 1.0
PORT_PHI_DEG = (171.0, 189.0)
PORT_Z_CM = (-7.2, -3.2)

# VariantB missed the upper crossings.  This band sits above the signal
# side-port z-range, so it should not clip the Laue side-entry window.  Leave a
# small +x notch for the real DR_Still_PumpLine_SS_to_300K_top service proxy.
UPPER_Z_MIN_CM = 1.05
UPPER_Z_MAX_CM = 28.0
UPPER_PHI_START_DEG = 5.0
UPPER_PHI_DELTA_DEG = 350.0

# Two local attenuation constants have been used in prior notes/scripts.  Keep
# both in the proxy manifest; the MC smoke is the authority gate.
W_MU_RHO_511_ALTERNATES_CM2_G = [0.0918, 0.137]


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
            SELECTED_RECS,
        )
        if not path.exists()
    ]
    if missing:
        joined = "\n".join(f"- {rel(path)}" for path in missing)
        raise FileNotFoundError(f"upper-W-shadow inputs are missing:\n{joined}")


def replace_geometry_names(text: str) -> str:
    return text.replace(SRC_NAME, OUT_NAME)


def pcon_volume(name: str, material: str, phi0: float, dphi: float, z0: float, z1: float) -> list[str]:
    return [
        f"Volume {name}",
        f"{name}.Material {material}",
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


def upper_w_shadow_geo_block() -> str:
    lines = [
        "",
        "// Prompt-511 upper-W-shadow candidate (2026-06-20).",
        "// Diagnostic passive-column test: cover VariantB's missed upper OVC/service z-range.",
        "// The true side signal-port sector is left open only at phi[171,189], z[-7.2,-3.2].",
    ]
    lines.extend(
        pcon_volume(
            "Prompt511_UpperWShadow_lower_nonport_arc",
            "W",
            189.0,
            342.0,
            LOWER_Z_MIN_CM,
            LOWER_Z_MAX_CM,
        )
    )
    lines.extend(
        pcon_volume(
            "Prompt511_UpperWShadow_port_below",
            "W",
            PORT_PHI_DEG[0],
            PORT_PHI_DEG[1] - PORT_PHI_DEG[0],
            LOWER_Z_MIN_CM,
            PORT_Z_CM[0],
        )
    )
    lines.extend(
        pcon_volume(
            "Prompt511_UpperWShadow_port_above",
            "W",
            PORT_PHI_DEG[0],
            PORT_PHI_DEG[1] - PORT_PHI_DEG[0],
            PORT_Z_CM[1],
            LOWER_Z_MAX_CM,
        )
    )
    lines.extend(
        pcon_volume(
            "Prompt511_UpperWShadow_upper_notched",
            "W",
            UPPER_PHI_START_DEG,
            UPPER_PHI_DELTA_DEG,
            UPPER_Z_MIN_CM,
            UPPER_Z_MAX_CM,
        )
    )
    return "\n".join(lines)


def volume_mass_kg(phi0: float, dphi: float, z0: float, z1: float) -> float:
    del phi0
    volume_cm3 = math.pi * (R_OUT_CM * R_OUT_CM - R_IN_CM * R_IN_CM) * (dphi / 360.0) * (z1 - z0)
    return volume_cm3 * W_DENSITY_G_CM3 / 1000.0


def in_phi(phi: float, start: float, delta: float) -> bool:
    if delta >= 360.0:
        return True
    end = start + delta
    if end <= 360.0:
        return start <= phi <= end
    wrapped = end - 360.0
    return phi >= start or phi <= wrapped


def radius_roots(a: list[float], d: list[float], radius: float) -> list[float]:
    a2 = d[0] * d[0] + d[1] * d[1]
    if a2 == 0.0:
        return []
    b2 = 2.0 * (a[0] * d[0] + a[1] * d[1])
    c2 = a[0] * a[0] + a[1] * a[1] - radius * radius
    disc = b2 * b2 - 4.0 * a2 * c2
    if disc < 0.0:
        return []
    root = math.sqrt(disc)
    return [(-b2 - root) / (2.0 * a2), (-b2 + root) / (2.0 * a2)]


def segment_length(d: list[float]) -> float:
    return math.sqrt(sum(value * value for value in d))


def point_at(a: list[float], d: list[float], s: float) -> list[float]:
    return [a[i] + d[i] * s for i in range(3)]


def cross_radius(a: list[float], t: list[float], radius: float) -> list[float] | None:
    d = [t[i] - a[i] for i in range(3)]
    for s in sorted(radius_roots(a, d, radius)):
        if 0.0 <= s <= 1.0:
            return point_at(a, d, s)
    return None


def actual_shadow_hit(point: list[float]) -> str | None:
    phi = math.degrees(math.atan2(point[1], point[0])) % 360.0
    z = point[2]
    if LOWER_Z_MIN_CM <= z <= LOWER_Z_MAX_CM:
        if not (PORT_PHI_DEG[0] <= phi <= PORT_PHI_DEG[1] and PORT_Z_CM[0] <= z <= PORT_Z_CM[1]):
            return "lower_nonport_or_port_fill"
    if UPPER_Z_MIN_CM <= z <= UPPER_Z_MAX_CM and in_phi(phi, UPPER_PHI_START_DEG, UPPER_PHI_DELTA_DEG):
        return "upper_notched"
    return None


def solid_w_path_length_cm(a: list[float], t: list[float]) -> tuple[float, set[str]]:
    d = [t[i] - a[i] for i in range(3)]
    cuts = [0.0, 1.0]
    for radius in (R_IN_CM, R_OUT_CM):
        cuts.extend(radius_roots(a, d, radius))
    if abs(d[2]) > 1.0e-12:
        for z in (LOWER_Z_MIN_CM, LOWER_Z_MAX_CM, PORT_Z_CM[0], PORT_Z_CM[1], UPPER_Z_MIN_CM, UPPER_Z_MAX_CM):
            cuts.append((z - a[2]) / d[2])

    clipped = sorted({round(max(0.0, min(1.0, s)), 12) for s in cuts if -1.0e-9 <= s <= 1.0 + 1.0e-9})
    length = 0.0
    regions: set[str] = set()
    line_length = segment_length(d)
    for s0, s1 in zip(clipped, clipped[1:]):
        if s1 <= s0:
            continue
        midpoint = point_at(a, d, 0.5 * (s0 + s1))
        radius = math.hypot(midpoint[0], midpoint[1])
        if not (R_IN_CM <= radius <= R_OUT_CM):
            continue
        region = actual_shadow_hit(midpoint)
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
        w = float(rec["rate_s-1"])
        length, regions = solid_w_path_length_cm(rec["annihilation_local_cm"], rec["tes_centroid_local_cm"])
        if length <= 1.0e-9:
            missed += 1
            missed_rate += w
            p = cross_radius(rec["annihilation_local_cm"], rec["tes_centroid_local_cm"], 0.5 * (R_IN_CM + R_OUT_CM))
            if p is not None and len(miss_samples) < 8:
                miss_samples.append({"z_cm": p[2], "phi_deg": math.degrees(math.atan2(p[1], p[0])) % 360.0})
        else:
            caught += 1
            caught_rate += w
            lengths.append((length, w))
            for region in regions:
                by_region[region] = by_region.get(region, 0) + 1

    path_weighted = {}
    for mu_rho in W_MU_RHO_511_ALTERNATES_CM2_G:
        mu = mu_rho * W_DENSITY_G_CM3
        path_weighted[str(mu_rho)] = {
            "mu_rho_cm2_g": mu_rho,
            "normal_incidence_511_transmission": math.exp(-mu * (R_OUT_CM - R_IN_CM)),
            "path_weighted_residual_estimate_s-1": missed_rate
            + sum(w * math.exp(-mu * length) for length, w in lengths),
        }

    sorted_lengths = sorted(length for length, _ in lengths)
    if sorted_lengths:
        length_stats = {
            "min_cm": min(sorted_lengths),
            "p10_cm": sorted_lengths[len(sorted_lengths) // 10],
            "median_cm": sorted_lengths[len(sorted_lengths) // 2],
            "rate_weighted_mean_cm": sum(length * w for length, w in lengths) / caught_rate,
            "max_cm": max(sorted_lengths),
        }
    else:
        length_stats = {}
    return {
        "selected_records": len(records),
        "ray_trace_method": "piecewise segment-length through actual PCON z/phi coverage; not a single mid-radius hit test",
        "caught_events": caught,
        "caught_rate_s-1": caught_rate,
        "missed_events": missed,
        "missed_rate_s-1": missed_rate,
        "caught_by_region": by_region,
        "nominal_w_thickness_cm": R_OUT_CM - R_IN_CM,
        "solid_path_length_stats_cm": length_stats,
        "attenuation_estimates": path_weighted,
        "miss_samples": miss_samples,
        "claim_boundary": "Straight-line selected-event proxy only; MC must close self-emission, Compton refill, n/mu prompt, signal transport, and activation.",
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

    setup = replace_geometry_names(OUT_SETUP.read_text(encoding="utf-8"))
    OUT_SETUP.write_text(setup, encoding="utf-8")

    geo_path = OUT_GEOM / f"{OUT_NAME}.geo"
    geo = replace_geometry_names(geo_path.read_text(encoding="utf-8"))
    geo = geo.rstrip() + upper_w_shadow_geo_block() + "\n"
    geo_path.write_text(geo, encoding="utf-8")

    intro_path = OUT_GEOM / f"Intro_{OUT_NAME}.geo"
    intro_path.write_text(replace_geometry_names(intro_path.read_text(encoding="utf-8")), encoding="utf-8")

    det_path = OUT_GEOM / f"{OUT_NAME}.det"
    det_path.write_text(replace_geometry_names(det_path.read_text(encoding="utf-8")), encoding="utf-8")

    masses = {
        "lower_nonport_arc_kg": volume_mass_kg(189.0, 342.0, LOWER_Z_MIN_CM, LOWER_Z_MAX_CM),
        "port_below_kg": volume_mass_kg(PORT_PHI_DEG[0], 18.0, LOWER_Z_MIN_CM, PORT_Z_CM[0]),
        "port_above_kg": volume_mass_kg(PORT_PHI_DEG[0], 18.0, PORT_Z_CM[1], LOWER_Z_MAX_CM),
        "upper_notched_kg": volume_mass_kg(
            UPPER_PHI_START_DEG,
            UPPER_PHI_DELTA_DEG,
            UPPER_Z_MIN_CM,
            UPPER_Z_MAX_CM,
        ),
    }
    return {
        "geometry_setup": rel(OUT_SETUP),
        "geometry_geo": rel(geo_path),
        "geometry_det": rel(det_path),
        "added_material": "W",
        "added_w_envelope": {
            "r_cm": [R_IN_CM, R_OUT_CM],
            "lower_z_cm": [LOWER_Z_MIN_CM, LOWER_Z_MAX_CM],
            "signal_port_gap": {"phi_deg": list(PORT_PHI_DEG), "z_cm": list(PORT_Z_CM)},
            "upper_notched_z_cm": [UPPER_Z_MIN_CM, UPPER_Z_MAX_CM],
            "upper_notched_phi_deg": [UPPER_PHI_START_DEG, UPPER_PHI_START_DEG + UPPER_PHI_DELTA_DEG],
        },
        "estimated_added_w_mass_kg": sum(masses.values()),
        "estimated_added_w_mass_breakdown_kg": masses,
        "selected_ray_proxy": selected_ray_proxy(),
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
        "status": "PASS_PROMPT511_UPPER_W_SHADOW_SOURCE_CARDS",
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
    source = WORK / "overlap_upper_w_shadow.source"
    log = WORK / "overlap_upper_w_shadow.log"
    source.write_text(
        f"""Version                     1
Geometry                    {OUT_SETUP}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_upper_w_shadow_overlap
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
    ray = geometry["selected_ray_proxy"]
    assert isinstance(ray, dict)
    lines = [
        "# Prompt-511 Upper W Shadow Candidate",
        "",
        "Status: geometry/source-card candidate for prompt mechanism testing.",
        "",
        "Purpose:",
        "",
        "- Test whether the VariantB failure is primarily finite-z coverage of the upper OVC/service leakage paths.",
        "- Keep the current side signal-port aperture open; do not use ROI or focal-spot cuts.",
        "- Treat this as a diagnostic candidate because added W mass can raise neutron prompt and activation.",
        "",
        "Geometry change:",
        "",
        f"- candidate setup: `{geometry['geometry_setup']}`",
        f"- W radial envelope: `{R_IN_CM:g}..{R_OUT_CM:g} cm`.",
        f"- lower non-port/port-fill range: z `{LOWER_Z_MIN_CM:g}..{LOWER_Z_MAX_CM:g} cm`, with signal gap phi `{PORT_PHI_DEG[0]:g}..{PORT_PHI_DEG[1]:g}` and z `{PORT_Z_CM[0]:g}..{PORT_Z_CM[1]:g}` left open.",
        f"- upper notched range: z `{UPPER_Z_MIN_CM:g}..{UPPER_Z_MAX_CM:g} cm`, phi `{UPPER_PHI_START_DEG:g}..{UPPER_PHI_START_DEG + UPPER_PHI_DELTA_DEG:g}`; the small +x notch avoids the DR pump-line proxy.",
        f"- estimated added W mass: `{geometry['estimated_added_w_mass_kg']:.6g} kg`.",
        "",
        "Selected-current-event ray proxy:",
        "",
        f"- caught selected events: `{ray['caught_events']}/{ray['selected_records']}`.",
        f"- caught selected rate: `{ray['caught_rate_s-1']:.6g} cps`.",
        f"- missed selected rate: `{ray['missed_rate_s-1']:.6g} cps`.",
        f"- path-length proxy residual estimates: `{json.dumps(ray['attenuation_estimates'], sort_keys=True)}`.",
        "",
        "Claim boundary:",
        "",
        "- This is not a total-background or sensitivity result.",
        "- The ray proxy ignores new W self-emission, Compton refill, neutron/muon prompt, delayed activation, and signal transport.",
        "- A prompt-only e+ smoke is required before spending n/mu and isotope-record budget.",
    ]
    README.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload = {
        "status": "PASS_PROMPT511_UPPER_W_SHADOW_GEOMETRY_READY",
        "claim_level": "PROMPT511_UPPER_W_SHADOW_DESIGN_SMOKE_NO_RATE_AUTHORITY",
        "base_geometry": rel(SRC_SETUP),
        "geometry": geometry,
        "sources": sources,
        "overlap": overlap,
        "readme": rel(README),
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_readme(payload)
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
