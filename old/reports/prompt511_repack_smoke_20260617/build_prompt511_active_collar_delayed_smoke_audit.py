#!/usr/bin/env python3
"""Summarize active-collar delayed activation and W2 response smoke."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_repack_smoke_20260617"

BASE_PROXY = WORK / "build_prompt511_repack_l1_proxy.py"
STEP05_TOOL = ROOT / "code/tools/build_v3p5_centerfinger_step05_l1_response.py"

ACTIVE_FIX_DIR = WORK / "runs/active_collar_bgo_delay_fix_smoke_g1m_r2"
ACTIVE_CORR = ACTIVE_FIX_DIR / "groundstate_activity_corrections.csv"
ACTIVE_FIX_SUMMARY = ACTIVE_FIX_DIR / "source_fix_summary.json"
ACTIVE_DELAYED_SIM = (
    WORK
    / "runs/active_collar_bgo_delayed_transport_smoke_g1m_r2"
    / "DelayedDecayRPIPActiveCollarBgoSmokeGroundStateFixed.inc1.id1.sim.gz"
)
ACTIVE_BGO_PROMPT_L1 = WORK / "prompt511_active_collar_bgo_l1_proxy_summary.json"
ACTIVE_BGO_FOCUS = WORK / "prompt511_active_collar_bgo_focus_smoke_summary.json"

CURRENT_CORR = (
    ROOT
    / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613"
    / "groundstate_activity_corrections.csv"
)
CURRENT_FIX_SUMMARY = (
    ROOT
    / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613"
    / "source_fix_summary.json"
)
CURRENT_STEP05_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/"
    / "outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613_l1"
    / "step05_v3p5_centerfinger_l1_response_summary.json"
)

SUMMARY_JSON = WORK / "prompt511_active_collar_bgo_delayed_smoke_summary.json"
SUMMARY_MD = WORK / "prompt511_active_collar_bgo_delayed_smoke_summary.md"
W2_KEY = "w2_510p58_511p42"
ID_RE = re.compile(r"^ID\s+(\d+)")
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_module(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def inspect_sim(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "SE": 0,
        "ID": 0,
        "TS": 0,
        "TE_s": None,
        "geometry": "",
    }
    if not path.exists():
        return info

    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if raw.startswith("SE"):
                info["SE"] += 1
            elif raw.startswith("ID"):
                info["ID"] += 1
            elif raw.startswith("TS"):
                info["TS"] += 1
            elif raw.startswith("TE "):
                parts = raw.split()
                if len(parts) >= 2:
                    info["TE_s"] = float(parts[1])
            elif raw.startswith("Geometry "):
                info["geometry"] = raw.strip().split(" ", 1)[1].strip()
    return info


def material_category(vn: str, nuclide: str) -> str:
    upper_vn = vn.upper()
    element = nuclide.split("-", 1)[0]
    if upper_vn.startswith("BGO_ACTIVE_SHIELD_PROMPT511_COLLAR"):
        return "BGO_collar"
    if upper_vn.startswith("CSI"):
        return "CsI"
    if (
        upper_vn.startswith("PASSIVE_W")
        or upper_vn.startswith("W_")
        or "_W_" in upper_vn
        or "TUNGSTEN" in upper_vn
    ):
        return "W"
    if "CU" in upper_vn or "COLDPLATE" in upper_vn or element in {"Cu", "Ni"}:
        return "Cu"
    if "AL" in upper_vn or upper_vn == "WINDOW" or element in {"Al", "Mg"}:
        return "Al"
    return "Other"


def load_activity_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            row["new_groundstate_activity_Bq"] = float(row["new_groundstate_activity_Bq"])
            row["old_source_activity_Bq"] = float(row["old_source_activity_Bq"])
            row["RP_yield"] = float(row["RP_yield"])
            rows.append(row)
    return rows


def activity_summary(path: Path) -> dict[str, Any]:
    rows = load_activity_rows(path)
    by_category: dict[str, float] = defaultdict(float)
    by_nuclide: dict[str, float] = defaultdict(float)
    by_bgo_nuclide: dict[str, float] = defaultdict(float)
    by_bgo_volume: dict[str, float] = defaultdict(float)

    for row in rows:
        vn = str(row["VN"])
        nuclide = str(row["nuclide"])
        activity = float(row["new_groundstate_activity_Bq"])
        category = material_category(vn, nuclide)
        by_category[category] += activity
        by_nuclide[nuclide] += activity
        if category == "BGO_collar":
            by_bgo_nuclide[nuclide] += activity
            by_bgo_volume[vn] += activity

    total = sum(float(row["new_groundstate_activity_Bq"]) for row in rows)
    category_rows = [
        {
            "category": key,
            "activity_Bq": value,
            "fraction_of_total": value / total if total > 0.0 else None,
        }
        for key, value in sorted(by_category.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        "csv": rel(path),
        "rows": len(rows),
        "total_activity_from_csv_Bq": total,
        "activity_by_category": category_rows,
        "top_nuclides": top_map(by_nuclide, 12),
        "bgo_collar_activity_Bq": by_category.get("BGO_collar", 0.0),
        "bgo_collar_fraction_of_total": by_category.get("BGO_collar", 0.0) / total if total > 0.0 else None,
        "top_bgo_collar_nuclides": top_map(by_bgo_nuclide, 12),
        "bgo_collar_by_volume": top_map(by_bgo_volume, 12),
    }


def normalize_sim_primary(primary: str) -> str:
    match = re.match(r"^([A-Za-z]+)(\d+)$", primary)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return primary


def selected_volume_activity_compare(
    active_csv: Path,
    current_csv: Path,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    events = diagnostics.get("events") or []
    volumes = sorted(
        {
            str(row.get("first_non_tes_volume") or "")
            for row in events
            if row.get("first_non_tes_volume")
        }
        | {
            str(row.get("top_non_tes_volume") or "")
            for row in events
            if row.get("top_non_tes_volume")
        }
    )
    primaries = sorted(
        {
            normalize_sim_primary(str(row.get("primary_most_common") or ""))
            for row in events
            if row.get("primary_most_common")
        }
    )
    return {
        "volumes_from_selected_events": volumes,
        "nuclides_from_selected_events": primaries,
        "active_collar_smoke": selected_activity_subset(active_csv, volumes, primaries),
        "current_fullstat_reference": selected_activity_subset(current_csv, volumes, primaries),
    }


def selected_activity_subset(path: Path, volumes: list[str], nuclides: list[str]) -> dict[str, Any]:
    rows = load_activity_rows(path)
    volume_set = set(volumes)
    nuclide_set = set(nuclides)
    selected_rows = [row for row in rows if str(row["VN"]) in volume_set]
    selected_nuclide_rows = [
        row for row in selected_rows if str(row["nuclide"]) in nuclide_set
    ]

    by_volume: dict[str, float] = defaultdict(float)
    by_nuclide: dict[str, float] = defaultdict(float)
    by_volume_nuclide: dict[str, float] = defaultdict(float)
    for row in selected_rows:
        activity = float(row["new_groundstate_activity_Bq"])
        by_volume[str(row["VN"])] += activity
        by_nuclide[str(row["nuclide"])] += activity
        by_volume_nuclide[f"{row['VN']}:{row['nuclide']}"] += activity

    total_all_nuclides = sum(float(row["new_groundstate_activity_Bq"]) for row in selected_rows)
    total_selected_nuclides = sum(float(row["new_groundstate_activity_Bq"]) for row in selected_nuclide_rows)
    return {
        "csv": rel(path),
        "matched_rows_all_nuclides": len(selected_rows),
        "matched_rows_selected_nuclides": len(selected_nuclide_rows),
        "selected_volumes_all_nuclides_activity_Bq": total_all_nuclides,
        "selected_volumes_selected_nuclides_activity_Bq": total_selected_nuclides,
        "activity_by_selected_volume": top_map(by_volume, 20),
        "activity_by_selected_nuclide_in_selected_volumes": top_map(by_nuclide, 20),
        "activity_by_selected_volume_nuclide": top_map(by_volume_nuclide, 20),
    }


def top_map(values: dict[str, float], limit: int) -> list[dict[str, Any]]:
    return [
        {"name": name, "activity_Bq": activity}
        for name, activity in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def current_w2_reference() -> dict[str, Any]:
    current = load_json(CURRENT_STEP05_SUMMARY)
    w2 = current["windows"][W2_KEY]
    by = w2["by_stream"]
    phys = w2["physical_reference_flux"]
    return {
        "summary": rel(CURRENT_STEP05_SUMMARY),
        "prompt": by["prompt"],
        "delayed": by["delayed"],
        "science": by["science"],
        "physical_reference_flux": phys,
    }


def poisson_rate_sigma(events: int, te_s: float) -> float | None:
    if events < 0 or te_s <= 0.0:
        return None
    return math.sqrt(float(events)) / te_s


def parse_cc_hit(line: str) -> tuple[str, dict[str, str]] | None:
    match = CC_HIT_RE.match(line.strip())
    if not match:
        return None
    return match.group(1), dict(KV_RE.findall(match.group(2)))


def is_tes_volume(volume: str) -> bool:
    return volume.upper().startswith("TP_L")


def is_active_volume(volume: str) -> bool:
    upper = volume.upper()
    return upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper


def selected_event_diagnostics(sim: Path, selected_ids: list[int]) -> dict[str, Any]:
    wanted = set(int(x) for x in selected_ids)
    if not wanted:
        return {}

    event_rows: list[dict[str, Any]] = []
    by_primary = Counter()
    by_first_non_tes_volume = Counter()
    by_top_non_tes_volume = Counter()
    by_top_non_tes_category = Counter()
    by_material_category = Counter()

    cur_id: int | None = None
    capture = False
    hits: list[tuple[str, float, dict[str, str]]] = []

    def flush() -> None:
        nonlocal cur_id, capture, hits
        if cur_id is None or not capture:
            cur_id = None
            capture = False
            hits = []
            return

        volume_energy: dict[str, float] = defaultdict(float)
        non_tes_energy: dict[str, float] = defaultdict(float)
        prim_counter = Counter()
        sec_counter = Counter()
        proc_counter = Counter()
        active_total = 0.0
        tes_total = 0.0
        first_non_tes = ""
        first_primary = ""

        for volume, edep, kv in hits:
            volume_energy[volume] += edep
            prim = kv.get("prim", "")
            sec = kv.get("sec", "")
            proc = kv.get("cproc", "")
            if prim:
                prim_counter[prim] += 1
            if sec:
                sec_counter[sec] += 1
            if proc:
                proc_counter[proc] += 1
            if is_tes_volume(volume):
                tes_total += edep
            else:
                non_tes_energy[volume] += edep
                if not first_non_tes:
                    first_non_tes = volume
                    first_primary = prim
                if is_active_volume(volume):
                    active_total += edep

        top_non_tes = sorted(non_tes_energy.items(), key=lambda item: (-item[1], item[0]))
        top_volume = top_non_tes[0][0] if top_non_tes else ""
        top_category = material_category(top_volume, "")
        primary = prim_counter.most_common(1)[0][0] if prim_counter else ""
        by_primary[primary] += 1
        by_first_non_tes_volume[first_non_tes] += 1
        by_top_non_tes_volume[top_volume] += 1
        by_top_non_tes_category[top_category] += 1
        for volume in non_tes_energy:
            by_material_category[material_category(volume, "")] += 1

        event_rows.append(
            {
                "local_id": int(cur_id),
                "hit_count": len(hits),
                "tes_total_keV": tes_total,
                "active_total_keV": active_total,
                "primary_most_common": primary,
                "first_non_tes_volume": first_non_tes,
                "first_primary": first_primary,
                "top_non_tes_volume": top_volume,
                "top_non_tes_category": top_category,
                "top_non_tes_edep_keV": top_non_tes[0][1] if top_non_tes else 0.0,
                "top_non_tes_volumes": [
                    {"volume": volume, "edep_keV": edep}
                    for volume, edep in top_non_tes[:5]
                ],
                "primary_counts": dict(prim_counter.most_common(6)),
                "secondary_counts": dict(sec_counter.most_common(6)),
                "process_counts": dict(proc_counter.most_common(6)),
            }
        )

        cur_id = None
        capture = False
        hits = []

    with gzip.open(sim, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match_id = ID_RE.match(line)
            if match_id:
                flush()
                cur_id = int(match_id.group(1))
                capture = cur_id in wanted
                hits = []
                continue
            if not capture or not line.startswith("CC HIT "):
                continue
            parsed = parse_cc_hit(line)
            if parsed is None:
                continue
            volume, kv = parsed
            try:
                edep = float(kv.get("edep_keV", "0"))
            except ValueError:
                edep = 0.0
            hits.append((volume, edep, kv))
    flush()

    return {
        "selected_ids": sorted(wanted),
        "events_found": len(event_rows),
        "by_primary_most_common": dict(by_primary.most_common(12)),
        "by_first_non_tes_volume": dict(by_first_non_tes_volume.most_common(12)),
        "by_top_non_tes_volume": dict(by_top_non_tes_volume.most_common(12)),
        "by_top_non_tes_category": dict(by_top_non_tes_category.most_common(12)),
        "by_non_tes_material_category_presence": dict(by_material_category.most_common(12)),
        "events": sorted(event_rows, key=lambda row: row["local_id"]),
    }


def summarize_active_delayed_w2(sim_info: dict[str, Any]) -> dict[str, Any]:
    te_s = sim_info.get("TE_s")
    if te_s is None or float(te_s) <= 0.0:
        raise RuntimeError(f"Cannot use delayed SIM without positive TE: {ACTIVE_DELAYED_SIM}")
    proxy = load_module("prompt511_active_delayed_smoke_base_proxy", BASE_PROXY)
    step05 = load_module("build_v3p5_centerfinger_step05_l1_response_delayed_smoke", STEP05_TOOL)
    disk = step05.side_entry_disk()
    rate_per_event = 1.0 / float(te_s)
    row = proxy.summarize_sim_stream(step05, ACTIVE_DELAYED_SIM, rate_per_event, disk, "keep")
    final_events = int(row["side_compton_fov_pass_events"])
    active_events = int(row["active_veto_pass_events"])
    raw_events = int(row["raw_events"])
    row["rate_per_event_s-1"] = rate_per_event
    row["raw_rate_counting_1sigma_s-1"] = poisson_rate_sigma(raw_events, float(te_s))
    row["active_veto_pass_rate_counting_1sigma_s-1"] = poisson_rate_sigma(active_events, float(te_s))
    row["side_compton_fov_pass_rate_counting_1sigma_s-1"] = poisson_rate_sigma(final_events, float(te_s))
    row["selected_event_diagnostics"] = selected_event_diagnostics(
        ACTIVE_DELAYED_SIM,
        [int(item["local_id"]) for item in row.get("selected_examples", [])],
    )
    return row


def ratio(num: float, den: float) -> float | None:
    return num / den if den > 0.0 else None


def build_payload() -> dict[str, Any]:
    problems: list[str] = []
    for path in (
        ACTIVE_CORR,
        ACTIVE_FIX_SUMMARY,
        ACTIVE_DELAYED_SIM,
        ACTIVE_BGO_PROMPT_L1,
        CURRENT_CORR,
        CURRENT_FIX_SUMMARY,
        CURRENT_STEP05_SUMMARY,
    ):
        if not path.exists():
            problems.append(f"missing:{rel(path)}")

    active_fix = load_json(ACTIVE_FIX_SUMMARY) if ACTIVE_FIX_SUMMARY.exists() else {}
    current_fix = load_json(CURRENT_FIX_SUMMARY) if CURRENT_FIX_SUMMARY.exists() else {}
    active_activity = activity_summary(ACTIVE_CORR) if ACTIVE_CORR.exists() else {}
    current_activity = activity_summary(CURRENT_CORR) if CURRENT_CORR.exists() else {}
    sim_info = inspect_sim(ACTIVE_DELAYED_SIM)
    if sim_info["exists"] and sim_info["SE"] != sim_info["ID"]:
        problems.append("active_delayed_SE_ID_mismatch")
    if sim_info["exists"] and not sim_info.get("TE_s"):
        problems.append("active_delayed_missing_TE")

    delayed_w2 = summarize_active_delayed_w2(sim_info) if not problems else {}
    selected_activity = (
        selected_volume_activity_compare(
            ACTIVE_CORR,
            CURRENT_CORR,
            delayed_w2.get("selected_event_diagnostics", {}),
        )
        if delayed_w2
        else {}
    )
    current_w2 = current_w2_reference() if CURRENT_STEP05_SUMMARY.exists() else {}
    prompt_l1 = load_json(ACTIVE_BGO_PROMPT_L1) if ACTIVE_BGO_PROMPT_L1.exists() else {}
    focus = load_json(ACTIVE_BGO_FOCUS) if ACTIVE_BGO_FOCUS.exists() else {}

    prompt_projection = (prompt_l1.get("total_prompt_projection") or {}) if prompt_l1 else {}
    projected_prompt = float(prompt_projection.get("projected_total_s-1", 0.0) or 0.0)
    delayed_rate = float(delayed_w2.get("side_compton_fov_pass_rate_s-1", 0.0) or 0.0)
    delayed_sigma = delayed_w2.get("side_compton_fov_pass_rate_counting_1sigma_s-1")
    current_delayed = current_w2.get("delayed", {}) if current_w2 else {}
    current_delayed_rate = float(current_delayed.get("side_compton_fov_pass_rate_s-1", 0.0) or 0.0)

    payload = {
        "status": "FAIL_PROMPT511_ACTIVE_COLLAR_BGO_DELAYED_SMOKE" if problems else "PASS_PROMPT511_ACTIVE_COLLAR_BGO_DELAYED_SMOKE",
        "claim_level": "active-collar delayed activation and Step05-like W2 smoke; not final Step06-Step08 authority",
        "problems": problems,
        "inputs": {
            "active_fix_summary": rel(ACTIVE_FIX_SUMMARY),
            "active_activity_csv": rel(ACTIVE_CORR),
            "active_delayed_sim": rel(ACTIVE_DELAYED_SIM),
            "active_prompt_l1_summary": rel(ACTIVE_BGO_PROMPT_L1),
            "active_focus_summary": rel(ACTIVE_BGO_FOCUS),
            "current_activity_csv": rel(CURRENT_CORR),
            "current_step05_summary": rel(CURRENT_STEP05_SUMMARY),
        },
        "active_source_fix": {
            "old_total_activity_Bq": active_fix.get("old_total_activity_Bq"),
            "new_total_activity_Bq": active_fix.get("new_total_activity_Bq"),
            "source_blocks_in": active_fix.get("source_blocks_in"),
            "source_blocks_removed": active_fix.get("source_blocks_removed"),
            "dat_files": active_fix.get("dat_files"),
        },
        "current_source_fix_reference": {
            "old_total_activity_Bq": current_fix.get("old_total_activity_Bq"),
            "new_total_activity_Bq": current_fix.get("new_total_activity_Bq"),
            "source_blocks_in": current_fix.get("source_blocks_in"),
            "source_blocks_removed": current_fix.get("source_blocks_removed"),
            "dat_files": current_fix.get("dat_files"),
        },
        "activity": {
            "active_collar_smoke": active_activity,
            "current_fullstat_reference": current_activity,
        },
        "active_delayed_transport": sim_info,
        "active_delayed_w2_proxy": delayed_w2,
        "selected_delayed_event_activity_compare": selected_activity,
        "current_w2_reference": current_w2,
        "prompt_projection_reference": prompt_projection,
        "focused_signal_proxy_reference": focus.get("focused_signal_proxy", {}),
        "combined_design_smoke": {
            "active_prompt_projection_s-1": projected_prompt,
            "active_delayed_w2_smoke_s-1": delayed_rate,
            "active_delayed_w2_smoke_counting_1sigma_s-1": delayed_sigma,
            "active_prompt_plus_delayed_smoke_s-1": projected_prompt + delayed_rate,
            "current_authority_prompt_s-1": float((current_w2.get("prompt") or {}).get("side_compton_fov_pass_rate_s-1", 0.0) or 0.0),
            "current_authority_delayed_s-1": current_delayed_rate,
            "current_authority_background_s-1": float(
                (current_w2.get("physical_reference_flux") or {}).get("background_cps", 0.0) or 0.0
            ),
            "active_delayed_over_current_delayed": ratio(delayed_rate, current_delayed_rate),
            "active_prompt_plus_delayed_over_current_background": ratio(
                projected_prompt + delayed_rate,
                float((current_w2.get("physical_reference_flux") or {}).get("background_cps", 0.0) or 0.0),
            ),
            "old_new_geo_re_prompt_total_s-1": float(prompt_projection.get("old_new_geo_re_prompt_total_s-1", 0.0) or 0.0),
            "active_prompt_plus_delayed_over_old_prompt_total": ratio(
                projected_prompt + delayed_rate,
                float(prompt_projection.get("old_new_geo_re_prompt_total_s-1", 0.0) or 0.0),
            ),
        },
        "boundary": [
            "The delayed transport uses the active-collar rebuilt activation source, not an old-inventory replay.",
            "The delayed W2 rate is normalized by 1 / TE_s from the delayed SIM, matching the current Step05 delayed-rate rule.",
            "The active-collar delayed transport is a 100k-trigger smoke from a g1m/r2 buildup inventory; the W2 event count is low.",
            "The delayed W2 central value is high enough to block an old-like combined background claim until a higher-stat delayed closure is done.",
            "Prompt projection, delayed smoke, and focused-signal smoke are not yet a common Step06-Step08 mission authority.",
        ],
    }
    return payload


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def activity_table(summary: dict[str, Any]) -> list[str]:
    lines = ["| category | activity Bq | fraction |", "|---|---:|---:|"]
    for row in summary.get("activity_by_category", []):
        lines.append(
            f"| {row['category']} | {row['activity_Bq']:.6g} | {row['fraction_of_total']:.6g} |"
        )
    return lines


def top_list(rows: list[dict[str, Any]], limit: int = 6) -> str:
    if not rows:
        return ""
    return ", ".join(f"{row['name']} {row['activity_Bq']:.6g} Bq" for row in rows[:limit])


def write_markdown(payload: dict[str, Any]) -> None:
    active_act = payload["activity"]["active_collar_smoke"]
    current_act = payload["activity"]["current_fullstat_reference"]
    delayed = payload["active_delayed_w2_proxy"]
    combo = payload["combined_design_smoke"]
    sim = payload["active_delayed_transport"]
    diagnostics = delayed.get("selected_event_diagnostics", {})
    selected_activity = payload.get("selected_delayed_event_activity_compare", {})

    lines = [
        "# Prompt-511 Active BGO Collar Delayed Smoke",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "This is a delayed activation and Step05-like W2 smoke for the local",
        "active BGO collar. It is not a final Step06--Step08 mission authority.",
        "",
        "## Inputs",
        "",
        f"- active delayed SIM: `{payload['inputs']['active_delayed_sim']}`",
        f"- active activity CSV: `{payload['inputs']['active_activity_csv']}`",
        f"- current Step05 reference: `{payload['inputs']['current_step05_summary']}`",
        f"- current activity CSV: `{payload['inputs']['current_activity_csv']}`",
        "",
        "## Active Delayed Transport",
        "",
        f"- SE/ID: `{sim['SE']} / {sim['ID']}`",
        f"- TE: `{fmt(sim['TE_s'], 9)} s`",
        f"- rate per delayed event: `{fmt(delayed.get('rate_per_event_s-1'), 9)} cps`",
        f"- geometry: `{sim.get('geometry', '')}`",
        "",
        "| W2 stage | events | cps | counting 1sigma cps |",
        "|---|---:|---:|---:|",
        (
            f"| raw line window | {delayed.get('raw_events')} | "
            f"{fmt(delayed.get('raw_rate_s-1'))} | "
            f"{fmt(delayed.get('raw_rate_counting_1sigma_s-1'))} |"
        ),
        (
            f"| active-veto pass | {delayed.get('active_veto_pass_events')} | "
            f"{fmt(delayed.get('active_veto_pass_rate_s-1'))} | "
            f"{fmt(delayed.get('active_veto_pass_rate_counting_1sigma_s-1'))} |"
        ),
        (
            f"| side-Compton/FoV pass | {delayed.get('side_compton_fov_pass_events')} | "
            f"{fmt(delayed.get('side_compton_fov_pass_rate_s-1'))} | "
            f"{fmt(delayed.get('side_compton_fov_pass_rate_counting_1sigma_s-1'))} |"
        ),
        "",
        f"Current authority delayed W2 is `{combo['current_authority_delayed_s-1']:.6g} cps`; "
        f"this smoke gives `{combo['active_delayed_w2_smoke_s-1']:.6g} cps`, "
        f"ratio `{fmt(combo['active_delayed_over_current_delayed'])}`.",
        "",
        "## Activation Inventory",
        "",
        (
            "Active-collar source-fix total activity: "
            f"`{payload['active_source_fix']['new_total_activity_Bq']:.9g} Bq`; "
            "current fullstat source-fix total activity: "
            f"`{payload['current_source_fix_reference']['new_total_activity_Bq']:.9g} Bq`."
        ),
        "",
        "Active-collar smoke activity by material category:",
        "",
    ]
    lines.extend(activity_table(active_act))
    lines.extend(
        [
            "",
            "Current fullstat activity by material category:",
            "",
        ]
    )
    lines.extend(activity_table(current_act))
    lines.extend(
        [
            "",
            (
                "BGO collar self-activation in this smoke: "
                f"`{active_act.get('bgo_collar_activity_Bq', 0.0):.6g} Bq`, "
                f"`{active_act.get('bgo_collar_fraction_of_total', 0.0):.6g}` of total."
            ),
            f"Top BGO-collar nuclides: {top_list(active_act.get('top_bgo_collar_nuclides', []))}.",
            f"Top active-smoke nuclides: {top_list(active_act.get('top_nuclides', []))}.",
            "",
            "Selected delayed W2 final-event diagnostics:",
            "",
            f"- primary nuclides by event: `{diagnostics.get('by_primary_most_common', {})}`",
            f"- first non-TES volumes: `{diagnostics.get('by_first_non_tes_volume', {})}`",
            f"- top non-TES energy volumes: `{diagnostics.get('by_top_non_tes_volume', {})}`",
            f"- top non-TES material categories: `{diagnostics.get('by_top_non_tes_category', {})}`",
            "",
            "Selected Cu-volume activity cross-check:",
            "",
            (
                "- active selected volumes, selected nuclides: "
                f"`{selected_activity.get('active_collar_smoke', {}).get('selected_volumes_selected_nuclides_activity_Bq', 0.0):.6g} Bq`; "
                "current selected volumes, selected nuclides: "
                f"`{selected_activity.get('current_fullstat_reference', {}).get('selected_volumes_selected_nuclides_activity_Bq', 0.0):.6g} Bq`."
            ),
            (
                "- active selected volumes, all nuclides: "
                f"`{selected_activity.get('active_collar_smoke', {}).get('selected_volumes_all_nuclides_activity_Bq', 0.0):.6g} Bq`; "
                "current selected volumes, all nuclides: "
                f"`{selected_activity.get('current_fullstat_reference', {}).get('selected_volumes_all_nuclides_activity_Bq', 0.0):.6g} Bq`."
            ),
            "",
            "## Combined Design-Smoke Read",
            "",
            "| quantity | cps |",
            "|---|---:|",
            f"| active-collar prompt projection | {combo['active_prompt_projection_s-1']:.6g} |",
            f"| active-collar delayed W2 smoke | {combo['active_delayed_w2_smoke_s-1']:.6g} |",
            f"| active prompt + delayed smoke | {combo['active_prompt_plus_delayed_smoke_s-1']:.6g} |",
            f"| current authority background | {combo['current_authority_background_s-1']:.6g} |",
            f"| old new_geo_re prompt total | {combo['old_new_geo_re_prompt_total_s-1']:.6g} |",
            "",
            (
                "Interpretation: the active collar still looks promising for"
                " prompt suppression, but this delayed smoke does not close the"
                " mature-design case. The BGO collar self-activity is small, yet"
                " the delayed W2 central value is about 4x the current delayed"
                " authority and raises prompt+delayed to above the old"
                " new_geo_re prompt total. This may be a smoke-statistics/source"
                " sampling issue, but it is a decision-changing risk until a"
                " higher-stat delayed closure is done."
            ),
            "",
            "Boundary:",
            "",
        ]
    )
    for item in payload["boundary"]:
        lines.append(f"- {item}")
    if payload["problems"]:
        lines.extend(["", "Problems:", ""])
        for item in payload["problems"]:
            lines.append(f"- {item}")
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_json(SUMMARY_JSON, payload)
    write_markdown(payload)
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON)}, indent=2))
    return 0 if not payload["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
