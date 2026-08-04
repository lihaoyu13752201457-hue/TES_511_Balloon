#!/usr/bin/env python3
"""Pure validator for the S3c thinning audit contract gates."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"
CONTRACT_SHA256 = "2781e05d1d4a63c45e51236e376af75c5e75e2fefe4a9b0d86bc0fbded0661b1"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def gate(severity: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"severity": severity, "pass": bool(passed), "detail": detail}


def validate() -> dict[str, Any]:
    required = [
        WORK / "TASK_CONTRACT.md",
        WORK / "README.md",
        WORK / "code/run_audit.py",
        WORK / "code/validate_audit.py",
        DATA / "depth_profile.csv",
        DATA / "thinning_leak_table.csv",
        DATA / "panel_importance.csv",
        DATA / "pareto_options.csv",
        DATA / "summary.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        return {"deliverables_pass": False, "missing": missing, "gates": {}}

    summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    leak_rows = read_csv(DATA / "thinning_leak_table.csv")
    pareto_rows = read_csv(DATA / "pareto_options.csv")
    importance_rows = read_csv(DATA / "panel_importance.csv")
    depth_rows = read_csv(DATA / "depth_profile.csv")
    readme = (WORK / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()

    reproduction = summary["mass_model"]["bgo_reproduction"]
    mass_ok = len(reproduction) == 3 and all(float(item["relative_error"]) <= 0.01 for item in reproduction.values())
    w_al = [panel for panel in summary["geometry"]["panels"] if panel["material"] in {"W", "Aluminium"}]
    extents_ok = len(w_al) == 6 and all(
        float(panel["rmax"]) > float(panel["rmin"]) and float(panel["zmax"]) > float(panel["zmin"])
        for panel in w_al
    )
    g1 = gate("FAIL", mass_ok and extents_ok, "three BGO masses within 1%; six nondegenerate W/Al extents")

    identities = []
    for row in leak_rows:
        passthrough = int(row["passthrough_c0"])
        vetoed = int(row["vetoed_c0"])
        new = int(row["new_leak"])
        still = int(row["still_vetoed"])
        leak = int(row["leak"])
        identities.append(leak == passthrough + new and new + still == vetoed)
    g2 = gate("FAIL", len(leak_rows) == 10 and all(identities), "10 options conserve both exact integer identities")

    mu = float(summary["depth_fit"]["mu_eff_cm-1"])
    g3 = gate("WARN", math.isfinite(mu) and 0.80 <= mu <= 1.10, f"mu_eff={mu:.8g} cm^-1")

    shift_ratio = float(summary["calibration"]["shift_ratio"])
    g4 = gate("WARN", math.isfinite(shift_ratio) and shift_ratio <= 3.0, f"O1/LW1 shift ratio={shift_ratio:.8g}")

    status_proc = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True
    )
    status_lines = [line for line in status_proc.stdout.splitlines() if line]
    outside = [line for line in status_lines if "41_s3c_bgo_thinning_volume_audit_20260711" not in line]
    g5 = gate("FAIL", not outside, f"outside-41 git-status entries={len(outside)}")

    nonempty = [line for line in lines if line.strip()]
    status_first = len(nonempty) >= 2 and nonempty[0].startswith("# ") and nonempty[1].startswith("Status: `")
    answer_block = readme.split("## Answers", 1)[1].split("## Option table", 1)[0] if "## Answers" in readme else ""
    numbered_answers = [line for line in answer_block.splitlines() if line.startswith(("1. ", "2. "))]
    answers_quoted = len(numbered_answers) == 2 and all("Sources:" in line and "`" in line for line in numbered_answers)
    table_quoted = "All numbers below are sourced from `data/pareto_options.csv`" in readme
    required_sections = all(section in readme for section in ("## Gaps", "## Non-claims", "## Method limits"))
    g6 = gate(
        "FAIL",
        status_first and answers_quoted and table_quoted and required_sections,
        "status first; both headline answers and option table carry source paths; required sections present",
    )

    contract_hash = hashlib.sha256((WORK / "TASK_CONTRACT.md").read_bytes()).hexdigest()
    content_checks = {
        "contract_unmodified": contract_hash == CONTRACT_SHA256,
        "pareto_options": len(pareto_rows) == 10,
        "panel_importance_rows": len(importance_rows) == 5,
        "depth_profile_nonempty": bool(depth_rows),
        "method_limits_verbatim": all(
            phrase in readme
            for phrase in (
                "coupling drops secondary particles that interactions in the removed slab would have produced (biases leak LOW)",
                "some newly leaked photons would scatter in remaining material and miss W2 anyway (biases leak HIGH)",
                "e+/n/residual components are held flat at the frozen budget — thinning effects on them are NOT modeled here and require the 40_ run-matrix screening transport",
            )
        ),
        "nonclaims_verbatim": all(
            phrase in readme
            for phrase in (
                "Screening arithmetic on frozen budgets; NOT a full S3c prompt-family or Step05–08 closure; NOT structural qualification; no promotion decision.",
                "atm511 absolute normalization inherits the unresolved Harris-vs-4π-sidecar calibration; ratios reported here are internal to the 4π sidecar and do not resolve it.",
                "The 6-event W2 atm511 anchor carries ±41% (1σ) counting error which dominates every predicted_atm511_w2_cps; print this next to the table.",
            )
        ),
    }
    gates = {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6}
    failed = [name for name, result in gates.items() if result["severity"] == "FAIL" and not result["pass"]]
    warnings = [name for name, result in gates.items() if result["severity"] == "WARN" and not result["pass"]]
    expected_status = "PASS_S3C_THINNING_VOLUME_AUDIT" if not failed else f"FAIL_S3C_THINNING_AUDIT_{failed[0]}"
    readme_status_match = f"Status: `{expected_status}`" in readme
    return {
        "deliverables_pass": not missing,
        "content_checks": content_checks,
        "gates": gates,
        "failed_gates": failed,
        "warning_gates": warnings,
        "expected_status": expected_status,
        "readme_status_match": readme_status_match,
        "overall_pass": not failed and all(content_checks.values()) and readme_status_match,
        "git_status_outside_41": outside,
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("overall_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
