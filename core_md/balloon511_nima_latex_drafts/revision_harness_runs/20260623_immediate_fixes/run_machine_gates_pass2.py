#!/usr/bin/env python3
"""Run immediate-fixes harness machine gates G1-G5 for pass 2."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
HARNESS = Path(__file__).resolve().parent

JSON_PATHS = [
    Path("core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.json"),
    Path("core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json"),
    Path("core_md/balloon511_nima_latex_drafts/simulation_config_authority_20260623.json"),
    Path("core_md/balloon511_nima_latex_drafts/figures_audit_20260623.json"),
    Path("outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.as_posix()


def load_jsons(errors: list[str]) -> dict[str, object]:
    data: dict[str, object] = {}
    for path in JSON_PATHS:
        try:
            with (ROOT / path).open("r", encoding="utf-8") as f:
                data[rel(path)] = json.load(f)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path}: {exc}")
    return data


def require_keys(obj: object, keys: list[str], where: str, errors: list[str]) -> None:
    if not isinstance(obj, dict):
        errors.append(f"{where}: expected object")
        return
    for key in keys:
        if key not in obj:
            errors.append(f"{where}: missing key {key}")


def gate_g2(data: dict[str, object]) -> list[str]:
    errors: list[str] = []
    allowed_manifest_status = {"current", "archived", "stale", "UNKNOWN", "TO_RECOVER"}

    manifest = data.get(rel(JSON_PATHS[0]))
    require_keys(manifest, ["artifact_type", "created_utc", "scope", "entries"], "paper_evidence_manifest", errors)
    if isinstance(manifest, dict):
        for i, entry in enumerate(manifest.get("entries", [])):
            require_keys(
                entry,
                ["id", "value", "units", "source_path", "source_locator", "status", "used_by_manuscript", "notes"],
                f"paper_evidence_manifest.entries[{i}]",
                errors,
            )
            if isinstance(entry, dict) and entry.get("status") not in allowed_manifest_status:
                errors.append(f"paper_evidence_manifest.entries[{i}]: bad status {entry.get('status')!r}")

    norm = data.get(rel(JSON_PATHS[1]))
    require_keys(
        norm,
        [
            "artifact_type",
            "created_utc",
            "source_classes",
            "equations",
            "unit_checks",
            "source_plane",
            "parma_expacs_inputs",
            "megalib_cards",
            "sanity_checks",
            "linked_manuscript_quantities",
        ],
        "source_normalization_audit",
        errors,
    )

    config = data.get(rel(JSON_PATHS[2]))
    require_keys(config, ["artifact_type", "created_utc", "components"], "simulation_config_authority", errors)
    if isinstance(config, dict):
        for i, component in enumerate(config.get("components", [])):
            require_keys(component, ["name", "value", "source", "source_locator", "status"], f"simulation_config.components[{i}]", errors)

    delayed = data.get(rel(JSON_PATHS[4]))
    require_keys(delayed, ["artifact_type", "created_utc", "runs", "combined", "between_sampling_check", "verdict"], "delayed_selected_rate_convergence", errors)
    if isinstance(delayed, dict):
        for i, run in enumerate(delayed.get("runs", [])):
            require_keys(
                run,
                [
                    "run_id",
                    "generated_decays",
                    "selected_events",
                    "selected_rate_cps",
                    "uncertainty_cps",
                    "relative_uncertainty",
                    "source_activity_Bq",
                    "sampling_id",
                    "seed_or_tag",
                    "geometry_path",
                    "source_card_path",
                    "sim_header_geometry_path",
                    "command",
                    "output_path",
                ],
                f"delayed.runs[{i}]",
                errors,
            )

    figures = data.get(rel(JSON_PATHS[3]))
    require_keys(figures, ["artifact_type", "created_utc", "figures"], "figures_audit", errors)
    if isinstance(figures, dict):
        for i, fig in enumerate(figures.get("figures", [])):
            require_keys(
                fig,
                [
                    "figure_path",
                    "source_data_path",
                    "generation_script",
                    "command",
                    "reproduced_this_run",
                    "visual_qa_status",
                    "physical_data_changed",
                    "remaining_action",
                ],
                f"figures[{i}]",
                errors,
            )
    return errors


def parse_baseline_snapshot() -> dict[str, tuple[str, int, int]]:
    baseline = HARNESS / "00_git_baseline.txt"
    rows: dict[str, tuple[str, int, int]] = {}
    in_snapshot = False
    for raw in baseline.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "## frozen_path_file_snapshot":
            in_snapshot = True
            continue
        if not in_snapshot or not line or line.startswith("#") or line.startswith("Format:"):
            continue
        parts = line.split(maxsplit=3)
        if len(parts) == 4 and len(parts[0]) == 64:
            rows[parts[3]] = (parts[0], int(parts[1]), int(parts[2]))
    return rows


def gate_g3() -> dict[str, object]:
    errors: list[str] = []
    rows = parse_baseline_snapshot()
    for path_s, (expected_hash, expected_size, expected_mtime) in rows.items():
        path = ROOT / path_s
        if not path.exists():
            errors.append(f"{path_s}: missing")
            continue
        st = path.stat()
        actual_hash = sha256(path)
        if actual_hash != expected_hash or st.st_size != expected_size or st.st_mtime_ns != expected_mtime:
            errors.append(
                f"{path_s}: expected {expected_hash}/{expected_size}/{expected_mtime}, "
                f"got {actual_hash}/{st.st_size}/{st.st_mtime_ns}"
            )
    return {
        "status": "PASS" if not errors else "FAIL",
        "checked_file_count": len(rows),
        "errors": errors,
        "error_count": len(errors),
    }


def gate_g4(manifest: object) -> dict[str, object]:
    errors: list[str] = []
    checked_paths: set[str] = set()
    checked_entries = 0
    if not isinstance(manifest, dict):
        return {"status": "FAIL", "checked_entries": 0, "checked_paths": [], "errors": ["manifest not object"]}
    for i, entry in enumerate(manifest.get("entries", [])):
        checked_entries += 1
        if not isinstance(entry, dict):
            errors.append(f"entry {i}: not object")
            continue
        if not entry.get("source_path"):
            errors.append(f"entry {i}: missing source_path")
        if not (entry.get("source_locator") or entry.get("json_pointer")):
            errors.append(f"entry {i}: missing source_locator/json_pointer")
        for key in ("source_path", "supporting_source_path"):
            value = entry.get(key)
            if isinstance(value, str) and value not in {"UNKNOWN", "TO_RECOVER"}:
                checked_paths.add(value)
                if not (ROOT / value).exists():
                    errors.append(f"entry {i}: {key} missing on disk: {value}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "checked_entries": checked_entries,
        "checked_paths": sorted(checked_paths),
        "errors": errors,
    }


def git_hash_object(path: str) -> str:
    out = subprocess.check_output(["git", "hash-object", path], cwd=ROOT, text=True)
    return out.strip()


def gate_g5() -> dict[str, object]:
    expected = {
        "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex": "ba58d38c668998b39aaf8657fd90b8c0aa6f690c",
        "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex": "2673308ed29c3d50e3329cfe038e862123d2c52f",
        "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md": "be3cc8eb3a4b8025aec3e1a535f7ea9aa1e3cbb0e735dc5a47c380cfee7c62c6",
    }
    errors: list[str] = []
    for path, want in expected.items():
        got = sha256(ROOT / path) if path.endswith(".md") else git_hash_object(path)
        if got != want:
            errors.append(f"{path}: expected {want}, got {got}")
    return {"status": "PASS" if not errors else "FAIL", "checked_paths": sorted(expected), "errors": errors}


def main() -> int:
    g1_errors: list[str] = []
    data = load_jsons(g1_errors)
    g2_errors = gate_g2(data)
    g3 = gate_g3()
    g4 = gate_g4(data.get(rel(JSON_PATHS[0])))
    g5 = gate_g5()
    gates = {
        "G1_json_parse": {"status": "PASS" if not g1_errors else "FAIL", "errors": g1_errors},
        "G2_schema_keys": {"status": "PASS" if not g2_errors else "FAIL", "errors": g2_errors},
        "G3_no_overwrite_resolved_frozen_paths": g3,
        "G4_provenance_rows": g4,
        "G5_manuscript_frozen": g5,
    }
    overall = "PASS" if all(g["status"] == "PASS" for g in gates.values()) else "FAIL"
    result = {
        "artifact_type": "machine_gate_results",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Executor-side pass2 G1-G5 validation after PI-02 convergence closure.",
        "json_paths_checked": [rel(p) for p in JSON_PATHS],
        "gates": gates,
        "overall_status": overall,
    }
    (HARNESS / "03_machine_gate_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 03 Machine Gate Results",
        "",
        f"Created UTC: {result['created_utc']}",
        "",
        f"Overall: `{overall}`",
        "",
        "| Gate | Status | Detail |",
        "|---|---|---|",
    ]
    lines.append(f"| `G1_json_parse` | `{gates['G1_json_parse']['status']}` | errors {len(g1_errors)} |")
    lines.append(f"| `G2_schema_keys` | `{gates['G2_schema_keys']['status']}` | errors {len(g2_errors)} |")
    lines.append(f"| `G3_no_overwrite_resolved_frozen_paths` | `{g3['status']}` | checked {g3['checked_file_count']} frozen files; errors {g3['error_count']} |")
    lines.append(f"| `G4_provenance_rows` | `{g4['status']}` | checked {g4['checked_entries']} evidence entries and {len(g4['checked_paths'])} source/support paths |")
    lines.append(f"| `G5_manuscript_frozen` | `{g5['status']}` | {', '.join(g5['checked_paths'])} |")
    (HARNESS / "03_machine_gate_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"overall_status": overall, "gates": {k: v["status"] for k, v in gates.items()}}, indent=2))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
