#!/usr/bin/env python3
"""Ingress and veto audit for the current geo-opt branch.

This script intentionally reads existing transport products only.  It does not
modify any authority geometry or rerun transport.
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import pickle
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent

STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_BRIDGE = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
STEP05_CACHE = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1"
    / "work/event_catalog.pkl"
)
P2_ATM511_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1"
    / "Atm511LowerUnit3M_GeoOptS1BpeW5.inc1.id1.sim.gz"
)
P2_ATM511_LOG = (
    ROOT
    / "runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1"
    / "cosima_Atm511LowerUnit3M_GeoOptS1BpeW5.log"
)
P2_ATM511_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/06_atm511_replay_20260707"
    / "p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json"
)
CURRENT_GEO = (
    ROOT
    / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
)

ACTIVE_VETO_THRESHOLD_KEV = 50.0
WINDOWS = {
    "w2_510p58_511p42": (510.58, 511.42),
    "broad_480_550": (480.0, 550.0),
}

CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
ID_RE = re.compile(r"^ID\s+(\d+)")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_step05_module():
    spec = importlib.util.spec_from_file_location("geo_opt_ingress_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.STEP09_SUMMARY = STEP09_BRIDGE
    return mod


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
    )


def volume_category(vol: str | None) -> str:
    if not vol:
        return "none"
    upper = str(vol).upper()
    if upper.startswith("TP_") or upper.startswith("TES_"):
        return "tes"
    if upper.startswith("CSI_"):
        return "csi_active"
    if upper.startswith("GEOOPT_S1_PLASTICFULLWRAP"):
        return "geoopt_plastic_active"
    if upper.startswith("GEOOPT_BPE"):
        return "geoopt_bpe_passive"
    if upper.startswith("GEOOPT_W") or upper == "W" or "TUNGSTEN" in upper:
        return "geoopt_w_passive"
    if "WINDOW" in upper:
        return "window_or_side_port"
    if upper.startswith("NF2_OUTERSUPPORT"):
        return "external_support"
    if "VACUUM_JACKET" in upper or "OUTER_AL" in upper or "OUTER_" in upper:
        return "outer_mechanics"
    if "SHIELD" in upper or "COLL" in upper or "XS400" in upper:
        return "passive_shield_or_collimator"
    if "AL" in upper or "ALUMIN" in upper:
        return "aluminium_passive"
    if "STAINLESS" in upper or "SS_" in upper:
        return "stainless_passive"
    if "G10" in upper:
        return "g10_passive"
    return "other"


def load_material_map() -> dict[str, str]:
    material: dict[str, str] = {}
    if CURRENT_GEO.exists():
        for raw in CURRENT_GEO.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ".Material " not in raw:
                continue
            name, mat = raw.split(".Material ", 1)
            material[name.strip()] = mat.strip()
    return material


def material_for_volume(vol: str | None, material_map: dict[str, str]) -> str:
    if not vol:
        return "none"
    if vol in material_map:
        return material_map[vol]
    upper = str(vol).upper()
    if upper.startswith("TP_L") or upper.startswith("TES_PIXEL"):
        return "Ta"
    if upper.startswith("CSI_"):
        return "CsI"
    if upper.startswith("GEOOPT_S1_PLASTICFULLWRAP"):
        return "PlasticScintillator"
    if upper.startswith("GEOOPT_BPE"):
        return "BoratedPolyethylene5wtB"
    if upper.startswith("GEOOPT_W"):
        return "W"
    if "AL" in upper or "WINDOW" in upper:
        return "Aluminium_or_window_proxy"
    if "STAINLESS" in upper or "SS_" in upper:
        return "StainlessSteel"
    if "G10" in upper:
        return "G10"
    return "unknown"


def canonical_entry_region(row: dict[str, Any]) -> str:
    first_cat = str(row.get("first_hit_category") or "")
    if first_cat == "external_support":
        return "support"
    surface = str(row.get("entry_surface_proxy") or "")
    detailed = str(row.get("entry_region_proxy") or "")
    if "window_axis" in detailed:
        return "side_window"
    if surface == "side":
        return "side_wall"
    if surface == "bottom":
        return "bottom"
    if surface == "top":
        return "top"
    return "unknown"


def source_angle_bins(row: dict[str, Any]) -> dict[str, str]:
    dx = row.get("dir_x")
    dy = row.get("dir_y")
    dz = row.get("dir_z")
    if dx is None or dy is None or dz is None:
        return {"source_theta_bin": "unknown", "source_phi_bin": "unknown"}
    vec = rotate_y((float(dx), float(dy), float(dz)), -45.0)
    norm = float(np.linalg.norm(vec))
    if norm <= 0:
        return {"source_theta_bin": "unknown", "source_phi_bin": "unknown"}
    vec = vec / norm
    theta = math.degrees(math.acos(max(-1.0, min(1.0, float(vec[2])))))
    phi = math.degrees(math.atan2(float(vec[1]), float(vec[0]))) % 360.0
    t0 = int(math.floor(theta / 10.0) * 10)
    p0 = int(math.floor(phi / 45.0) * 45)
    return {"source_theta_bin": f"{t0:03d}_{t0 + 10:03d}", "source_phi_bin": f"{p0:03d}_{p0 + 45:03d}"}


def rotate_y(vec: tuple[float, float, float] | list[float] | np.ndarray, angle_deg: float) -> np.ndarray:
    x, y, z = [float(v) for v in vec]
    a = math.radians(angle_deg)
    c = math.cos(a)
    s = math.sin(a)
    return np.asarray([c * x + s * z, y, -s * x + c * z], dtype=float)


def phi_sector(phi_deg: float) -> str:
    phi = phi_deg % 360.0
    idx = int(math.floor((phi + 22.5) / 45.0)) % 8
    return f"phi{idx:02d}_{idx * 45:03d}deg"


def signed_window_axis_delta_deg(phi_deg: float) -> float:
    # Negative local X is the side-window axis in this branch.
    return ((phi_deg - 180.0 + 180.0) % 360.0) - 180.0


def classify_envelope_entry(
    init_pos_world: tuple[float, float, float] | None,
    init_dir_world: tuple[float, float, float] | None,
) -> dict[str, Any]:
    if init_pos_world is None or init_dir_world is None:
        return {"entry_surface_proxy": "missing_init", "entry_region_proxy": "missing_init"}

    p = rotate_y(init_pos_world, -45.0)
    d = rotate_y(init_dir_world, -45.0)
    norm = float(np.linalg.norm(d))
    if norm <= 0:
        return {"entry_surface_proxy": "bad_init_dir", "entry_region_proxy": "bad_init_dir"}
    d = d / norm

    r_outer = 27.9
    z_min = -23.6
    z_max = 7.7
    candidates: list[tuple[float, str, np.ndarray]] = []

    a = d[0] ** 2 + d[1] ** 2
    b = 2.0 * (p[0] * d[0] + p[1] * d[1])
    c = p[0] ** 2 + p[1] ** 2 - r_outer**2
    if abs(a) > 1.0e-15:
        disc = b * b - 4.0 * a * c
        if disc >= 0:
            root = math.sqrt(disc)
            for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if t > 0:
                    q = p + t * d
                    if z_min - 1.0e-6 <= q[2] <= z_max + 1.0e-6:
                        candidates.append((float(t), "side", q))

    if abs(d[2]) > 1.0e-15:
        for z_cap, surface in ((z_min, "bottom"), (z_max, "top")):
            t = (z_cap - p[2]) / d[2]
            if t > 0:
                q = p + t * d
                if q[0] ** 2 + q[1] ** 2 <= r_outer**2 + 1.0e-6:
                    candidates.append((float(t), surface, q))

    if not candidates:
        phi0 = math.degrees(math.atan2(p[1], p[0])) % 360.0
        return {
            "entry_surface_proxy": "miss_current_outer_envelope",
            "entry_region_proxy": phi_sector(phi0),
            "init_local_x_cm": float(p[0]),
            "init_local_y_cm": float(p[1]),
            "init_local_z_cm": float(p[2]),
            "dir_local_x": float(d[0]),
            "dir_local_y": float(d[1]),
            "dir_local_z": float(d[2]),
        }

    _, surface, q = sorted(candidates, key=lambda item: item[0])[0]
    phi = math.degrees(math.atan2(q[1], q[0])) % 360.0
    delta = signed_window_axis_delta_deg(phi)
    if surface == "side" and abs(delta) <= 15.0:
        region = "side_neg_x_window_axis_pm15deg"
    elif surface == "side":
        region = f"side_{phi_sector(phi)}"
    else:
        region = f"{surface}_{phi_sector(phi)}"

    return {
        "entry_surface_proxy": surface,
        "entry_region_proxy": region,
        "entry_phi_deg_local": float(phi),
        "entry_window_axis_delta_deg": float(delta),
        "entry_local_x_cm": float(q[0]),
        "entry_local_y_cm": float(q[1]),
        "entry_local_z_cm": float(q[2]),
        "init_local_x_cm": float(p[0]),
        "init_local_y_cm": float(p[1]),
        "init_local_z_cm": float(p[2]),
        "dir_local_x": float(d[0]),
        "dir_local_y": float(d[1]),
        "dir_local_z": float(d[2]),
    }


def parse_ia_init(line: str) -> dict[str, Any] | None:
    try:
        fields = [part.strip() for part in line.split("IA INIT", 1)[1].split(";")]
        x = float(fields[4])
        y = float(fields[5])
        z = float(fields[6])
        particle_code = int(float(fields[15]))
        dx = float(fields[16])
        dy = float(fields[17])
        dz = float(fields[18])
        energy = float(fields[-1])
    except Exception:
        return None
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    theta = math.degrees(math.acos(max(-1.0, min(1.0, dz / norm)))) if norm > 0 else None
    return {
        "init_x_cm": x,
        "init_y_cm": y,
        "init_z_cm": z,
        "dir_x": dx,
        "dir_y": dy,
        "dir_z": dz,
        "init_energy_keV": energy,
        "particle_code": particle_code,
        "theta_from_global_plus_z_deg": theta,
    }


def parse_hit(line: str) -> dict[str, Any] | None:
    match = CC_HIT_RE.match(line)
    if match is None:
        return None
    vol = match.group(1)
    kv = dict(KV_RE.findall(match.group(2)))
    out: dict[str, Any] = {"volume": vol, "category": volume_category(vol)}
    for key in ("edep_keV", "x", "y", "z", "t"):
        if key in kv:
            try:
                out[key] = float(kv[key])
            except ValueError:
                pass
    for key in ("sec", "prim", "sproc", "cproc"):
        if key in kv:
            out[key] = kv[key]
    return out


def event_hits_from_cache(cat: dict[str, Any], idx: int) -> list[Any]:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    hits = []
    for j in range(start, start + count):
        hit = type("Hit", (), {})()
        hit.x = float(cat["pix_x"][j])
        hit.y = float(cat["pix_y"][j])
        hit.z = float(cat["pix_z"][j])
        hit.e = float(cat["pix_e"][j])
        hit.pixel_uid = str(cat["pix_uid"][j])
        hit.layer = int(cat["pix_layer"][j])
        hits.append(hit)
    return hits


def load_current_catalog() -> dict[str, Any]:
    with STEP05_CACHE.open("rb") as handle:
        return pickle.load(handle)


def collect_selected_event_metadata(targets_by_file: dict[str, set[int]]) -> dict[tuple[str, int], dict[str, Any]]:
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for source_file, ids in sorted(targets_by_file.items()):
        path = Path(source_file)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise FileNotFoundError(path)
        remaining = set(ids)
        cur_id: int | None = None
        interested = False
        rec: dict[str, Any] | None = None

        def flush() -> None:
            nonlocal rec, cur_id, interested
            if interested and cur_id is not None and rec is not None:
                init = rec.get("init")
                if init:
                    rec.update(
                        classify_envelope_entry(
                            (init["init_x_cm"], init["init_y_cm"], init["init_z_cm"]),
                            (init["dir_x"], init["dir_y"], init["dir_z"]),
                        )
                    )
                records[(rel(path), int(cur_id))] = rec
                remaining.discard(int(cur_id))
            rec = None
            cur_id = None
            interested = False

        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                line = raw.strip()
                if line == "SE":
                    flush()
                    if not remaining:
                        break
                    continue
                match_id = ID_RE.match(line)
                if match_id:
                    cur_id = int(match_id.group(1))
                    interested = cur_id in remaining
                    rec = {
                        "source_file": rel(path),
                        "local_id": cur_id,
                        "first_hit_volume": None,
                        "first_hit_category": "none",
                        "first_hit_x_cm": None,
                        "first_hit_y_cm": None,
                        "first_hit_z_cm": None,
                        "first_hit_edep_keV": None,
                    } if interested else None
                    continue
                if not interested or rec is None:
                    continue
                if line.startswith("IA INIT"):
                    rec["init"] = parse_ia_init(line)
                elif line.startswith("CC HIT ") and rec.get("first_hit_volume") is None:
                    hit = parse_hit(line)
                    if hit:
                        rec["first_hit_volume"] = hit["volume"]
                        rec["first_hit_category"] = hit["category"]
                        rec["first_hit_x_cm"] = hit.get("x")
                        rec["first_hit_y_cm"] = hit.get("y")
                        rec["first_hit_z_cm"] = hit.get("z")
                        rec["first_hit_edep_keV"] = hit.get("edep_keV")
            flush()
        if remaining:
            raise RuntimeError(f"missing {len(remaining)} target events in {path}: {sorted(remaining)[:10]}")
    return records


def summarize_current_prompt_family(
    cat: dict[str, Any],
    step05: Any,
    disk: dict[str, Any],
    family: str,
    window_name: str,
    emin: float,
    emax: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    stream = np.asarray(cat["stream"], dtype=object)
    tag = np.asarray(cat["tag"], dtype=object)
    tes = np.asarray(cat["tes_total_keV"], dtype=np.float64)
    bgo = np.asarray(cat["bgo_total_keV"], dtype=np.float64)
    rates = np.asarray(cat["rate_hz"], dtype=np.float64)

    raw_indices = np.flatnonzero((stream == "prompt") & (tag == family) & (tes >= emin) & (tes < emax))
    active_indices = [int(i) for i in raw_indices if float(bgo[i]) < ACTIVE_VETO_THRESHOLD_KEV]
    side_classes: Counter[str] = Counter()
    final_indices: list[int] = []
    for idx in active_indices:
        keep, cls = step05.side_keep_from_hits(event_hits_from_cache(cat, idx), disk, "keep")
        side_classes[cls] += 1
        if keep:
            final_indices.append(idx)

    targets_by_file: dict[str, set[int]] = defaultdict(set)
    for idx in raw_indices:
        targets_by_file[str(cat["source_file"][idx])].add(int(cat["local_id"][idx]))
    metadata = collect_selected_event_metadata(targets_by_file)

    active_set = set(active_indices)
    final_set = set(final_indices)
    event_rows: list[dict[str, Any]] = []
    for idx in raw_indices:
        key = (rel(Path(str(cat["source_file"][idx])) if Path(str(cat["source_file"][idx])).is_absolute() else ROOT / str(cat["source_file"][idx])), int(cat["local_id"][idx]))
        meta = metadata.get(key, {})
        init = meta.get("init") or {}
        event_rows.append(
            {
                "family": family,
                "window": window_name,
                "source_file": rel(str(cat["source_file"][idx])),
                "local_id": int(cat["local_id"][idx]),
                "stage_raw": True,
                "stage_active_veto_pass": int(idx) in active_set,
                "stage_side_compton_fov_pass": int(idx) in final_set,
                "tes_total_keV": float(tes[idx]),
                "active_veto_keV": float(bgo[idx]),
                "rate_s-1": float(rates[idx]),
                "side_compton_class": "not_active_veto_pass",
                "entry_surface_proxy": meta.get("entry_surface_proxy"),
                "entry_region_proxy": meta.get("entry_region_proxy"),
                "entry_phi_deg_local": meta.get("entry_phi_deg_local"),
                "entry_local_x_cm": meta.get("entry_local_x_cm"),
                "entry_local_y_cm": meta.get("entry_local_y_cm"),
                "entry_local_z_cm": meta.get("entry_local_z_cm"),
                "init_x_cm": init.get("init_x_cm"),
                "init_y_cm": init.get("init_y_cm"),
                "init_z_cm": init.get("init_z_cm"),
                "dir_x": init.get("dir_x"),
                "dir_y": init.get("dir_y"),
                "dir_z": init.get("dir_z"),
                "theta_from_global_plus_z_deg": init.get("theta_from_global_plus_z_deg"),
                "init_energy_keV": init.get("init_energy_keV"),
                "first_hit_volume": meta.get("first_hit_volume"),
                "first_hit_category": meta.get("first_hit_category"),
            }
        )
    # Fill side class after event rows are built, preserving order.
    side_by_idx: dict[int, str] = {}
    for idx in active_indices:
        _, cls = step05.side_keep_from_hits(event_hits_from_cache(cat, idx), disk, "keep")
        side_by_idx[idx] = cls
    for row, idx in zip(event_rows, raw_indices):
        if int(idx) in side_by_idx:
            row["side_compton_class"] = side_by_idx[int(idx)]

    summary = {
        "family": family,
        "window": window_name,
        "raw_events": int(len(raw_indices)),
        "active_veto_pass_events": int(len(active_indices)),
        "side_compton_fov_pass_events": int(len(final_indices)),
        "raw_rate_s-1": float(np.sum(rates[raw_indices])),
        "active_veto_pass_rate_s-1": float(np.sum(rates[active_indices])) if active_indices else 0.0,
        "side_compton_fov_pass_rate_s-1": float(np.sum(rates[final_indices])) if final_indices else 0.0,
        "active_veto_rejection_fraction_vs_raw_rate": None,
        "side_compton_fov_rejection_fraction_vs_active_rate": None,
        "final_survival_fraction_vs_raw_rate": None,
        "side_compton_class_counts": dict(sorted(side_classes.items())),
    }
    if summary["raw_rate_s-1"] > 0:
        summary["active_veto_rejection_fraction_vs_raw_rate"] = 1.0 - summary["active_veto_pass_rate_s-1"] / summary["raw_rate_s-1"]
        summary["final_survival_fraction_vs_raw_rate"] = summary["side_compton_fov_pass_rate_s-1"] / summary["raw_rate_s-1"]
    if summary["active_veto_pass_rate_s-1"] > 0:
        summary["side_compton_fov_rejection_fraction_vs_active_rate"] = (
            1.0 - summary["side_compton_fov_pass_rate_s-1"] / summary["active_veto_pass_rate_s-1"]
        )
    return summary, event_rows


def p2_observation_time_s() -> float:
    for line in P2_ATM511_LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if nums:
                return float(nums[0])
    raise RuntimeError(f"cannot locate Observation time in {P2_ATM511_LOG}")


def parse_atm511_window(step05: Any, disk: dict[str, Any], window_name: str, emin: float, emax: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_rows: list[dict[str, Any]] = []
    obs_time_s = p2_observation_time_s()
    cur_id: int | None = None
    init: dict[str, Any] | None = None
    first_hit: dict[str, Any] | None = None
    tes_total = 0.0
    active_total = 0.0
    pix: dict[str, dict[str, Any]] = {}
    generated = 0

    tp_re = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)

    def hits_for_side() -> list[Any]:
        hits = []
        for uid, rec in sorted(pix.items()):
            e = float(rec["e"])
            if e <= 0:
                continue
            hit = type("Hit", (), {})()
            hit.x = float(rec["wx"] / e)
            hit.y = float(rec["wy"] / e)
            hit.z = float(rec["wz"] / e)
            hit.e = e
            hit.pixel_uid = uid
            hit.layer = int(rec["layer"])
            hits.append(hit)
        return hits

    def flush() -> None:
        nonlocal cur_id, init, first_hit, tes_total, active_total, pix
        if cur_id is None:
            return
        if emin <= tes_total < emax:
            keep = False
            cls = "not_active_veto_pass"
            if active_total < ACTIVE_VETO_THRESHOLD_KEV:
                keep, cls = step05.side_keep_from_hits(hits_for_side(), disk, "keep")
            entry = classify_envelope_entry(
                None if init is None else (init["init_x_cm"], init["init_y_cm"], init["init_z_cm"]),
                None if init is None else (init["dir_x"], init["dir_y"], init["dir_z"]),
            )
            row = {
                "family": "atm511",
                "window": window_name,
                "source_file": rel(P2_ATM511_SIM),
                "local_id": int(cur_id),
                "stage_raw": True,
                "stage_active_veto_pass": active_total < ACTIVE_VETO_THRESHOLD_KEV,
                "stage_side_compton_fov_pass": bool(keep),
                "tes_total_keV": float(tes_total),
                "active_veto_keV": float(active_total),
                "rate_s-1_per_unit_flux": 1.0 / obs_time_s,
                "side_compton_class": cls,
                "first_hit_volume": None if first_hit is None else first_hit.get("volume"),
                "first_hit_category": "none" if first_hit is None else first_hit.get("category"),
            }
            if init:
                row.update(
                    {
                        "init_x_cm": init.get("init_x_cm"),
                        "init_y_cm": init.get("init_y_cm"),
                        "init_z_cm": init.get("init_z_cm"),
                        "dir_x": init.get("dir_x"),
                        "dir_y": init.get("dir_y"),
                        "dir_z": init.get("dir_z"),
                        "theta_from_global_plus_z_deg": init.get("theta_from_global_plus_z_deg"),
                        "init_energy_keV": init.get("init_energy_keV"),
                    }
                )
            row.update(entry)
            raw_rows.append(row)
        cur_id = None
        init = None
        first_hit = None
        tes_total = 0.0
        active_total = 0.0
        pix = {}

    with gzip.open(P2_ATM511_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match_id = ID_RE.match(line)
            if match_id:
                cur_id = int(match_id.group(1))
                generated += 1
                continue
            if cur_id is None:
                continue
            if line.startswith("IA INIT"):
                init = parse_ia_init(line)
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parse_hit(line)
            if not hit:
                continue
            if first_hit is None:
                first_hit = hit
            vol = str(hit["volume"])
            edep = float(hit.get("edep_keV") or 0.0)
            x = float(hit.get("x") or 0.0)
            y = float(hit.get("y") or 0.0)
            z = float(hit.get("z") or 0.0)
            match_tp = tp_re.match(vol)
            if match_tp:
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(match_tp.group("layer"))})
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
                tes_total += edep
            elif is_active_veto_volume(vol):
                active_total += edep
        flush()

    obs = obs_time_s
    raw = len(raw_rows)
    active = [r for r in raw_rows if r["stage_active_veto_pass"]]
    final = [r for r in raw_rows if r["stage_side_compton_fov_pass"]]
    class_counts = Counter(str(r["side_compton_class"]) for r in active)
    summary = {
        "family": "atm511",
        "window": window_name,
        "generated_events": generated,
        "observation_time_s": obs,
        "raw_events": raw,
        "active_veto_pass_events": len(active),
        "side_compton_fov_pass_events": len(final),
        "raw_rate_s-1_per_unit_flux": raw / obs,
        "active_veto_pass_rate_s-1_per_unit_flux": len(active) / obs,
        "side_compton_fov_pass_rate_s-1_per_unit_flux": len(final) / obs,
        "active_veto_rejection_fraction_vs_raw_count": 1.0 - len(active) / raw if raw else None,
        "side_compton_fov_rejection_fraction_vs_active_count": 1.0 - len(final) / len(active) if active else None,
        "final_survival_fraction_vs_raw_count": len(final) / raw if raw else None,
        "side_compton_class_counts": dict(sorted(class_counts.items())),
    }
    return summary, raw_rows


def aggregate_ingress(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stages = [
        ("raw", "stage_raw"),
        ("active_veto_pass", "stage_active_veto_pass"),
        ("side_compton_fov_pass", "stage_side_compton_fov_pass"),
    ]
    groupers = [
        ("entry_surface_proxy", "entry_surface_proxy"),
        ("entry_region_proxy", "entry_region_proxy"),
        ("first_hit_category", "first_hit_category"),
        ("first_hit_volume", "first_hit_volume"),
    ]
    for family in sorted(set(str(r["family"]) for r in event_rows)):
        family_rows = [r for r in event_rows if str(r["family"]) == family]
        for stage_name, stage_key in stages:
            stage_rows = [r for r in family_rows if bool(r.get(stage_key))]
            denom = len(stage_rows)
            for group_name, key in groupers:
                counts = Counter(str(r.get(key) or "missing") for r in stage_rows)
                for value, count in counts.most_common():
                    out.append(
                        {
                            "family": family,
                            "window": "w2_510p58_511p42",
                            "stage": stage_name,
                            "group_by": group_name,
                            "group_value": value,
                            "events": count,
                            "fraction_of_stage": count / denom if denom else "",
                        }
                    )
    return out


def build_ingress_event_stage_rows(event_rows: list[dict[str, Any]], material_map: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stages = [
        ("raw", "stage_raw"),
        ("active_veto_pass", "stage_active_veto_pass"),
        ("side_compton_fov_pass", "stage_side_compton_fov_pass"),
    ]
    for event in event_rows:
        first_vol = event.get("first_hit_volume")
        base = {
            "source_family": event["family"],
            "window": event["window"],
            "source_file": event.get("source_file"),
            "local_id": event.get("local_id"),
            "source_theta_bin": "",
            "source_phi_bin": "",
            "first_recorded_volume": first_vol or "none",
            "first_recorded_material": material_for_volume(first_vol, material_map),
            "entry_region": canonical_entry_region(event),
            "first_recorded_x_cm": event.get("first_hit_x_cm"),
            "first_recorded_y_cm": event.get("first_hit_y_cm"),
            "first_recorded_z_cm": event.get("first_hit_z_cm"),
            "tes_energy_keV": event.get("tes_total_keV"),
            "active_veto_energy_keV": event.get("active_veto_keV"),
            "side_compton_class": event.get("side_compton_class"),
            "entry_surface_proxy": event.get("entry_surface_proxy"),
            "entry_region_proxy": event.get("entry_region_proxy"),
            "entry_phi_deg_local": event.get("entry_phi_deg_local"),
            "init_x_cm": event.get("init_x_cm"),
            "init_y_cm": event.get("init_y_cm"),
            "init_z_cm": event.get("init_z_cm"),
            "dir_x": event.get("dir_x"),
            "dir_y": event.get("dir_y"),
            "dir_z": event.get("dir_z"),
            "init_energy_keV": event.get("init_energy_keV"),
        }
        base.update(source_angle_bins(event))
        rate = event.get("rate_s-1", event.get("rate_s-1_per_unit_flux", 0.0))
        for stage_name, stage_key in stages:
            if not bool(event.get(stage_key)):
                continue
            row = dict(base)
            row.update(
                {
                    "stage": stage_name,
                    "event_count": 1,
                    "rate_or_transfer": rate,
                    "rate_units": "cps normalized by prompt TT"
                    if event["family"] in ("eplus", "n")
                    else "cps per ph cm^-2 s^-1 lower-hemisphere flux",
                }
            )
            rows.append(row)
    return rows


def build_veto_rows(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for s in summaries:
        raw_rate = s.get("raw_rate_s-1", s.get("raw_rate_s-1_per_unit_flux"))
        active_rate = s.get("active_veto_pass_rate_s-1", s.get("active_veto_pass_rate_s-1_per_unit_flux"))
        final_rate = s.get("side_compton_fov_pass_rate_s-1", s.get("side_compton_fov_pass_rate_s-1_per_unit_flux"))
        raw_count = int(s["raw_events"])
        active_count = int(s["active_veto_pass_events"])
        final_count = int(s["side_compton_fov_pass_events"])
        rows.append(
            {
                "family": s["family"],
                "window": s["window"],
                "raw_events": raw_count,
                "active_veto_pass_events": active_count,
                "side_compton_fov_pass_events": final_count,
                "raw_rate": raw_rate,
                "active_veto_pass_rate": active_rate,
                "side_compton_fov_pass_rate": final_rate,
                "active_veto_rejection_fraction_count": 1.0 - active_count / raw_count if raw_count else "",
                "compton_fov_rejection_fraction_vs_active_count": 1.0 - final_count / active_count if active_count else "",
                "total_rejection_fraction_count": 1.0 - final_count / raw_count if raw_count else "",
                "active_veto_rejection_fraction_rate": 1.0 - active_rate / raw_rate if raw_rate else "",
                "compton_fov_rejection_fraction_vs_active_rate": 1.0 - final_rate / active_rate if active_rate else "",
                "total_rejection_fraction_rate": 1.0 - final_rate / raw_rate if raw_rate else "",
                "final_survival_fraction_vs_raw_rate": final_rate / raw_rate if raw_rate else "",
                "side_compton_class_counts_json": json.dumps(s.get("side_compton_class_counts", {}), sort_keys=True),
                "rate_units": "cps normalized by prompt TT" if s["family"] in ("eplus", "n") else "cps per ph cm^-2 s^-1 lower-hemisphere flux",
            }
        )
    return rows


def build_veto_by_ingress_region(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in event_rows:
        grouped[(str(event["family"]), str(event["window"]), canonical_entry_region(event))].append(event)
    rows: list[dict[str, Any]] = []
    for (family, window, region), events in sorted(grouped.items()):
        raw = [e for e in events if e.get("stage_raw")]
        active = [e for e in events if e.get("stage_active_veto_pass")]
        final = [e for e in events if e.get("stage_side_compton_fov_pass")]

        def rate(items: list[dict[str, Any]]) -> float:
            return float(sum(float(e.get("rate_s-1", e.get("rate_s-1_per_unit_flux", 0.0)) or 0.0) for e in items))

        raw_rate = rate(raw)
        active_rate = rate(active)
        final_rate = rate(final)
        rows.append(
            {
                "family": family,
                "window": window,
                "entry_region": region,
                "raw_events": len(raw),
                "active_veto_pass_events": len(active),
                "side_compton_fov_pass_events": len(final),
                "raw_rate": raw_rate,
                "active_veto_pass_rate": active_rate,
                "side_compton_fov_pass_rate": final_rate,
                "active_veto_rejection_fraction_count": 1.0 - len(active) / len(raw) if raw else "",
                "compton_fov_rejection_fraction_vs_active_count": 1.0 - len(final) / len(active) if active else "",
                "total_rejection_fraction_count": 1.0 - len(final) / len(raw) if raw else "",
                "active_veto_rejection_fraction_rate": 1.0 - active_rate / raw_rate if raw_rate else "",
                "compton_fov_rejection_fraction_vs_active_rate": 1.0 - final_rate / active_rate if active_rate else "",
                "total_rejection_fraction_rate": 1.0 - final_rate / raw_rate if raw_rate else "",
            }
        )
    return rows


def build_side_class_rows(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in event_rows:
        if not event.get("stage_active_veto_pass"):
            continue
        grouped[(str(event["family"]), str(event["window"]), str(event.get("side_compton_class") or "missing"))].append(event)
    rows: list[dict[str, Any]] = []
    for (family, window, cls), events in sorted(grouped.items()):
        rows.append(
            {
                "family": family,
                "window": window,
                "side_compton_class": cls,
                "events": len(events),
                "rate": float(sum(float(e.get("rate_s-1", e.get("rate_s-1_per_unit_flux", 0.0)) or 0.0) for e in events)),
                "survives_reject_policy_keep": cls in ("single", "keep", "reject_kept"),
            }
        )
    return rows


def write_markdown(veto_rows: list[dict[str, Any]], ingress_rows: list[dict[str, Any]], event_rows: list[dict[str, Any]]) -> None:
    md = [
        "# Ingress And Veto Audit",
        "",
        f"Generated: `{now_utc()}`",
        "",
        "Scope: current `geo_opt_s1_bpe_w5_fullstat_v1` W2 candidates only.",
        "",
        "Ingress definition: `IA INIT` is read from each SIM event.  The entry surface is a proxy from the INIT ray intersecting the current geo-opt outer envelope in instrument-local coordinates: radius 27.9 cm, z -23.6..7.7 cm, inverse 45 deg Y rotation.  This is not a Geant4 boundary-crossing scorer.",
        "",
        "Veto definition: active anticoincidence is `active_veto_keV < 50 keV`, with CsI/BGO/legacy active names and `GeoOpt_S1_PlasticFullWrap*` counted as active.  Compton/FoV veto reuses `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py` with `reject_policy=keep`.",
        "",
        "## Veto Cutflow",
        "",
        "| family | raw | active pass | final pass | active rejection | Compton/FoV rejection vs active | final survival |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in veto_rows:
        md.append(
            "| {family} | {raw_events} | {active_veto_pass_events} | {side_compton_fov_pass_events} | {a:.3f} | {c:.3f} | {s:.3f} |".format(
                family=row["family"],
                raw_events=row["raw_events"],
                active_veto_pass_events=row["active_veto_pass_events"],
                side_compton_fov_pass_events=row["side_compton_fov_pass_events"],
                a=float(row["active_veto_rejection_fraction_rate"]) if row["active_veto_rejection_fraction_rate"] != "" else float("nan"),
                c=float(row["compton_fov_rejection_fraction_vs_active_rate"]) if row["compton_fov_rejection_fraction_vs_active_rate"] != "" else float("nan"),
                s=float(row["final_survival_fraction_vs_raw_rate"]) if row["final_survival_fraction_vs_raw_rate"] != "" else float("nan"),
            )
        )
    md.extend(["", "## Dominant Final Entry Proxies", ""])
    final_entries = [r for r in ingress_rows if r["stage"] == "side_compton_fov_pass" and r["group_by"] == "entry_region_proxy"]
    md.append("| family | entry proxy | events | fraction |")
    md.append("|---|---|---:|---:|")
    for row in final_entries:
        md.append(f"| {row['family']} | {row['group_value']} | {row['events']} | {float(row['fraction_of_stage']):.3f} |")
    md.extend(
        [
            "",
            "## Files",
            "",
            f"- `ingress_summary.csv/json/md` from `{rel(WORK)}`",
            f"- `veto_efficiency_summary.csv/json/md` from `{rel(WORK)}`",
            f"- `veto_efficiency_by_source_window_stage.csv`, `veto_efficiency_by_ingress_region.csv`, `side_compton_class_counts.csv`",
            f"- Event records are embedded in `ingress_summary.json`; raw W2 event rows: `{len(event_rows)}`.",
        ]
    )
    (WORK / "ingress_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (WORK / "veto_efficiency_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    step05 = load_step05_module()
    disk = step05.side_entry_disk()
    cat = load_current_catalog()
    material_map = load_material_map()

    veto_summaries: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for family in ("eplus", "n"):
        summary, rows = summarize_current_prompt_family(cat, step05, disk, family, "w2_510p58_511p42", *WINDOWS["w2_510p58_511p42"])
        veto_summaries.append(summary)
        event_rows.extend(rows)

    atm_summary, atm_rows = parse_atm511_window(step05, disk, "w2_510p58_511p42", *WINDOWS["w2_510p58_511p42"])
    veto_summaries.append(atm_summary)
    event_rows.extend(atm_rows)

    ingress_rows = aggregate_ingress(event_rows)
    ingress_event_stage_rows = build_ingress_event_stage_rows(event_rows, material_map)
    veto_rows = build_veto_rows(veto_summaries)
    veto_region_rows = build_veto_by_ingress_region(event_rows)
    side_class_rows = build_side_class_rows(event_rows)

    write_csv(
        WORK / "ingress_summary.csv",
        ingress_event_stage_rows,
        [
            "source_family",
            "window",
            "stage",
            "event_count",
            "rate_or_transfer",
            "rate_units",
            "source_theta_bin",
            "source_phi_bin",
            "first_recorded_volume",
            "first_recorded_material",
            "entry_region",
            "first_recorded_x_cm",
            "first_recorded_y_cm",
            "first_recorded_z_cm",
            "tes_energy_keV",
            "active_veto_energy_keV",
            "side_compton_class",
            "entry_surface_proxy",
            "entry_region_proxy",
            "entry_phi_deg_local",
            "source_file",
            "local_id",
            "init_x_cm",
            "init_y_cm",
            "init_z_cm",
            "dir_x",
            "dir_y",
            "dir_z",
            "init_energy_keV",
        ],
    )
    write_csv(
        WORK / "ingress_aggregate_summary.csv",
        ingress_rows,
        ["family", "window", "stage", "group_by", "group_value", "events", "fraction_of_stage"],
    )
    write_json(
        WORK / "ingress_summary.json",
        {
            "status": "PASS_INGRESS_AUDIT_CURRENT_GEO_OPT",
            "generated_at_utc": now_utc(),
            "inputs": {
                "step05_cache": rel(STEP05_CACHE),
                "atm511_sim": rel(P2_ATM511_SIM),
                "atm511_summary": rel(P2_ATM511_SUMMARY),
                "step05_algorithm": rel(STEP05_SCRIPT),
                "side_entry_bridge": rel(STEP09_BRIDGE),
            },
            "method": {
                "window": "w2_510p58_511p42",
                "active_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
                "entry_proxy": "IA INIT ray intersection with current geo-opt outer envelope in instrument-local coordinates.",
                "entry_proxy_limits": "Not a Geant4 boundary scorer; outer envelope proxy ignores local cutouts and support reliefs.",
            },
            "aggregate_rows": ingress_rows,
            "event_stage_rows": ingress_event_stage_rows,
            "event_rows": event_rows,
        },
    )
    write_csv(
        WORK / "veto_efficiency_summary.csv",
        veto_rows,
        [
            "family",
            "window",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
            "raw_rate",
            "active_veto_pass_rate",
            "side_compton_fov_pass_rate",
            "active_veto_rejection_fraction_count",
            "compton_fov_rejection_fraction_vs_active_count",
            "total_rejection_fraction_count",
            "active_veto_rejection_fraction_rate",
            "compton_fov_rejection_fraction_vs_active_rate",
            "total_rejection_fraction_rate",
            "final_survival_fraction_vs_raw_rate",
            "side_compton_class_counts_json",
            "rate_units",
        ],
    )
    write_csv(
        WORK / "veto_efficiency_by_source_window_stage.csv",
        veto_rows,
        [
            "family",
            "window",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
            "raw_rate",
            "active_veto_pass_rate",
            "side_compton_fov_pass_rate",
            "active_veto_rejection_fraction_count",
            "compton_fov_rejection_fraction_vs_active_count",
            "total_rejection_fraction_count",
            "active_veto_rejection_fraction_rate",
            "compton_fov_rejection_fraction_vs_active_rate",
            "total_rejection_fraction_rate",
            "final_survival_fraction_vs_raw_rate",
            "side_compton_class_counts_json",
            "rate_units",
        ],
    )
    write_csv(
        WORK / "veto_efficiency_by_ingress_region.csv",
        veto_region_rows,
        [
            "family",
            "window",
            "entry_region",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
            "raw_rate",
            "active_veto_pass_rate",
            "side_compton_fov_pass_rate",
            "active_veto_rejection_fraction_count",
            "compton_fov_rejection_fraction_vs_active_count",
            "total_rejection_fraction_count",
            "active_veto_rejection_fraction_rate",
            "compton_fov_rejection_fraction_vs_active_rate",
            "total_rejection_fraction_rate",
        ],
    )
    write_csv(
        WORK / "side_compton_class_counts.csv",
        side_class_rows,
        ["family", "window", "side_compton_class", "events", "rate", "survives_reject_policy_keep"],
    )
    write_json(
        WORK / "veto_efficiency_summary.json",
        {
            "status": "PASS_VETO_EFFICIENCY_AUDIT_CURRENT_GEO_OPT",
            "generated_at_utc": now_utc(),
            "method": {
                "active_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
                "active_volume_rule": "CsI/BGO/ACTIVE_SHIELD/CEBR3 plus GeoOpt_S1_PlasticFullWrap*.",
                "compton_fov_algorithm": rel(STEP05_SCRIPT),
                "side_entry_bridge": rel(STEP09_BRIDGE),
            },
            "summaries": veto_summaries,
            "csv_rows": veto_rows,
            "by_ingress_region_rows": veto_region_rows,
            "side_compton_class_rows": side_class_rows,
        },
    )
    write_markdown(veto_rows, ingress_rows, event_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
