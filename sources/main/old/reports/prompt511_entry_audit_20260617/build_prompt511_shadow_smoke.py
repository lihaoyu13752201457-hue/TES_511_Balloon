#!/usr/bin/env python3
"""Build minimal prompt-511 shadow-shield smoke geometries and source cards.

This is intentionally small-scope: it does not edit the authority geometry.
It copies the current v3p5 proxy geometry, appends simple W PCON sector shells
inside the side-entry cryostat, and creates low-stat prompt-eplus source cards.
The generated candidates are for smoke testing only.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/reports/prompt511_shadow_smoke_20260617"

BASE_GEO_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
BASE_GEO_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
BASE_SOURCE = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45/Background_eplus_fullsphere20.source"
BASE_SETUP = BASE_GEO_DIR / f"{BASE_GEO_NAME}.geo.setup"


@dataclass(frozen=True)
class Candidate:
    name: str
    r0_cm: float
    r1_cm: float
    z0_cm: float
    z1_cm: float
    gap0_deg: float = 160.0
    gap1_deg: float = 200.0
    note: str = ""


CANDIDATES = [
    Candidate(
        name="w_shadow_gap_safe_r8p39_8p48_zm10p3_z5p3",
        r0_cm=8.39,
        r1_cm=8.48,
        z0_cm=-10.3,
        z1_cm=5.3,
        note="CAD-safer thin shell in the narrow radial gap inside the Still shield; z-range avoids bottom caps and support-ring planes; expected analytic suppression is modest.",
    ),
    Candidate(
        name="w_shadow_mid_r7p85_8p48_zm10p3_z5p3",
        r0_cm=7.85,
        r1_cm=8.48,
        z0_cm=-10.3,
        z1_cm=5.3,
        note="More aggressive shell with cap/ring z-range trimmed; expected to remain overlap-prone with local can/support features.",
    ),
]


def fmt(x: float) -> str:
    return f"{x:.6g}"


def candidate_geo_name(candidate: Candidate) -> str:
    return f"{BASE_GEO_NAME}_{candidate.name}"


def sector_specs(candidate: Candidate) -> list[tuple[str, float, float]]:
    """Return two PCON sectors leaving the signal port gap open."""
    return [
        ("sector_a", 0.025, candidate.gap0_deg - 0.05),
        ("sector_b", candidate.gap1_deg + 0.025, 360.0 - candidate.gap1_deg - 0.05),
    ]


def append_shadow_volumes(geo_path: Path, candidate: Candidate) -> None:
    blocks = [
        "",
        f"// Prompt-511 smoke candidate: {candidate.name}",
        f"// {candidate.note}",
        f"// W shell r=[{candidate.r0_cm},{candidate.r1_cm}] cm, z=[{candidate.z0_cm},{candidate.z1_cm}] cm,",
        f"// with signal port phi gap [{candidate.gap0_deg},{candidate.gap1_deg}] deg left open.",
    ]
    for suffix, start, delta in sector_specs(candidate):
        volume = f"Prompt511_W_Shadow_{candidate.name}_{suffix}"
        blocks.extend(
            [
                f"Volume {volume}",
                f"{volume}.Material W",
                f"{volume}.Visibility 1",
                (
                    f"{volume}.Shape PCON {fmt(start)} {fmt(delta)} 2 "
                    f"{fmt(candidate.z0_cm)} {fmt(candidate.r0_cm)} {fmt(candidate.r1_cm)} "
                    f"{fmt(candidate.z1_cm)} {fmt(candidate.r0_cm)} {fmt(candidate.r1_cm)}"
                ),
                f"{volume}.Position 0 0 0",
                f"{volume}.Mother InstrumentFrame",
                "",
            ]
        )
    with geo_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(blocks))


def rewrite_setup(setup_path: Path, old_name: str, new_name: str) -> None:
    text = setup_path.read_text(encoding="utf-8")
    text = text.replace(f"Name {old_name}", f"Name {new_name}")
    text = text.replace(f"Include {old_name}.geo", f"Include {new_name}.geo")
    text = text.replace(f"Include {old_name}.det", f"Include {new_name}.det")
    setup_path.write_text(text, encoding="utf-8")


def rewrite_source(source_path: Path, candidate: Candidate, setup_path: Path, events: int) -> None:
    text = BASE_SOURCE.read_text(encoding="utf-8")
    text = text.replace(
        "Geometry outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup",
        f"Geometry {setup_path}",
    )
    text = text.replace("Background_eplus_fullsphere20.Events 1000000", f"Background_eplus_fullsphere20.Events {events}")
    text = text.replace(
        "Background_eplus_fullsphere20.FileName Background_eplus_fullsphere20",
        f"Background_eplus_fullsphere20.FileName {OUT / candidate.name / 'Background_eplus_fullsphere20'}",
    )
    source_path.write_text(text, encoding="utf-8")


def write_overlap_source(path: Path, setup_path: Path, run_name: str) -> None:
    text = f"""Version                     1
