#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add a native MEGAlib TES-trigger + CsI-veto block to the DEMO2 .det authority.

Point-7 (anti-coincidence) implementation, "native Trigger + keep post-processing":

* The detector map (.det) gains a formal, citable MEGAlib trigger model:
    - one non-veto main trigger on any Calorimeter (the 6 TES layers D1..D6);
    - one veto trigger per CsI active-shield segment (Side/Bottom/Top).
* This mirrors ecosystem practice (resource/examples/geomega/GRI shield triggers,
  cosiballoon/CsIShield.geo, COSI Ge guard ring): a threshold-only hardware veto.
* MEGAlib requires that a detector carrying ONLY veto triggers also sets
  `NoiseThresholdEqualsTriggerThreshold true`; we set the CsI veto/storage
  threshold to the project analysis baseline 50 keV (bounds.json also records a
  30 keV CsI design recommendation as an alternative).

IMPORTANT coexistence / re-run caveat (see the appended .det comment too):
  The completed production .sim files were generated BEFORE this trigger with
  full event storage and NO trigger, and the post-processing veto in
  make_complete_day15_report_ADR.py (1 us coincidence window, summed-CsI 50 keV
  threshold, accidental/self-veto, Compton/FoV) remains the QUANTITATIVE
  authority. The native trigger here is the formal detector-trigger model only;
  current results are unchanged. If the chain is ever re-run with this native
  veto active, CsI hits below the per-segment 50 keV threshold (and shield-only
  / no-TES events) are no longer stored, which the summed-CsI + accidental
  post-processing model needs -- so that model must then be re-derived
  consistently. The two layers are complementary, not redundant: native =
  per-segment threshold veto; post-processing = summed time-window veto +
  accidentals that a threshold-only native veto cannot capture.

Idempotent: re-running detects the existing trigger block and does nothing.
A timestamped backup of the original .det is written next to it.
"""

from __future__ import annotations

import datetime as _dt
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DET = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "TibetTES_ADR_v4c_mkflange_cm.det"

VETO_THRESHOLD_KEV = 50.0  # matches make_complete_day15_report_ADR.py BGO_THR_KEV
MARKER = "# ===== Native MEGAlib TES-trigger + CsI anticoincidence veto ====="

CSI_THR_RE = re.compile(r"^(CsI_Active_Shield_\S+_SD)\.TriggerThreshold\s+\S+\s*$")


def main() -> int:
    if not DET.exists():
        print(f"[ERR] .det not found: {DET}", file=sys.stderr)
        return 2
    text = DET.read_text(encoding="utf-8")
    if MARKER in text:
        print("[SKIP] native veto trigger block already present; nothing to do.")
        return 0

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DET.with_suffix(DET.suffix + f".bak_native_veto_{stamp}")
    shutil.copy2(DET, backup)
    print(f"[OK] backup written: {backup.name}")

    lines = text.splitlines()
    out: list[str] = []
    segments: list[str] = []
    for line in lines:
        m = CSI_THR_RE.match(line.strip())
        if m:
            det_name = m.group(1)
            segments.append(det_name)
            # raise CsI segment threshold to the veto baseline and tie noise to it
            out.append(f"{det_name}.TriggerThreshold {VETO_THRESHOLD_KEV:.1f}")
            out.append(f"{det_name}.NoiseThresholdEqualsTriggerThreshold true")
        else:
            out.append(line)

    if not segments:
        print("[ERR] no CsI_Active_Shield_*_SD segments found; aborting.", file=sys.stderr)
        return 3

    block: list[str] = ["", MARKER]
    block.append("# Citable threshold-only veto model; quantitative veto stays in post-processing.")
    block.append("# Production .sim predate this trigger (full storage, no trigger) -> results unchanged.")
    block.append("# Re-run caveat: native per-segment 50 keV veto + NoiseThresholdEqualsTriggerThreshold")
    block.append("# changes the stored event population the post-processing accidental/summed-veto needs.")
    block.append("")
    block.append("# Main science trigger: any TES calorimeter layer (D1..D6) above its threshold.")
    block.append("Trigger TES_MainTrigger")
    block.append("TES_MainTrigger.Veto false")
    block.append("TES_MainTrigger.TriggerByChannel true")
    block.append("TES_MainTrigger.DetectorType Calorimeter 1")
    block.append("")
    block.append(f"# CsI anticoincidence: any CsI segment above {VETO_THRESHOLD_KEV:.0f} keV vetoes the event.")
    block.append("# One veto trigger per segment (logical OR); CsI shares the 'Scintillator' type with")
    block.append("# passive volumes, so DetectorType cannot be used here -- segments are listed explicitly.")
    for seg in segments:
        tname = "Veto_" + seg[:-3] if seg.endswith("_SD") else "Veto_" + seg
        block.append(f"Trigger {tname}")
        block.append(f"{tname}.Veto true")
        block.append(f"{tname}.TriggerByChannel true")
        block.append(f"{tname}.Detector {seg} 1")
    block.append("")

    new_text = "\n".join(out).rstrip("\n") + "\n" + "\n".join(block) + "\n"
    DET.write_text(new_text, encoding="utf-8")
    print(f"[OK] updated {DET.name}: 1 main TES trigger + {len(segments)} CsI veto triggers; "
          f"CsI threshold -> {VETO_THRESHOLD_KEV:.0f} keV (+NoiseThresholdEqualsTriggerThreshold).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
