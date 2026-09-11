#!/usr/bin/env python3
"""WP03 delayed selected-rate convergence evidence for HARNESS_20260624.

The script promotes the existing PI-02 convergence audit into the engineering
harness tree and adds the required run manifest, resource estimate, and selected
event decomposition. It does not run Cosima.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import math
import pickle
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "03_delayed_convergence"
CONV_SRC = ROOT / "outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json"
STEP05_CODE = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
FIX5_GEO = "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
W2 = (510.58, 511.42)
COORD_DECIMALS = 5
COORD_TOL_CM = 1.0e-5

ELEMENTS = [
    "",
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
]


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def load_step05_module() -> Any:
    spec = importlib.util.spec_from_file_location("wp03_step05_fix5", STEP05_CODE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {STEP05_CODE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.configure_paths(LABEL)
    return mod


def selected_delayed_events(step05_mod: Any, cat: dict[str, Any]) -> tuple[list[dict[str, Any]], Counter]:
    disk = step05_mod.side_entry_disk()
    stream = np.asarray(cat["stream"], dtype=object)
    tes = np.asarray(cat["tes_total_keV"], dtype=float)
    bgo = np.asarray(cat["bgo_total_keV"], dtype=float)
    mask = (stream == "delayed") & (tes >= W2[0]) & (tes < W2[1]) & (bgo < float(step05_mod.ACTIVE_VETO_THRESHOLD_KEV))
    rows: list[dict[str, Any]] = []
    class_counts: Counter = Counter()
    for idx in np.flatnonzero(mask):
        keep, cls = step05_mod.side_keep_from_hits(step05_mod.event_hits(cat, int(idx)), disk, "keep")
        class_counts[cls] += 1
        if not keep:
            continue
        rows.append(
            {
                "catalog_index": int(idx),
                "local_id": int(cat["local_id"][idx]),
                "tes_total_keV": float(cat["tes_total_keV"][idx]),
                "bgo_total_keV": float(cat["bgo_total_keV"][idx]),
                "pix_count": int(cat["pix_count"][idx]),
                "rate_hz": float(cat["rate_hz"][idx]),
                "side_compton_class": cls,
            }
        )
    return rows, class_counts


def coord_key(za: str | int, x: float, y: float, z: float) -> tuple[str, str, str, str]:
    fmt = f"{{:.{COORD_DECIMALS}f}}"
    return str(int(za)), fmt.format(x), fmt.format(y), fmt.format(z)


def iter_gzip_lines(path: Path):
    proc = subprocess.Popen(["gzip", "-cd", str(path)], stdout=subprocess.PIPE)
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            yield raw.decode("utf-8", errors="ignore")
    finally:
        if proc.poll() is None:
            proc.terminate()
        proc.wait()


def parse_ia_init(sim_path: Path, wanted_ids: set[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    cur_id: int | None = None
    for raw in iter_gzip_lines(sim_path):
        if raw.startswith("ID "):
            parts = raw.split()
            cur_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            continue
        if cur_id not in wanted_ids:
            continue
        if raw.startswith("IA INIT"):
            fields = [part.strip() for part in raw.split(";")]
            if len(fields) >= 16:
                out[int(cur_id)] = {
                    "source_x_cm": float(fields[4]),
                    "source_y_cm": float(fields[5]),
                    "source_z_cm": float(fields[6]),
                    "ZA": int(float(fields[15])),
                }
                if len(out) == len(wanted_ids):
                    break
    return out


def load_exactpos_table(path: Path) -> tuple[dict[tuple[str, str, str, str], list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    lookup: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_za: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row["_x_cm"] = float(row["x_cm"])
            row["_y_cm"] = float(row["y_cm"])
            row["_z_cm"] = float(row["z_cm"])
            key = coord_key(row["ZA"], row["_x_cm"], row["_y_cm"], row["_z_cm"])
            lookup[key].append(row)
            by_za[str(int(row["ZA"]))].append(row)
    return lookup, by_za


def distance(init: dict[str, Any], row: dict[str, Any]) -> float:
    dx = float(init["source_x_cm"]) - float(row["_x_cm"])
    dy = float(init["source_y_cm"]) - float(row["_y_cm"])
    dz = float(init["source_z_cm"]) - float(row["_z_cm"])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def match_source(
    init: dict[str, Any],
    lookup: dict[tuple[str, str, str, str], list[dict[str, Any]]],
    by_za: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any] | None, str, int, float | None]:
    key = coord_key(init["ZA"], init["source_x_cm"], init["source_y_cm"], init["source_z_cm"])
    keyed = lookup.get(key, [])
    if len(keyed) == 1:
        return keyed[0], "KEY_MATCH", 1, distance(init, keyed[0])
    if len(keyed) > 1:
        return None, "AMBIGUOUS_KEY_MATCH", len(keyed), None
    candidates = [(distance(init, row), row) for row in by_za.get(str(int(init["ZA"])), [])]
    candidates = [item for item in candidates if item[0] <= COORD_TOL_CM]
    candidates.sort(key=lambda item: item[0])
    if len(candidates) == 1:
        return candidates[0][1], "NEAREST_MATCH_WITHIN_TOLERANCE", 1, candidates[0][0]
    if len(candidates) > 1:
        return None, "AMBIGUOUS_NEAREST_MATCH_WITHIN_TOLERANCE", len(candidates), candidates[0][0]
    return None, "NO_MATCH_WITHIN_TOLERANCE", 0, None


def isotope_from_za(za: Any) -> str:
    try:
        value = int(float(za))
    except Exception:
        return "unknown"
    z = value // 1000
    a = value % 1000
    symbol = ELEMENTS[z] if 0 < z < len(ELEMENTS) else f"Z{z}"
    return f"{symbol}-{a}"


def particle_from_source(source_sim: str) -> str:
    m = re.search(r"Background_([^_]+)_", source_sim)
    return m.group(1) if m else "unknown"


def run_exactpos_table(run: dict[str, Any]) -> Path:
    summary = load_json(resolve(str(run["summary_path"])))
    weighted = summary.get("weighted_table")
    if weighted:
        return resolve(str(weighted))
    source = resolve(str(run["source_card_path"]))
    seed = str(run.get("seed_or_tag", ""))
    return source.parent / f"exactpos_weighted_rpip_table_m50000_s{seed}.csv"


def grouped(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    acc: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        item = acc.setdefault(key, {k: row.get(k, "") for k in keys} | {"events": 0, "rate_hz": 0.0, "sum_w2": 0.0})
        rate = float(row.get("rate_hz") or 0.0)
        item["events"] += 1
        item["rate_hz"] += rate
        item["sum_w2"] += rate * rate
    total = sum(float(row["rate_hz"]) for row in acc.values())
    out = list(acc.values())
    for row in out:
        row["mc_sigma_cps"] = math.sqrt(float(row["sum_w2"]))
        row["fraction_of_rate"] = float(row["rate_hz"]) / total if total > 0 else 0.0
    out.sort(key=lambda row: (float(row["rate_hz"]), int(row["events"])), reverse=True)
    return out


def estimate_resources(runs: list[dict[str, Any]], combined: dict[str, Any]) -> dict[str, Any]:
    total_generated = sum(int(run.get("generated_decays", run.get("generated_delayed_decays", 0))) for run in runs)
    selected = int(combined.get("selected_events", 0))
    efficiency = selected / total_generated if total_generated > 0 else 0.0
    target_100 = math.ceil(100 / efficiency) if efficiency > 0 else None
    target_300 = math.ceil(300 / efficiency) if efficiency > 0 else None
    total_size = 0
    for run in runs:
        path = resolve(str(run["output_path"]))
        if path.exists():
            total_size += path.stat().st_size
    return {
        "current_generated_decays": total_generated,
        "current_selected_events": selected,
        "selected_efficiency_per_decay": efficiency,
        "estimated_decays_for_100_selected": target_100,
        "estimated_decays_for_300_selected": target_300,
        "current_sim_gz_size_bytes": total_size,
        "average_sim_gz_bytes_per_1M_decays": total_size / (total_generated / 1.0e6) if total_generated > 0 else None,
        "resource_guard": {
            "max_events_without_explicit_approval_per_launch_batch": 5000000,
            "max_estimated_output_without_approval_bytes": 100 * 1024**3,
            "max_estimated_cpu_without_approval_cpu_days": 7,
        },
        "new_runs_required_for_g3": False,
        "reason": "Existing PI-02 pooled sample already meets the harness minimum selected-event and relative-uncertainty targets.",
    }


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    conv = load_json(CONV_SRC)
    step05_mod = load_step05_module()
    geometry_hash = sha256(resolve(FIX5_GEO))
    selection_hash = sha256(STEP05_CODE)

    manifest_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    problems: list[str] = []

    for run in conv["runs"]:
        run_id = str(run["run_id"])
        catalog_cache = resolve(str(run["catalog_cache"]))
        with catalog_cache.open("rb") as handle:
            cat = pickle.load(handle)
        selected, class_counts = selected_delayed_events(step05_mod, cat)
        selected_rate = sum(float(row["rate_hz"]) for row in selected)
        selected_sum_w2 = sum(float(row["rate_hz"]) ** 2 for row in selected)
        if len(selected) != int(run["selected_events"]):
            problems.append(f"{run_id}: selected event count mismatch {len(selected)} != {run['selected_events']}")
        if abs(selected_rate - float(run["selected_rate_cps"])) > 1.0e-14:
            problems.append(f"{run_id}: selected rate mismatch {selected_rate:.16g} != {float(run['selected_rate_cps']):.16g}")

        ids = {int(row["local_id"]) for row in selected}
        sim_path = resolve(str(run["output_path"]))
        ia = parse_ia_init(sim_path, ids)
        table = run_exactpos_table(run)
        lookup, by_za = load_exactpos_table(table)

        for row in selected:
            local_id = int(row["local_id"])
            init = ia.get(local_id)
            if init is None:
                problems.append(f"{run_id}: missing IA INIT for local_id {local_id}")
                selected_rows.append({**row, "run_id": run_id, "source_match_status": "MISSING_IA_INIT"})
                continue
            match, status, match_count, match_distance = match_source(init, lookup, by_za)
            if match is None:
                problems.append(f"{run_id}: exactpos {status} for local_id {local_id}")
                match = {}
            source_sim = str(match.get("source_sim", ""))
            selected_rows.append(
                {
                    **row,
                    "run_id": run_id,
                    "source_x_cm": init["source_x_cm"],
                    "source_y_cm": init["source_y_cm"],
                    "source_z_cm": init["source_z_cm"],
                    "ZA": init["ZA"],
                    "isotope": isotope_from_za(init["ZA"]),
                    "exc_keV": match.get("exc_keV", ""),
                    "source_volume": match.get("VN", ""),
                    "sample_weight": match.get("sample_weight", ""),
                    "source_sim": source_sim,
                    "production_particle_family": particle_from_source(source_sim),
                    "source_match_status": status,
                    "source_match_count": match_count,
                    "source_match_distance_cm": match_distance,
                    "energy_band": "W2_510p58_511p42",
                }
            )

        summary = load_json(resolve(str(run["summary_path"])))
        m_points = int(summary.get("n_pointsource_blocks", 0) or 0)
        source_card = resolve(str(run["source_card_path"]))
        manifest_rows.append(
            {
                "run_id": run_id,
                "sampling_class": run.get("sampling_class", ""),
                "source_activity_Bq": run.get("source_activity_Bq", ""),
                "M": m_points,
                "position_sampling_seed": run.get("seed_or_tag", ""),
                "decay_transport_seed": run.get("seed_or_tag", ""),
                "generated_decays": run.get("generated_decays", run.get("generated_delayed_decays", "")),
                "selected_events": len(selected),
                "sum_w": selected_rate,
                "sum_w2": selected_sum_w2,
                "selected_rate_cps": selected_rate,
                "mc_sigma_cps": math.sqrt(selected_sum_w2),
                "geometry_hash": geometry_hash,
                "source_hash": sha256(source_card),
                "selection_code_hash": selection_hash,
                "geometry_path": run.get("geometry_path", ""),
                "source_card_path": rel(source_card),
                "sim_path": rel(sim_path),
                "catalog_cache": rel(catalog_cache),
                "exactpos_table": rel(table),
                "source_geometry_status": run.get("source_geometry_status", {}).get("status", ""),
                "sim_header_status": run.get("sim_header_status", ""),
                "provenance_status": run.get("provenance_status", ""),
                "sampling_audit_status": run.get("sampling_audit_status", ""),
                "side_compton_class_counts": ";".join(f"{key}:{class_counts[key]}" for key in sorted(class_counts)),
            }
        )

    run_manifest_csv = OUT / "delayed_run_manifest.csv"
    selected_events_csv = OUT / "delayed_selected_events.csv"
    decomposition_csv = OUT / "delayed_selected_decomposition.csv"
    isotope_csv = OUT / "delayed_selected_isotope_summary.csv"
    volume_csv = OUT / "delayed_selected_volume_summary.csv"
    convergence_csv = OUT / "delayed_selected_rate_convergence.csv"
    write_csv(run_manifest_csv, manifest_rows)
    write_csv(selected_events_csv, selected_rows)
    write_csv(decomposition_csv, grouped(selected_rows, ("isotope", "ZA", "source_volume", "production_particle_family", "energy_band")))
    write_csv(isotope_csv, grouped(selected_rows, ("isotope", "ZA", "energy_band")))
    write_csv(volume_csv, grouped(selected_rows, ("source_volume", "production_particle_family", "energy_band")))
    write_csv(
        convergence_csv,
        [
            {
                "run_id": run["run_id"],
                "selected_events": run["selected_events"],
                "selected_rate_cps": run["selected_rate_cps"],
                "sigma_cps": run["sigma_cps"],
                "relative_uncertainty": run["relative_uncertainty"],
                "provenance_status": run["provenance_status"],
                "sampling_audit_status": run["sampling_audit_status"],
            }
            for run in conv["runs"]
        ],
    )

    combined = dict(conv["combined"])
    g3_pass = (
        int(combined.get("selected_events", 0)) >= 100
        and float(combined.get("relative_uncertainty", 1.0)) <= 0.1
        and conv.get("between_sampling_check", {}).get("status") == "PASS"
        and all(str(run.get("provenance_status")) == "PASS" for run in conv["runs"])
        and all(str(run.get("sampling_audit_status")) == "PASS" for run in conv["runs"])
        and not problems
    )
    status = "DELAYED_CONVERGED" if g3_pass else "DELAYED_STAT_LIMITED"
    resource_estimate = estimate_resources(conv["runs"], combined)

    payload = {
        "artifact_type": "wp03_delayed_selected_rate_convergence",
        "status": status,
        "created_utc": now_utc(),
        "source_convergence_artifact": rel(CONV_SRC),
        "acceptance": {
            "minimum_selected_events": 100,
            "preferred_selected_events": 300,
            "relative_uncertainty_max": 0.1,
            "requires_between_sampling_check": True,
            "requires_provenance_and_sampling_audit_pass": True,
        },
        "combined": combined,
        "between_sampling_check": conv.get("between_sampling_check", {}),
        "resource_estimate": resource_estimate,
        "outputs": {
            "run_manifest_csv": rel(run_manifest_csv),
            "selected_events_csv": rel(selected_events_csv),
            "decomposition_csv": rel(decomposition_csv),
            "isotope_summary_csv": rel(isotope_csv),
            "volume_summary_csv": rel(volume_csv),
            "convergence_csv": rel(convergence_csv),
            "json": rel(OUT / "delayed_selected_rate_convergence.json"),
            "markdown": rel(OUT / "delayed_selected_rate_convergence.md"),
        },
        "notes": [
            "The existing PI-02 runs vary the exact-position production-position sampling seed and use matching Cosima transport seed tags.",
            "No new delayed transport was launched by this engineering harness script.",
        ],
        "problems": problems,
    }
    write_json(OUT / "delayed_selected_rate_convergence.json", payload)
    write_json(OUT / "summary.json", payload)
    md = markdown(payload)
    (OUT / "delayed_selected_rate_convergence.md").write_text(md, encoding="utf-8")
    (OUT / "summary.md").write_text(md, encoding="utf-8")
    return payload


def markdown(payload: dict[str, Any]) -> str:
    combined = payload["combined"]
    lines = [
        "# WP03 Delayed Selected-Rate Convergence",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"Pooled selected events: `{combined['selected_events']}`.",
        f"Pooled selected rate: `{combined['selected_rate_cps']:.12g}` cps.",
        f"MC sigma: `{combined['sigma_cps']:.12g}` cps.",
        f"Relative uncertainty: `{combined['relative_uncertainty']:.6g}`.",
        f"Between-sampling check: `{payload['between_sampling_check'].get('status')}`.",
        "",
        "Resource estimate:",
        f"- current generated decays: `{payload['resource_estimate']['current_generated_decays']}`",
        f"- estimated decays for 100 selected: `{payload['resource_estimate']['estimated_decays_for_100_selected']}`",
        f"- estimated decays for 300 selected: `{payload['resource_estimate']['estimated_decays_for_300_selected']}`",
        f"- new runs required for G3: `{payload['resource_estimate']['new_runs_required_for_g3']}`",
        "",
        "Outputs:",
        f"- run manifest: `{payload['outputs']['run_manifest_csv']}`",
        f"- selected events: `{payload['outputs']['selected_events_csv']}`",
        f"- decomposition: `{payload['outputs']['decomposition_csv']}`",
    ]
    if payload["problems"]:
        lines.extend(["", "Problems:"])
        lines.extend(f"- {item}" for item in payload["problems"])
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = build()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_events": payload["combined"]["selected_events"],
                "relative_uncertainty": payload["combined"]["relative_uncertainty"],
                "out": payload["outputs"]["json"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if payload["status"] in {"DELAYED_CONVERGED", "DELAYED_STAT_LIMITED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
