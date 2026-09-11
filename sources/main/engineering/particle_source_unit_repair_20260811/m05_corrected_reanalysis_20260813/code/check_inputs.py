#!/usr/bin/env python3
"""Select the corrected-keV M05 inputs and publish a compact exposure audit.

This reader trusts each campaign's published ledger/receipt authority.  It does
not reopen SIM gzip payloads or recompute their artifact hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve()
DEFAULT_CONFIG = HERE.parent.parent / "analysis_inputs.json"


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = find_root(HERE.parent)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object: {path}")
    return value


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_geometry(raw: Any, config: dict[str, Any]) -> str:
    value = str(raw)
    return str(config["selection"]["geometry_aliases"].get(value, value))


def normalize_family(raw: Any, config: dict[str, Any]) -> str:
    value = str(raw)
    return str(config["selection"]["family_aliases"].get(value, value))


def campaign_jobs(
    ledger: dict[str, Any], input_id: str, config: dict[str, Any]
) -> Iterable[dict[str, Any]]:
    for campaign in ledger.get("campaigns", []):
        for job in campaign.get("jobs", []):
            yield {
                "input_id": input_id,
                "batch_id": str(ledger.get("batch_id", input_id)),
                "geometry": normalize_geometry(campaign.get("geometry"), config),
                "mode": str(campaign.get("mode")),
                "family": normalize_family(job.get("family", campaign.get("family")), config),
                "job_id": str(job.get("job_name")),
                "events": int(job.get("events")),
                "seed": int(job.get("seed")),
                "ordinal": job.get("ordinal"),
                "TT_s": float(
                    job.get(
                        "TT_s_from_isotope_dat",
                        campaign.get("TT_s_from_isotope_dat"),
                    )
                ),
                "sim_path": str(job.get("sim")),
                "sim_sha256": str(job.get("sim_sha256")),
                "geometry_header": str(job.get("ia_init", {}).get("geometry_header")),
            }


def receipt_jobs(
    ledger: dict[str, Any], input_id: str, path_key: str, config: dict[str, Any]
) -> Iterable[dict[str, Any]]:
    for selected in ledger.get("selected_receipts", []):
        receipt_path = repo_path(str(selected[path_key]))
        receipt = load_json(receipt_path)
        if receipt.get("status") != "PASS":
            raise RuntimeError(f"selected receipt is not PASS: {receipt_path}")
        job = receipt["job"]
        sim_path = str(Path(str(receipt["attempt_dir"])) / receipt["artifacts"]["sim"]["name"])
        yield {
            "input_id": input_id,
            "batch_id": input_id,
            "geometry": normalize_geometry(job.get("geometry"), config),
            "mode": str(job.get("mode")),
            "family": normalize_family(job.get("family"), config),
            "job_id": str(job.get("job_id")),
            "events": int(job.get("events")),
            "seed": int(job.get("seed")),
            "ordinal": job.get("shard_ordinal"),
            "TT_s": float(receipt["isotope_dat"]["TT_s"]),
            "sim_path": sim_path,
            "sim_sha256": str(receipt["artifacts"]["sim"]["sha256"]),
            "geometry_header": str(receipt["sim"]["geometry_header"]),
            "receipt_path": str(receipt_path),
        }


def selected_jobs(
    ledger: dict[str, Any], entry: dict[str, Any], config: dict[str, Any]
) -> list[dict[str, Any]]:
    selector = entry["selector"]
    if selector == "campaign_jobs":
        return list(campaign_jobs(ledger, entry["id"], config))
    if selector == "selected_receipts_path":
        return list(receipt_jobs(ledger, entry["id"], "path", config))
    if selector == "selected_receipts_receipt":
        return list(receipt_jobs(ledger, entry["id"], "receipt", config))
    raise RuntimeError(f"unknown selector: {selector}")


def pair(jobs: int, histories: int) -> dict[str, int]:
    return {"jobs": jobs, "histories": histories}


def check_source(config: dict[str, Any]) -> dict[str, Any]:
    source = config["source"]
    contract_path = repo_path(source["contract_path"])
    if sha256(contract_path) != source["contract_sha256"]:
        raise RuntimeError("corrected source contract hash differs")
    contract = load_json(contract_path)
    static = load_json(repo_path(source["static_validation_path"]))
    if static.get("status") != source["required_static_status"]:
        raise RuntimeError("corrected source static validation is not PASS")
    if static["source_packages"]["legacy_references"] != 0:
        raise RuntimeError("corrected source validation reports legacy references")
    if contract["energy_contract"]["output_energy_unit"] != source["energy_unit"]:
        raise RuntimeError("corrected source energy unit differs")
    if contract["source_model"]["profile"] != source["gamma_profile"]:
        raise RuntimeError("gamma source profile differs")
    if contract["policies"]["additive_mono_511_allowed"] != source["additive_mono511"]:
        raise RuntimeError("mono-511 composition policy differs")
    return {
        "contract_path": source["contract_path"],
        "contract_sha256": source["contract_sha256"],
        "static_validation_path": source["static_validation_path"],
        "gamma_profile": source["gamma_profile"],
        "additive_mono511": source["additive_mono511"],
    }


def check_geometry_contract(config: dict[str, Any]) -> None:
    for geometry, values in config["geometries"].items():
        if not repo_path(values["setup"]).is_file():
            raise RuntimeError(f"geometry setup is missing: {geometry}")
        volumes = values["active_veto_volumes"]
        if len(volumes) != values["expected_active_veto_count"] or len(volumes) != len(set(volumes)):
            raise RuntimeError(f"active-veto volume list differs: {geometry}")
    for key in ("response", "compton_fov"):
        if not repo_path(config["analysis"][key]["implementation"]).is_file():
            raise RuntimeError(f"reused implementation is missing: {key}")


def build_report(config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    source = check_source(config)
    check_geometry_contract(config)
    allowed_geometries = set(config["selection"]["geometries"])
    allowed_modes = set(config["selection"]["modes"])
    allowed_families = set(config["selection"]["families"])

    all_jobs: list[dict[str, Any]] = []
    input_rows: list[dict[str, Any]] = []
    for entry in config["transport_inputs"]:
        ledger_path = repo_path(entry["path"])
        ledger = load_json(ledger_path)
        if ledger.get("status") != entry["required_status"]:
            raise RuntimeError(f"ledger status differs: {entry['id']}")
        jobs = selected_jobs(ledger, entry, config)
        histories = sum(job["events"] for job in jobs)
        if pair(len(jobs), histories) != pair(entry["expected_jobs"], entry["expected_histories"]):
            raise RuntimeError(f"selected exposure differs: {entry['id']}")
        input_rows.append({
            "id": entry["id"],
            "path": entry["path"],
            "status": ledger["status"],
            "jobs": len(jobs),
            "histories": histories,
            "scope": entry["scope"],
        })
        all_jobs.extend(jobs)

    seen_sim: set[str] = set()
    by_mode: dict[str, dict[str, int]] = defaultdict(lambda: {"jobs": 0, "histories": 0})
    by_geometry: dict[str, dict[str, int]] = defaultdict(lambda: {"jobs": 0, "histories": 0})
    by_cell: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"jobs": 0, "histories": 0, "TT_s": 0.0}
    )
    for job in all_jobs:
        if job["geometry"] not in allowed_geometries:
            raise RuntimeError(f"unexpected geometry: {job['geometry']}")
        if job["mode"] not in allowed_modes:
            raise RuntimeError(f"unexpected mode: {job['mode']}")
        if job["family"] not in allowed_families:
            raise RuntimeError(f"unexpected family: {job['family']}")
        if job["TT_s"] <= 0:
            raise RuntimeError(f"non-positive TT: {job['job_id']}")
        if job["sim_path"] in seen_sim:
            raise RuntimeError(f"simulation selected twice: {job['sim_path']}")
        seen_sim.add(job["sim_path"])
        by_mode[job["mode"]]["jobs"] += 1
        by_mode[job["mode"]]["histories"] += job["events"]
        by_geometry[job["geometry"]]["jobs"] += 1
        by_geometry[job["geometry"]]["histories"] += job["events"]
        cell = f"{job['geometry']}|{job['mode']}|{job['family']}"
        by_cell[cell]["jobs"] += 1
        by_cell[cell]["histories"] += job["events"]
        by_cell[cell]["TT_s"] += job["TT_s"]

    totals = pair(len(all_jobs), sum(job["events"] for job in all_jobs))
    expected = config["expected_selection_summary"]
    if totals != expected["totals"]:
        raise RuntimeError("total selected exposure differs")
    if dict(by_mode) != expected["by_mode"]:
        raise RuntimeError("mode exposure summary differs")
    if dict(by_geometry) != expected["by_geometry"]:
        raise RuntimeError("geometry exposure summary differs")

    cells = {
        key: {
            "jobs": int(value["jobs"]),
            "histories": int(value["histories"]),
            "TT_s": round(float(value["TT_s"]), 12),
        }
        for key, value in sorted(by_cell.items())
    }
    return {
        "schema_version": 1,
        "status": "PASS__M05_CORRECTED_INPUTS_READY",
        "authority_boundary": config["authority_boundary"],
        "config": str(config_path.resolve().relative_to(ROOT)),
        "source": source,
        "transport_inputs": input_rows,
        "selection_summary": {
            "totals": totals,
            "by_mode": dict(sorted(by_mode.items())),
            "by_geometry": dict(sorted(by_geometry.items())),
            "by_geometry_mode_family": cells,
        },
        "checks": [
            "corrected source contract identity and static PASS",
            "unit_only_total_gamma with no additive mono-511",
            "canonical ledger terminal status",
            "geometry/mode/family selection boundary",
            "positive TT and no duplicate SIM selection",
            "exact active-veto volume lists",
        ],
        "not_checked": [
            "SIM gzip payload reopening",
            "large-artifact hash recomputation",
            "detector-response physics",
            "delayed or mission closure",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = load_json(config_path)
    report = build_report(config, config_path)
    if args.write:
        output = repo_path(config["outputs"]["input_audit"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(output.resolve().relative_to(ROOT))
    totals = report["selection_summary"]["totals"]
    print(f"{report['status']}: {totals['jobs']} jobs, {totals['histories']} histories")


if __name__ == "__main__":
    main()
