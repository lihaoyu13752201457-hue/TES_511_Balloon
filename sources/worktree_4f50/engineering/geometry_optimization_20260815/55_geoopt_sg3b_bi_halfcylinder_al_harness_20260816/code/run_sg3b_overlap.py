#!/usr/bin/env python3
"""Reuse the SG3 geometry-only Cosima overlap harness for SG3B."""
from pathlib import Path

source_path = Path(__file__).resolve().parents[2] / "53_geoopt_sg3_cu_ring_bi_umbrella_20260816/code/run_sg3_overlap.py"
source = source_path.read_text(encoding="utf-8")
replacements = {
    'STEM = "DEMO2_DR_v3p5_SG3"': 'STEM = "DEMO2_DR_v3p5_SG3B"',
    'STATIC_VALIDATION = AUDIT_DIR / "sg3_geometry_validation.json"': 'STATIC_VALIDATION = AUDIT_DIR / "sg3b_geometry_validation.json"',
    'DEFAULT_OUTPUT = AUDIT_DIR / "sg3_overlap_validation.json"': 'DEFAULT_OUTPUT = AUDIT_DIR / "sg3b_overlap_validation.json"',
    'DEFAULT_LOG = AUDIT_DIR / "sg3_overlap_cosima.log"': 'DEFAULT_LOG = AUDIT_DIR / "sg3b_overlap_cosima.log"',
    '"model_identity": "SG3"': '"model_identity": "SG3B"',
    '"PASS__SG3_TWO_CHANGE_BYTE_REVERSIBLE_SF3_CHILD"': '"PASS__SG3B_DETERMINISTIC_GEOMETRY_BUILD"',
    'static_core = static.get("generated", {})': 'static_core = static.get("outputs", {})',
}
for old,new in replacements.items():
    if old not in source: raise RuntimeError(f"upstream overlap harness drift: {old}")
    source=source.replace(old,new)
exec(compile(source,str(Path(__file__).resolve()),"exec"),{"__name__":"__main__","__file__":str(Path(__file__).resolve())})
