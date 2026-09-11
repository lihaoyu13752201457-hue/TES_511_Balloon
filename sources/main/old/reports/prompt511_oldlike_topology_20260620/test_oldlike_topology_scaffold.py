#!/usr/bin/env python3
"""Local scaffold checks for the prompt-511 old-like topology candidate."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_oldlike_topology_20260620"
BUILDER = WORK / "build_oldlike_topology_geometry.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_oldlike_topology_geometry", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_constants_preserve_side_signal_keepout():
    module = load_builder()
    assert module.PRIMARY_ADDED_MATERIAL == "CsI"
    assert "BGO" not in json.dumps(module.CANDIDATE_TAGS)
    assert module.SIGNAL_KEEP_PHI_DEG[0] <= 170.755682
    assert module.SIGNAL_KEEP_PHI_DEG[1] >= 189.219318
    assert module.SIGNAL_KEEP_Z_CM[0] <= -7.9
    assert module.SIGNAL_KEEP_Z_CM[1] >= -2.5
    assert module.ROI_SUPPRESSION_ALLOWED is False
    assert module.SPOT_R90_SUPPRESSION_ALLOWED is False


def test_generated_scaffold_has_native_csi_detectors_and_no_bgo():
    subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True)
    manifest = json.loads((WORK / "prompt511_oldlike_topology_manifest.json").read_text())
    setup = ROOT / manifest["geometry"]["geometry_setup"]
    geo = ROOT / manifest["geometry"]["geometry_geo"]
    det = ROOT / manifest["geometry"]["geometry_det"]
    assert setup.exists()
    assert geo.exists()
    assert det.exists()

    geo_text = geo.read_text()
    det_text = det.read_text()
    assert "Prompt511_OldLike_CsI_" in geo_text
    assert "Prompt511_OldLike_W_" not in geo_text
    assert "BGO" not in geo_text
    assert "ROI" not in geo_text
    assert "spot_r90" not in geo_text

    added_csi = manifest["geometry"]["added_csi_volumes"]
    assert len(added_csi) >= 4
    for volume in added_csi:
        assert f"Scintillator {volume}_SD" in det_text
        assert f"{volume}_SD.SensitiveVolume {volume}" in det_text
        assert f"{volume}_SD.TriggerThreshold 80" in det_text

    assert manifest["constraints"]["window_opening_policy"] == "not_narrowed"
    assert manifest["geometry"]["primary_added_material"] == "CsI"
    assert manifest["geometry"]["optional_w_assist"]["enabled"] is False


if __name__ == "__main__":
    failures = []
    for test in (test_constants_preserve_side_signal_keepout, test_generated_scaffold_has_native_csi_detectors_and_no_bgo):
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - tiny standalone check runner
            failures.append(f"{test.__name__}: {exc}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print("oldlike topology scaffold checks passed")
