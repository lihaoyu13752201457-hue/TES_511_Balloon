#!/usr/bin/env python3
"""Build event-level W2 veto-failure diagnostics for S1 and S2b."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
S1_PROMPT_DIR = ROOT / "runs/geometry_optimization_20260704/step02_instant_geo_opt_s1_bpe_w5_fullstat_v1"
S2B_PROMPT_DIR = ROOT / "runs/geometry_optimization_20260704/s2b_cryo_shell_45deg_eqstats_prompt_eplus_n_20260708"
S1_ATM_SIM = ROOT / "runs/geometry_optimization_20260704/p2_atm511_sidecar_s1_nominal_geo_opt_s1_bpe_w5_20260708/Atm511SidecarS1Nominal3M_GeoOptS1BpeW5.inc1.id1.sim.gz"
S2B_ATM_SIM = ROOT / "runs/geometry_optimization_20260704/s2b_cryo_shell_45deg_atm511_sidecar_3m_20260708/Atm511SidecarS2bCryoShell3M.inc1.id1.sim.gz"

W2 = (510.58, 511.42)
ACTIVE_THRESHOLD_KEV = 50.0
ID_RE = re.compile(r"^ID\s+(\d+)")
CC_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)
IA_RE = re.compile(r"^IA\s+(\S+)\s+")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_step05():
    spec = importlib.util.spec_from_file_location("w2_veto_failure_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.STEP09_SUMMARY = (
        ROOT
        / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
        / "step09_optics_bridge_summary.json"
    )
    return mod


def category(vol: str) -> str:
    upper = vol.upper()
    if TP_RE.match(vol):
        return "tes"
    if upper.startswith("GEOOPT_S1_PLASTICFULLWRAP"):
        return "s1_plastic"
    if upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC"):
        return "s2b_plastic"
    if upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper:
        return "legacy_active"
    return "passive_other"


def parse_hit(line: str) -> tuple[str, float, float, float, float, dict[str, str]] | None:
    m = CC_RE.match(line.strip())
    if not m:
        return None
    kv = dict(KV_RE.findall(m.group(2)))
    try:
        return m.group(1), float(kv["edep_keV"]), float(kv["x"]), float(kv["y"]), float(kv["z"]), kv
    except Exception:
        return None


def hits_from_pix(pix: dict[str, dict[str, Any]]) -> tuple[float, list[Any]]:
    tes_total = 0.0
    hits = []
    for uid, rec in sorted(pix.items()):
        e = float(rec["e"])
        if e <= 0.0:
            continue
        tes_total += e
        hits.append(
            SimpleNamespace(
                x=float(rec["wx"] / e),
                y=float(rec["wy"] / e),
                z=float(rec["wz"] / e),
                e=e,
                pixel_uid=uid,
                layer=int(rec["layer"]),
            )
        )
    return tes_total, hits


def find_w2_candidates(sim: Path) -> dict[int, dict[str, Any]]:
    candidates: dict[int, dict[str, Any]] = {}
    cur_id: int | None = None
    pix: dict[str, dict[str, Any]] = {}

    def flush() -> None:
        nonlocal cur_id, pix
        if cur_id is None:
            return
        tes_total, hits = hits_from_pix(pix)
        if W2[0] <= tes_total < W2[1]:
            candidates[int(cur_id)] = {
                "tes_total_keV": float(tes_total),
                "tes_hit_count": len(hits),
                "tes_hits": hits,
            }
        cur_id = None
        pix = {}

    with gzip.open(sim, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            mid = ID_RE.match(line)
            if mid:
                cur_id = int(mid.group(1))
                pix = {}
                continue
            if not line.startswith("CC HIT TP_L"):
                continue
            hit = parse_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z, _kv = hit
            mtp = TP_RE.match(vol)
            if not mtp:
                continue
            rec = pix.setdefault(
                vol,
                {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(mtp.group("layer"))},
            )
            rec["e"] += edep
            rec["wx"] += edep * x
            rec["wy"] += edep * y
            rec["wz"] += edep * z
    flush()
    return candidates


def attach_event_details(sim: Path, candidates: dict[int, dict[str, Any]], step05, geometry: str, particle: str) -> list[dict[str, Any]]:
    if not candidates:
        return []
    disk = step05.side_entry_disk()
    rows: list[dict[str, Any]] = []
    cur_id: int | None = None
    keep = False
    sums: Counter[str] = Counter()
    first_hit: dict[str, Any] | None = None
    top_vols: Counter[str] = Counter()
    ia_counts: Counter[str] = Counter()
    ia_init = ""
    ia_first_noninit = ""

    def flush() -> None:
        nonlocal cur_id, keep, sums, first_hit, top_vols, ia_counts, ia_init, ia_first_noninit
        if cur_id is None or not keep:
            cur_id = None
            keep = False
            sums = Counter()
            first_hit = None
            top_vols = Counter()
            ia_counts = Counter()
            ia_init = ""
            ia_first_noninit = ""
            return
        rec = candidates[int(cur_id)]
        tes_hits = rec["tes_hits"]
        side_keep, cls = step05.side_keep_from_hits(tes_hits, disk, "keep")
        legacy = float(sums["legacy_active"])
        s1_plastic = float(sums["s1_plastic"])
        s2b_plastic = float(sums["s2b_plastic"])
        plastic = s1_plastic + s2b_plastic
        active_total = legacy + plastic
        nonplastic_veto = legacy >= ACTIVE_THRESHOLD_KEV
        plastic_veto = plastic >= ACTIVE_THRESHOLD_KEV
        active_veto = active_total >= ACTIVE_THRESHOLD_KEV
        compton_veto = cls == "veto"
        final_pass = (not active_veto) and side_keep
        top = top_vols.most_common(8)
        rows.append(
            {
                "geometry": geometry,
                "particle": particle,
                "source_file": rel(sim),
                "local_id": int(cur_id),
                "tes_total_keV": rec["tes_total_keV"],
                "tes_hit_count": rec["tes_hit_count"],
                "legacy_active_keV": legacy,
                "s1_plastic_keV": s1_plastic,
                "s2b_plastic_keV": s2b_plastic,
                "plastic_skin_keV": plastic,
                "active_total_keV": active_total,
                "nonplastic_active_veto": nonplastic_veto,
                "plastic_skin_veto": plastic_veto,
                "active_veto": active_veto,
                "side_compton_class": cls,
                "compton_fov_veto": compton_veto,
                "final_pass": final_pass,
                "first_hit_volume": "" if first_hit is None else first_hit["vol"],
                "first_hit_category": "" if first_hit is None else first_hit["category"],
                "first_hit_edep_keV": "" if first_hit is None else first_hit["edep"],
                "first_hit_sec": "" if first_hit is None else first_hit["sec"],
                "first_hit_proc": "" if first_hit is None else first_hit["proc"],
                "ia_init": ia_init[:220],
                "ia_first_noninit": ia_first_noninit[:220],
                "ia_process_counts": json.dumps(dict(sorted(ia_counts.items())), sort_keys=True),
                "top_hit_volumes": "; ".join(f"{vol}:{edep:.3g}" for vol, edep in top),
            }
        )
        cur_id = None
        keep = False
        sums = Counter()
        first_hit = None
        top_vols = Counter()
        ia_counts = Counter()
        ia_init = ""
        ia_first_noninit = ""

    with gzip.open(sim, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            mid = ID_RE.match(line)
            if mid:
                cur_id = int(mid.group(1))
                keep = cur_id in candidates
                sums = Counter()
                first_hit = None
                top_vols = Counter()
                ia_counts = Counter()
                ia_init = ""
                ia_first_noninit = ""
                continue
            if not keep:
                continue
            if line.startswith("IA "):
                m = IA_RE.match(line)
                if m:
                    proc = m.group(1)
                    ia_counts[proc] += 1
                    if proc == "INIT" and not ia_init:
                        ia_init = line
                    elif proc != "INIT" and not ia_first_noninit:
                        ia_first_noninit = line
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parse_hit(line)
            if hit is None:
                continue
            vol, edep, _x, _y, _z, kv = hit
            cat = category(vol)
            sums[cat] += edep
            if cat != "tes":
                top_vols[vol] += edep
            if first_hit is None and cat != "tes":
                first_hit = {
                    "vol": vol,
                    "category": cat,
                    "edep": edep,
                    "sec": kv.get("sec", ""),
                    "proc": kv.get("sproc") or kv.get("cproc", ""),
                }
    flush()
    return rows


def prompt_sims(geometry: str, particle: str) -> list[Path]:
    base = S1_PROMPT_DIR if geometry == "S1" else S2B_PROMPT_DIR
    return sorted(base.glob(f"Background_{particle}_fullsphere20_*.sim.gz"))


def scan_sim_single_pass(sim: Path, step05, geometry: str, particle: str) -> list[dict[str, Any]]:
    disk = step05.side_entry_disk()
    rows: list[dict[str, Any]] = []
    cur_id: int | None = None
    pix: dict[str, dict[str, Any]] = {}
    sums: Counter[str] = Counter()
    first_hit: dict[str, Any] | None = None
    top_vols: Counter[str] = Counter()
    ia_counts: Counter[str] = Counter()
    ia_init = ""
    ia_first_noninit = ""

    def reset() -> None:
        nonlocal cur_id, pix, sums, first_hit, top_vols, ia_counts, ia_init, ia_first_noninit
        cur_id = None
        pix = {}
        sums = Counter()
        first_hit = None
        top_vols = Counter()
        ia_counts = Counter()
        ia_init = ""
        ia_first_noninit = ""

    def flush() -> None:
        nonlocal cur_id, pix, sums, first_hit, top_vols, ia_counts, ia_init, ia_first_noninit
        if cur_id is None:
            return
        tes_total, tes_hits = hits_from_pix(pix)
        if not (W2[0] <= tes_total < W2[1]):
            reset()
            return
        side_keep, cls = step05.side_keep_from_hits(tes_hits, disk, "keep")
        legacy = float(sums["legacy_active"])
        s1_plastic = float(sums["s1_plastic"])
        s2b_plastic = float(sums["s2b_plastic"])
        plastic = s1_plastic + s2b_plastic
        active_total = legacy + plastic
        nonplastic_veto = legacy >= ACTIVE_THRESHOLD_KEV
        plastic_veto = plastic >= ACTIVE_THRESHOLD_KEV
        active_veto = active_total >= ACTIVE_THRESHOLD_KEV
        compton_veto = cls == "veto"
        top = top_vols.most_common(8)
        rows.append(
            {
                "geometry": geometry,
                "particle": particle,
                "source_file": rel(sim),
                "local_id": int(cur_id),
                "tes_total_keV": float(tes_total),
                "tes_hit_count": len(tes_hits),
                "legacy_active_keV": legacy,
                "s1_plastic_keV": s1_plastic,
                "s2b_plastic_keV": s2b_plastic,
                "plastic_skin_keV": plastic,
                "active_total_keV": active_total,
                "nonplastic_active_veto": nonplastic_veto,
                "plastic_skin_veto": plastic_veto,
                "active_veto": active_veto,
                "side_compton_class": cls,
                "compton_fov_veto": compton_veto,
                "final_pass": (not active_veto) and side_keep,
                "first_hit_volume": "" if first_hit is None else first_hit["vol"],
                "first_hit_category": "" if first_hit is None else first_hit["category"],
                "first_hit_edep_keV": "" if first_hit is None else first_hit["edep"],
                "first_hit_sec": "" if first_hit is None else first_hit["sec"],
                "first_hit_proc": "" if first_hit is None else first_hit["proc"],
                "ia_init": ia_init[:220],
                "ia_first_noninit": ia_first_noninit[:220],
                "ia_process_counts": json.dumps(dict(sorted(ia_counts.items())), sort_keys=True),
                "top_hit_volumes": "; ".join(f"{vol}:{edep:.3g}" for vol, edep in top),
            }
        )
        reset()

    with gzip.open(sim, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            mid = ID_RE.match(line)
            if mid:
                flush()
                cur_id = int(mid.group(1))
                pix = {}
                sums = Counter()
                first_hit = None
                top_vols = Counter()
                ia_counts = Counter()
                ia_init = ""
                ia_first_noninit = ""
                continue
            if cur_id is None:
                continue
            if line.startswith("IA "):
                m = IA_RE.match(line)
                if m:
                    proc = m.group(1)
                    ia_counts[proc] += 1
                    if proc == "INIT" and not ia_init:
                        ia_init = line
                    elif proc != "INIT" and not ia_first_noninit:
                        ia_first_noninit = line
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parse_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z, kv = hit
            cat = category(vol)
            if cat == "tes":
                mtp = TP_RE.match(vol)
                if mtp:
                    rec = pix.setdefault(
                        vol,
                        {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(mtp.group("layer"))},
                    )
                    rec["e"] += edep
                    rec["wx"] += edep * x
                    rec["wy"] += edep * y
                    rec["wz"] += edep * z
                continue
            sums[cat] += edep
            top_vols[vol] += edep
            if first_hit is None:
                first_hit = {
                    "vol": vol,
                    "category": cat,
                    "edep": edep,
                    "sec": kv.get("sec", ""),
                    "proc": kv.get("sproc") or kv.get("cproc", ""),
                }
    flush()
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "geometry",
        "particle",
        "source_file",
        "local_id",
        "tes_total_keV",
        "tes_hit_count",
        "legacy_active_keV",
        "s1_plastic_keV",
        "s2b_plastic_keV",
        "plastic_skin_keV",
        "active_total_keV",
        "nonplastic_active_veto",
        "plastic_skin_veto",
        "active_veto",
        "side_compton_class",
        "compton_fov_veto",
        "final_pass",
        "first_hit_volume",
        "first_hit_category",
        "first_hit_edep_keV",
        "first_hit_sec",
        "first_hit_proc",
        "ia_init",
        "ia_first_noninit",
        "ia_process_counts",
        "top_hit_volumes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in sorted({(r["geometry"], r["particle"]) for r in rows}):
        g, p = key
        group = [r for r in rows if r["geometry"] == g and r["particle"] == p]
        final = [r for r in group if r["final_pass"]]
        active_pass = [r for r in group if not r["active_veto"]]
        out_key = f"{g}_{p}"
        out[out_key] = {
            "w2_raw_events": len(group),
            "active_vetoed_events": sum(1 for r in group if r["active_veto"]),
            "active_veto_pass_events": len(active_pass),
            "compton_fov_veto_events_after_active_pass": sum(1 for r in active_pass if r["compton_fov_veto"]),
            "final_pass_events": len(final),
            "final_side_compton_class_counts": dict(Counter(str(r["side_compton_class"]) for r in final)),
            "final_tes_hit_count_counts": dict(Counter(str(r["tes_hit_count"]) for r in final)),
            "final_active_total_bins": {
                "zero": sum(1 for r in final if float(r["active_total_keV"]) == 0.0),
                "gt0_lt50": sum(1 for r in final if 0.0 < float(r["active_total_keV"]) < ACTIVE_THRESHOLD_KEV),
                "gte50": sum(1 for r in final if float(r["active_total_keV"]) >= ACTIVE_THRESHOLD_KEV),
            },
            "final_plastic_bins": {
                "zero": sum(1 for r in final if float(r["plastic_skin_keV"]) == 0.0),
                "gt0_lt50": sum(1 for r in final if 0.0 < float(r["plastic_skin_keV"]) < ACTIVE_THRESHOLD_KEV),
                "gte50": sum(1 for r in final if float(r["plastic_skin_keV"]) >= ACTIVE_THRESHOLD_KEV),
            },
            "final_legacy_active_bins": {
                "zero": sum(1 for r in final if float(r["legacy_active_keV"]) == 0.0),
                "gt0_lt50": sum(1 for r in final if 0.0 < float(r["legacy_active_keV"]) < ACTIVE_THRESHOLD_KEV),
                "gte50": sum(1 for r in final if float(r["legacy_active_keV"]) >= ACTIVE_THRESHOLD_KEV),
            },
            "final_first_hit_category_counts": dict(Counter(str(r["first_hit_category"]) for r in final)),
            "final_first_hit_volume_top10": dict(Counter(str(r["first_hit_volume"]) for r in final).most_common(10)),
        }
    return out


def main() -> int:
    step05 = load_step05()
    rows: list[dict[str, Any]] = []
    for geometry in ("S1", "S2b"):
        for particle in ("eplus", "n"):
            for sim in prompt_sims(geometry, particle):
                rows.extend(scan_sim_single_pass(sim, step05, geometry, particle))
        sim = S1_ATM_SIM if geometry == "S1" else S2B_ATM_SIM
        rows.extend(scan_sim_single_pass(sim, step05, geometry, "atm511"))

    csv_path = WORK / "w2_veto_failure_events.csv"
    json_path = WORK / "w2_veto_failure_summary.json"
    write_csv(csv_path, rows)
    summary = {
        "status": "PASS_W2_VETO_FAILURE_AUDIT",
        "window_keV": list(W2),
        "active_threshold_keV": ACTIVE_THRESHOLD_KEV,
        "rows": len(rows),
        "summary": summarize(rows),
        "event_csv": rel(csv_path),
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "rows": len(rows), "csv": rel(csv_path), "summary": rel(json_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
