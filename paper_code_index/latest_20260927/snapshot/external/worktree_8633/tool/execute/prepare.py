#!/usr/bin/env python3
"""Create and audit the 21 corrected-keV SG3B background source cards."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from common import (
    PACKAGE_ROOT,
    load_config,
    load_json,
    meminfo,
    sha256,
    utc_now,
    write_once_json,
    write_once_text,
)


FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
MODES = ("instant", "buildup")
SEED_META_WORDS = {
    "base", "stride", "count", "sha256", "digest", "hash", "policy",
    "rule", "formula", "status", "collision", "namespace", "ordinal",
}


def extract_seed_values(value: Any, *, context: bool = False) -> set[int]:
    result: set[int] = set()
    if isinstance(value, dict):
        for raw_key, child in value.items():
            words = set(str(raw_key).lower().replace("-", "_").split("_"))
            is_seed_key = bool({"seed", "seeds"} & words)
            is_meta = bool(words & SEED_META_WORDS)
            result.update(
                extract_seed_values(child, context=(context or is_seed_key) and not is_meta)
            )
    elif isinstance(value, list):
        for child in value:
            result.update(extract_seed_values(child, context=context))
    elif context and isinstance(value, int) and not isinstance(value, bool) and value > 0:
        result.add(value)
    return result


def referenced_json(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            result.update(referenced_json(child))
    elif isinstance(value, list):
        for child in value:
            result.update(referenced_json(child))
    elif isinstance(value, str) and value.endswith(".json"):
        result.add(value)
    return result


def resolve_authority(path_text: str, roots: list[Path]) -> Path | None:
    path = Path(path_text)
    candidates = [path] if path.is_absolute() else [root / path for root in roots]
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def occupied_seeds(config: dict[str, Any]) -> tuple[set[int], dict[str, Any]]:
    roots = [Path(item) for item in config["authority_roots"]]
    m05_path = Path(config["m05_analysis_inputs"])
    m05 = load_json(m05_path)
    queue: list[Path] = []
    for item in m05.get("transport_inputs", []):
        resolved = resolve_authority(str(item["path"]), roots)
        if resolved is None:
            raise FileNotFoundError(f"seed authority not found: {item['path']}")
        queue.append(resolved)
    seen: set[Path] = set()
    occupied: set[int] = set()
    total_json_bytes = 0
    while queue:
        path = queue.pop().resolve()
        if path in seen:
            continue
        size = path.stat().st_size
        if size > 20_000_000:
            raise RuntimeError(f"seed JSON is not a small authority: {path} ({size})")
        payload = load_json(path)
        seen.add(path)
        total_json_bytes += size
        occupied.update(extract_seed_values(payload))
        for reference in referenced_json(payload):
            resolved = resolve_authority(reference, roots)
            if resolved is not None and resolved not in seen:
                queue.append(resolved)
    csv_rows = 0
    csv_paths: list[str] = []
    for raw in config["seed_registry_csvs"]:
        path = Path(raw)
        if not path.is_file():
            raise FileNotFoundError(path)
        csv_paths.append(str(path))
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("seed"):
                    occupied.add(int(row["seed"]))
                    csv_rows += 1
    registry_json_rows = 0
    registry_json_paths: list[str] = []
    configured_registry_jsons = config.get("seed_registry_jsons", [])
    for raw in configured_registry_jsons:
        path = Path(raw)
        if not path.is_file():
            raise FileNotFoundError(path)
        size = path.stat().st_size
        if size > 20_000_000:
            raise RuntimeError(f"seed registry JSON is not a small authority: {path} ({size})")
        payload = load_json(path)
        rows = payload.get("seeds")
        if not isinstance(rows, list):
            raise RuntimeError(f"seed registry JSON lacks rows: {path}")
        for row in rows:
            seed = row.get("seed") if isinstance(row, dict) else None
            if not isinstance(seed, int) or seed <= 0:
                raise RuntimeError(f"invalid seed registry row: {path}")
            occupied.add(seed)
            registry_json_rows += 1
        registry_json_paths.append(str(path))
    audit = {
        "policy": "SMALL_JSON_AND_REGISTERED_CSV_ONLY__NO_SIM_ACCESS",
        "m05_analysis_inputs": str(m05_path),
        "json_authority_files": len(seen),
        "json_authority_bytes": total_json_bytes,
        "registry_csvs": csv_paths,
        "registry_rows": csv_rows,
        "occupied_seed_count": len(occupied),
    }
    if configured_registry_jsons:
        audit.update({
            "policy": "SMALL_JSON_AND_REGISTERED_CSV_JSON_ONLY__NO_SIM_ACCESS",
            "registry_jsons": registry_json_paths,
            "registry_json_rows": registry_json_rows,
        })
    return occupied, audit


def derive_seed(namespace: str, identity: str, occupied: set[int]) -> int:
    for probe in range(100_000):
        digest = hashlib.sha256(f"{namespace}\x1e{identity}\x1e{probe}".encode()).digest()
        candidate = 1 + int.from_bytes(digest[:8], "big") % 2_147_483_646
        if candidate not in occupied:
            occupied.add(candidate)
            return candidate
    raise RuntimeError(f"unable to derive a fresh seed for {identity}")


def unique_index(lines: list[str], predicate, label: str) -> int:
    matches = [index for index, line in enumerate(lines) if predicate(line)]
    if len(matches) != 1:
        raise RuntimeError(f"base source requires one {label}, found {len(matches)}")
    return matches[0]


def patch_source(
    base_text: str,
    *,
    setup: Path,
    output_prefix: Path,
    job_id: str,
    run_name: str,
    mode: str,
    seed: int,
    events: int,
    config: dict[str, Any],
) -> str:
    lines = base_text.splitlines()
    geometry_i = unique_index(lines, lambda x: x.strip().startswith("Geometry "), "Geometry")
    seed_i = unique_index(lines, lambda x: x.strip().startswith("Seed "), "Seed")
    run_i = unique_index(lines, lambda x: x.strip().startswith("Run "), "Run")
    decay_i = unique_index(lines, lambda x: x.strip().startswith("DecayMode "), "DecayMode")
    unique_index(lines, lambda x: x.strip() == "StoreSimulationInfo all", "StoreSimulationInfo")
    unique_index(lines, lambda x: x.strip() == "StoreIsotopes true", "StoreIsotopes")
    old_run = lines[run_i].strip().split(maxsplit=1)[1]
    scoped = [index for index, line in enumerate(lines) if line.startswith(f"{old_run}.")]
    if len(scoped) != 23:
        raise RuntimeError(f"unexpected run-scoped key count in {job_id}: {len(scoped)}")
    events_i = unique_index(lines, lambda x: x.startswith(f"{old_run}.Events "), "Events")
    filename_i = unique_index(lines, lambda x: x.startswith(f"{old_run}.FileName "), "FileName")
    isotope_i = unique_index(
        lines,
        lambda x: x.startswith(f"{old_run}.IsotopeProductionFile "),
        "IsotopeProductionFile",
    )
    patched: list[str] = []
    for index, raw in enumerate(lines):
        if index == geometry_i:
            patched.append(f"Geometry {setup}")
        elif index == seed_i:
            patched.append(f"Seed {seed}")
        elif index == run_i:
            patched.append(f"Run {run_name}")
        elif index == decay_i and mode == "instant":
            continue
        elif index == events_i:
            patched.append(f"{run_name}.Events {events}")
        elif index == filename_i:
            patched.append(f"{run_name}.FileName {output_prefix}")
        elif index == isotope_i:
            patched.append(f"{run_name}.IsotopeProductionFile {output_prefix}.dat")
        elif raw.startswith(f"{old_run}."):
            patched.append(run_name + raw[len(old_run):])
        else:
            patched.append(raw)
    result = "\n".join(patched) + "\n"
    validate_source(
        result,
        setup=setup,
        output_prefix=output_prefix,
        run_name=run_name,
        mode=mode,
        seed=seed,
        events=events,
        config=config,
    )
    return result


def validate_source(
    text: str,
    *,
    setup: Path,
    output_prefix: Path,
    run_name: str,
    mode: str,
    seed: int,
    events: int,
    config: dict[str, Any],
) -> None:
    lines = text.splitlines()
    exact = lambda value: sum(line.strip() == value for line in lines)
    required = {
        f"Geometry {setup}": 1,
        f"Seed {seed}": 1,
        f"Run {run_name}": 1,
        f"{run_name}.Events {events}": 1,
        f"{run_name}.FileName {output_prefix}": 1,
        f"{run_name}.IsotopeProductionFile {output_prefix}.dat": 1,
        "StoreSimulationInfo all": 1,
        "StoreIsotopes true": 1,
        "PhysicsListHD qgsp-bic-hp": 1,
        "PhysicsListEM LivermorePol": 1,
    }
    wrong = {key: exact(key) for key, wanted in required.items() if exact(key) != wanted}
    if wrong:
        raise RuntimeError(f"source contract mismatch: {wrong}")
    if exact("DecayMode ActivationBuildUp") != (1 if mode == "buildup" else 0):
        raise RuntimeError("DecayMode contract mismatch")
    if text.count(".Spectrum File ") != 20 or text.count(config["corrected_token"]) != 20:
        raise RuntimeError("corrected-keV 20-spectrum contract mismatch")
    if text.count(f"{run_name}.Source ") != 20 or text.count("Beam FarFieldAreaSource") != 20:
        raise RuntimeError("20-bin FarField source contract mismatch")
    if config["forbidden_legacy_token"] in text:
        raise RuntimeError("legacy factor-1000 spectrum token found")
    if "mono511" in text.lower() or "mono_511" in text.lower():
        raise RuntimeError("forbidden additive mono-511 marker found")


def authority_checks(config: dict[str, Any]) -> dict[str, Any]:
    setup = Path(config["geometry_setup"])
    if not setup.is_file():
        raise FileNotFoundError(setup)
    setup_lines = setup.read_text(encoding="utf-8").splitlines()
    if setup_lines.count("Name DEMO2_DR_v3p5_SG3B") != 1:
        raise RuntimeError("SG3B setup Name mismatch")
    include_paths: list[str] = []
    for line in setup_lines:
        if line.startswith("Include "):
            included = setup.parent / line.split(maxsplit=1)[1]
            if not included.is_file():
                raise FileNotFoundError(included)
            include_paths.append(str(included))
    audit_rows = []
    for raw in config["geometry_audits"]:
        path = Path(raw)
        payload = load_json(path)
        status = str(payload.get("status", ""))
        if not status.startswith("PASS"):
            raise RuntimeError(f"geometry audit is not PASS: {path}: {status}")
        audit_rows.append({"path": str(path), "status": status, "sha256": sha256(path)})
    contract_path = Path(config["source_contract"])
    contract = load_json(contract_path)
    if contract.get("energy_contract", {}).get("output_energy_unit") != "keV_total":
        raise RuntimeError("source contract is not keV_total")
    if set(contract.get("families", [])) != set(FAMILIES) or contract.get("bins_per_family") != 20:
        raise RuntimeError("source family/bin contract mismatch")
    geometry_contract = contract.get("geometries", {}).get("s3d_o8", {})
    contract_cards = geometry_contract.get("cards", [])
    expected_base_hashes = {
        str(row.get("family")): str(row.get("source_sha256"))
        for row in contract_cards
        if row.get("family") and row.get("source_sha256")
    }
    if set(expected_base_hashes) != set(FAMILIES):
        raise RuntimeError("source contract lacks the eight s3d_o8 base-card hashes")
    for family, expected in expected_base_hashes.items():
        base = Path(config["base_source_root"]) / f"Background_{family}_fullsphere20.source"
        if not base.is_file() or sha256(base) != expected:
            raise RuntimeError(f"s3d_o8 base source differs from source contract: {family}")
    m05_path = Path(config["m05_analysis_inputs"])
    m05 = load_json(m05_path)
    source = m05.get("source", {})
    if source.get("gamma_profile") != config["gamma_profile"]:
        raise RuntimeError("gamma profile mismatch")
    if bool(source.get("additive_mono511")) or config["additive_mono511"]:
        raise RuntimeError("additive mono-511 must remain disabled")
    return {
        "geometry_setup": str(setup),
        "geometry_setup_sha256": sha256(setup),
        "geometry_includes": include_paths,
        "geometry_audits": audit_rows,
        "source_contract": str(contract_path),
        "source_contract_sha256": sha256(contract_path),
        "m05_analysis_inputs": str(m05_path),
        "gamma_profile": source.get("gamma_profile"),
        "additive_mono511": source.get("additive_mono511"),
    }


def build_payloads(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    setup = Path(config["geometry_setup"])
    base_root = Path(config["base_source_root"])
    template = Path(config["statistics_template_csv"])
    generated = Path(config["generated_root"])
    run_root = Path(config["run_root"])
    with template.open(newline="", encoding="utf-8") as handle:
        template_rows = [row for row in csv.DictReader(handle) if row.get("stage") == "background"]
    multiplier = int(config.get("statistics_multiplier", 1))
    if multiplier < 1:
        raise RuntimeError("statistics_multiplier must be a positive integer")
    if len(template_rows) != config["expected_jobs"]:
        raise RuntimeError(f"expected {config['expected_jobs']} background jobs, found {len(template_rows)}")
    if multiplier * sum(int(row["events"]) for row in template_rows if row["mode"] == "instant") != config["expected_instant_histories"]:
        raise RuntimeError("instant history total mismatch")
    if multiplier * sum(int(row["events"]) for row in template_rows if row["mode"] == "buildup") != config["expected_buildup_histories"]:
        raise RuntimeError("buildup history total mismatch")
    occupied, seed_audit = occupied_seeds(config)
    jobs: list[dict[str, Any]] = []
    seeds: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    base_records: dict[str, dict[str, str]] = {}
    for raw in template_rows:
        mode = raw["mode"]
        family = raw["family"]
        shard = int(raw["shard"])
        events = multiplier * int(raw["events"])
        if mode not in MODES or family not in FAMILIES:
            raise RuntimeError(f"invalid statistics cell: {mode}/{family}")
        job_id = f"sg3b_{mode}_{family}_shard{shard:04d}"
        run_name = f"SG3B_{mode}_{family}_{shard:04d}"
        seed = derive_seed(config["profile_id"], job_id, occupied)
        source_path = generated / "sources" / f"{job_id}.source"
        output_prefix = run_root / "jobs" / job_id / "active" / job_id
        base_path = base_root / f"Background_{family}_fullsphere20.source"
        if not base_path.is_file():
            raise FileNotFoundError(base_path)
        source_text = patch_source(
            base_path.read_text(encoding="utf-8"),
            setup=setup,
            output_prefix=output_prefix,
            job_id=job_id,
            run_name=run_name,
            mode=mode,
            seed=seed,
            events=events,
            config=config,
        )
        sources[str(source_path)] = source_text
        base_records[family] = {"path": str(base_path), "sha256": sha256(base_path)}
        jobs.append({
            "ordinal": int(raw["ordinal"]),
            "job_id": job_id,
            "stage": "background",
            "candidate": "SG3B",
            "mode": mode,
            "family": family,
            "shard": shard,
            "events": events,
            "target_histories": multiplier * int(raw["target_histories"]),
            "seed": seed,
            "source_path": str(source_path),
            "setup_path": str(setup),
            "output_prefix": str(output_prefix),
            "estimated_bytes": multiplier * int(raw["estimated_bytes"]),
            "production_canary": job_id == config["canary_job_id"],
        })
        seeds.append({"job_id": job_id, "seed": seed, "namespace": config["profile_id"]})
    jobs.sort(key=lambda row: row["ordinal"])
    if sum(bool(row["production_canary"]) for row in jobs) != 1:
        raise RuntimeError("exactly one production canary is required")
    source_audit = {
        "statistics_template": str(template),
        "statistics_template_sha256": sha256(template),
        "base_sources": base_records,
        "seed_authority": seed_audit,
    }
    if "statistics_multiplier" in config:
        source_audit["statistics_multiplier"] = multiplier
    return jobs, seeds, sources, source_audit


def execute(*, write: bool, config_path: str | Path | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    authority = authority_checks(config)
    jobs, seeds, sources, source_audit = build_payloads(config)
    generated = Path(config["generated_root"])
    run_root = Path(config["run_root"])
    disk = shutil.disk_usage(PACKAGE_ROOT)
    memory = meminfo()
    if disk.free < int(config["start_free_bytes"]):
        raise RuntimeError(f"start-free gate failed: {disk.free} < {config['start_free_bytes']}")
    if memory["MemAvailable"] < int(config["launch_mem_available_bytes"]):
        raise RuntimeError("launch MemAvailable gate failed")
    if memory["SwapFree"] < int(config["launch_swap_free_bytes"]):
        raise RuntimeError("launch SwapFree gate failed")
    plan = {
        "schema_version": 1,
        "profile_id": config["profile_id"],
        "candidate": "SG3B",
        "status": "PASS",
        "scope": "CORRECTED_KEV_INSTANT_AND_BUILDUP_BACKGROUND_ONLY",
        "jobs": jobs,
        "totals": {
            "jobs": len(jobs),
            "instant_histories": sum(row["events"] for row in jobs if row["mode"] == "instant"),
            "buildup_histories": sum(row["events"] for row in jobs if row["mode"] == "buildup"),
        },
    }
    registry = {
        "schema_version": 1,
        "profile_id": config["profile_id"],
        "status": "PASS__FRESH_GLOBALLY_DISJOINT_SEEDS",
        "seeds": seeds,
        "authority": source_audit["seed_authority"],
    }
    manifest_rows = []
    for job in jobs:
        text = sources[job["source_path"]]
        manifest_rows.append({
            "job_id": job["job_id"],
            "mode": job["mode"],
            "family": job["family"],
            "events": job["events"],
            "seed": job["seed"],
            "source_path": job["source_path"],
            "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "setup_path": job["setup_path"],
        })
    manifest = {
        "schema_version": 1,
        "profile_id": config["profile_id"],
        "status": "PASS__SG3B_CORRECTED_BACKGROUND_SOURCES",
        "gamma_profile": config["gamma_profile"],
        "additive_mono511": False,
        "sources": manifest_rows,
        "authority": source_audit,
    }
    preflight = {
        "schema_version": 1,
        "profile_id": config["profile_id"],
        "status": "PASS__SG3B_BACKGROUND_TRANSPORT_PREFLIGHT",
        "checked_at": utc_now(),
        "candidate": "SG3B",
        "authority": authority,
        "job_plan": plan["totals"],
        "source_manifest_status": manifest["status"],
        "seed_registry_status": registry["status"],
        "workers": config["workers"],
        "resource_snapshot": {
            "disk_free_bytes": disk.free,
            "mem_available_bytes": memory["MemAvailable"],
            "swap_free_bytes": memory["SwapFree"],
        },
        "forbidden_work": "NO_DELAYED_SIGNAL_OR_PAPER_POSTPROCESS_IN_THIS_PACKAGE",
    }
    if write:
        for path_text, text in sources.items():
            write_once_text(Path(path_text), text)
        write_once_json(generated / "job_plan.json", plan)
        write_once_json(generated / "seed_registry.json", registry)
        write_once_json(generated / "source_manifest.json", manifest)
        write_once_json(generated / "preflight.json", preflight)
        run_root.mkdir(parents=True, exist_ok=True)
    else:
        expected = {
            generated / "job_plan.json": plan,
            generated / "seed_registry.json": registry,
            generated / "source_manifest.json": manifest,
        }
        for path, payload in expected.items():
            if load_json(path) != payload:
                raise RuntimeError(f"generated authority differs from recomputed content: {path}")
        stored_preflight = load_json(generated / "preflight.json")
        stable_keys = (
            "schema_version", "profile_id", "status", "candidate", "authority",
            "job_plan", "source_manifest_status", "seed_registry_status", "workers",
            "forbidden_work",
        )
        stored_stable = {key: stored_preflight.get(key) for key in stable_keys}
        expected_stable = {key: preflight.get(key) for key in stable_keys}
        if stored_stable != expected_stable:
            raise RuntimeError("generated preflight stable contract differs from recomputed content")
        for path_text, text in sources.items():
            if Path(path_text).read_text(encoding="utf-8") != text:
                raise RuntimeError(f"generated source differs: {path_text}")
    return preflight


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = execute(write=args.prepare, config_path=args.config)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
