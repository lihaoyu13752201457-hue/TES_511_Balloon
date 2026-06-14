#!/usr/bin/env python3
"""Build full-sphere atmospheric source cards for the Bgo_sample geometry."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE_SOURCE_DIR = ROOT / "config" / "megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
BGO_SUMMARY = ROOT / "Bgo_sample" / "bgo_sample_summary.json"
BGO_SETUP = ROOT / "Bgo_sample" / "Bgo_sample.geo.setup"
OUT_DIR = ROOT / "config" / "megalib_sources_fullsphere20_bgo_sample_tilt45"
MANIFEST = OUT_DIR / "source_migration_manifest.json"

GEOMETRY_LINE_RE = re.compile(r"^Geometry\s+.+$", re.MULTILINE)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if not BASE_SOURCE_DIR.exists():
        raise SystemExit(f"Missing base source directory: {BASE_SOURCE_DIR}")
    if not BGO_SUMMARY.exists():
        raise SystemExit(f"Missing BGO summary: {BGO_SUMMARY}")
    if not BGO_SETUP.exists():
        raise SystemExit(f"Missing BGO geometry setup: {BGO_SETUP}")

    summary = load_json(BGO_SUMMARY)
    checks = summary.get("checks", {})
    extents = summary.get("geometry_extents", {})
    radius = float(extents.get("recommended_farfield_radius_cm", 60.0))
    instrument_frame = extents.get("instrument_frame", {})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geometry_line = f"Geometry {rel(BGO_SETUP)}"
    source_rows: list[dict[str, Any]] = []

    for src in sorted(BASE_SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        text = src.read_text(encoding="utf-8", errors="replace")
        if not GEOMETRY_LINE_RE.search(text):
            raise SystemExit(f"Source card has no Geometry line: {src}")
        header = "\n".join(
            [
                "# Bgo_sample migrated source card",
                f"# base_source={rel(src)}",
                f"# geometry_setup={rel(BGO_SETUP)}",
                "# megalib_length_unit=cm",
                f"# farfield_radius_cm={radius:.9g}",
                "# pointing_policy=InstrumentFrame rotated 0 45 0 deg; local side-window -x looks 45 deg upward in global zenith frame",
                f"# bgo_claim_level={summary.get('claim_level')}",
                f"# bgo_threshold_keV={checks.get('bgo_veto_threshold_keV')}",
                f"# bgo_attenuation_max_abs_relative_difference={checks.get('attenuation_max_abs_relative_difference')}",
                "",
            ]
        )
        migrated = GEOMETRY_LINE_RE.sub(geometry_line, text, count=1)
        out = OUT_DIR / src.name
        out.write_text(header + migrated, encoding="utf-8")
        source_rows.append(
            {
                "source": rel(out),
                "base_source": rel(src),
                "geometry_setup": rel(BGO_SETUP),
            }
        )

    manifest = {
        "status": "PASS",
        "claim_level": "BGO_SAMPLE_STEP02_SOURCE_CARDS_NO_TRANSPORT",
        "source_dir": rel(OUT_DIR),
        "base_source_dir": rel(BASE_SOURCE_DIR),
        "bgo_summary": rel(BGO_SUMMARY),
        "geometry_setup": rel(BGO_SETUP),
        "bgo_step01_status": summary.get("status"),
        "bgo_step01_claim_level": summary.get("claim_level"),
        "farfield_radius_cm": radius,
        "farfield_area_cm2": 3.141592653589793 * radius * radius,
        "geometry_extents": extents,
        "bgo_checks": {
            "attenuation_status": checks.get("attenuation_status"),
            "attenuation_max_abs_relative_difference": checks.get("attenuation_max_abs_relative_difference"),
            "bgo_veto_threshold_keV": checks.get("bgo_veto_threshold_keV"),
            "bgo_threshold_detectors": checks.get("bgo_proxy_detector_threshold70_count"),
            "transport_status": checks.get("transport_status"),
            "cosima_overlap_status": checks.get("cosima_overlap_status"),
        },
        "pointing_policy": {
            "megalib_length_unit": "cm",
            "zenith_frame": "FarFieldAreaSource theta/phi bins remain in global zenith coordinates",
            "implementation": "whole detector mass model is tilted through InstrumentFrame.Rotation 0 45 0",
            "side_window_local_look_axis": instrument_frame.get("side_window_local_look_axis", "-x"),
            "side_window_global_look_vector": instrument_frame.get("side_window_global_look_vector"),
            "side_window_look_elevation_deg": instrument_frame.get("side_window_look_elevation_deg"),
            "incoming_photon_global_axis": instrument_frame.get("incoming_photon_global_axis"),
        },
        "sources": source_rows,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "sources": len(source_rows),
                "out_dir": rel(OUT_DIR),
                "geometry_setup": rel(BGO_SETUP),
                "farfield_radius_cm": radius,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