Geometry                    {setup_path}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_{run_name}_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    path.write_text(text, encoding="utf-8")


def build_candidate(candidate: Candidate, events: int) -> dict:
    cand_dir = OUT / candidate.name
    geo_dir = cand_dir / "geometry"
    if geo_dir.exists():
        shutil.rmtree(geo_dir)
    shutil.copytree(BASE_GEO_DIR, geo_dir)

    old_geo = geo_dir / f"{BASE_GEO_NAME}.geo"
    old_setup = geo_dir / f"{BASE_GEO_NAME}.geo.setup"
    old_det = geo_dir / f"{BASE_GEO_NAME}.det"

    new_name = candidate_geo_name(candidate)
    new_geo = geo_dir / f"{new_name}.geo"
    new_setup = geo_dir / f"{new_name}.geo.setup"
    new_det = geo_dir / f"{new_name}.det"

    old_geo.rename(new_geo)
    old_setup.rename(new_setup)
    old_det.rename(new_det)

    rewrite_setup(new_setup, BASE_GEO_NAME, new_name)
    append_shadow_volumes(new_geo, candidate)

    source_path = cand_dir / f"{candidate.name}_eplus_smoke.source"
    overlap_source = cand_dir / f"{candidate.name}_overlap.source"
    rewrite_source(source_path, candidate, new_setup, events)
    write_overlap_source(overlap_source, new_setup, candidate.name)

    return {
        "name": candidate.name,
        "note": candidate.note,
        "r0_cm": candidate.r0_cm,
        "r1_cm": candidate.r1_cm,
        "z0_cm": candidate.z0_cm,
        "z1_cm": candidate.z1_cm,
        "signal_gap_deg": [candidate.gap0_deg, candidate.gap1_deg],
        "geometry_setup": str(new_setup.relative_to(ROOT)),
        "source": str(source_path.relative_to(ROOT)),
        "overlap_source": str(overlap_source.relative_to(ROOT)),
        "events": events,
    }


def build_baseline(events: int) -> dict:
    base_dir = OUT / "baseline"
    base_dir.mkdir(parents=True, exist_ok=True)
    source_path = base_dir / "baseline_eplus_smoke.source"
    text = BASE_SOURCE.read_text(encoding="utf-8")
    text = text.replace("Background_eplus_fullsphere20.Events 1000000", f"Background_eplus_fullsphere20.Events {events}")
    text = text.replace(
        "Background_eplus_fullsphere20.FileName Background_eplus_fullsphere20",
        f"Background_eplus_fullsphere20.FileName {base_dir / 'Background_eplus_fullsphere20'}",
    )
    source_path.write_text(text, encoding="utf-8")
    overlap_source = base_dir / "baseline_overlap.source"
    write_overlap_source(overlap_source, BASE_SETUP, "baseline")
    return {
        "name": "baseline",
        "geometry_setup": str(BASE_SETUP.relative_to(ROOT)),
        "source": str(source_path.relative_to(ROOT)),
        "overlap_source": str(overlap_source.relative_to(ROOT)),
        "events": events,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    events = 200000
    manifest = {
        "status": "PROMPT511_SHADOW_SMOKE_INPUTS_BUILT",
        "base_geometry": str((BASE_GEO_DIR / f"{BASE_GEO_NAME}.geo.setup").relative_to(ROOT)),
        "base_source": str(BASE_SOURCE.relative_to(ROOT)),
        "events_per_candidate": events,
        "baseline": build_baseline(events),
        "candidates": [build_candidate(c, events) for c in CANDIDATES],
    }
    manifest_path = OUT / "prompt511_shadow_smoke_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
