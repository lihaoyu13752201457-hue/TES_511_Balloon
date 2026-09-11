#!/usr/bin/env python3
"""Fail-closed static validation for the LC1 shrink-only geometries."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
MANIFEST = PACKAGE / "data/lc1_geometry_manifest.json"
OUTPUT = PACKAGE / "data/lc1_geometry_validation.json"
INTRO = PACKAGE / "geometry/Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
MATERIALS = PACKAGE / "geometry/Materials_DEMO2_DR_v3p5.geo"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base_geo = ROOT / data["baseline"]["geo"]["path"]
    base_det = ROOT / data["baseline"]["det"]["path"]
    require(sha256(base_geo) == data["baseline"]["geo"]["sha256"], "baseline GEO changed")
    require(sha256(base_det) == data["baseline"]["det"]["sha256"], "baseline DET changed")
    base_text = base_geo.read_text(encoding="utf-8")
    base_volumes = re.findall(r"^Volume\s+(\S+)\s*$", base_text, flags=re.MULTILINE)
    require(len(base_volumes) == len(set(base_volumes)), "baseline contains duplicate volumes")
    checks = []
    for variant in data["variants"]:
        geo = ROOT / variant["geo"]["path"]
        det = ROOT / variant["det"]["path"]
        setup = ROOT / variant["setup"]["path"]
        require(sha256(geo) == variant["geo"]["sha256"], f"{variant['key']} GEO hash mismatch")
        require(sha256(det) == variant["det"]["sha256"], f"{variant['key']} DET hash mismatch")
        require(sha256(setup) == variant["setup"]["sha256"], f"{variant['key']} setup hash mismatch")
        require(det.read_bytes() == base_det.read_bytes(), f"{variant['key']} DET is not byte-identical")
        text = geo.read_text(encoding="utf-8")
        restored = text
        for edit in reversed(variant["edits"]):
            require(restored.count(edit["new"]) == 1, f"{variant['key']} new token count is not one: {edit['label']}")
            restored = restored.replace(edit["new"], edit["old"], 1)
        require(restored == base_text, f"{variant['key']} is not an exact declared delta")
        volumes = re.findall(r"^Volume\s+(\S+)\s*$", text, flags=re.MULTILINE)
        require(volumes == base_volumes, f"{variant['key']} volume declarations changed")
        setup_text = setup.read_text(encoding="utf-8")
        require(f"Include {geo.resolve()}" in setup_text, f"{variant['key']} setup GEO include mismatch")
        require(f"Include {det.resolve()}" in setup_text, f"{variant['key']} setup DET include mismatch")
        require("cosima_spectra_dp_2602units" not in text, f"{variant['key']} contains legacy spectrum path")
        checks.append({
            "key": variant["key"],
            "exact_declared_delta": True,
            "det_byte_identical": True,
            "volume_declarations_identical": True,
            "absolute_setup_includes": True,
            "legacy_spectrum_reference_absent": True,
            "cosima_geometry_load": "NOT_RUN",
        })

    base_intro = base_geo.parent / INTRO.name
    base_materials = base_geo.parent / MATERIALS.name
    require(INTRO.read_bytes() == base_intro.read_bytes(), "Intro copy changed")
    require(MATERIALS.read_bytes() == base_materials.read_bytes(), "Materials copy changed")
    mass = data["mass_model"]
    require(mass["LC1_Cu_subset_total_kg"] < mass["current_subset_total_kg"], "Cu candidate did not reduce mass")
    require(mass["LC1_CuNb_subset_total_kg"] < mass["LC1_Cu_subset_total_kg"], "Nb candidate did not reduce mass")
    require(
        mass["LC2_CuNb_MXC3mm_subset_total_kg"] < mass["LC1_CuNb_subset_total_kg"],
        "LC2 MXC thinning did not reduce mass",
    )
    result = {
        "schema_version": 1,
        "status": "PASS_LC1_STATIC_GEOMETRY_VALIDATION__COSIMA_NOT_RUN",
        "checks": checks,
        "mass_model": mass,
        "claim_boundary": "Static exact-delta and mass validation only; no overlap, transport, thermal, mechanical, or magnetic authority.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
