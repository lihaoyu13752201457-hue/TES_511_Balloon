#!/usr/bin/env python3
"""Fast W2 veto failure audit using filtered SIM streams."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
import subprocess
import sys
from collections import Counter
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
TP_PATTERN = r"^(ID |SE$|CC HIT TP_L)"
VETO_PATTERN = (
    r"^(ID |SE$|CC HIT "
    r"(TP_L|CsI_|.*ACTIVE_SHIELD|.*CEBR3|.*BGO|"
    r"GeoOpt_S1_PlasticFullWrap|GeoOpt_S2B_CryoShell_Plastic))"
)


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_step05():
    spec = importlib.util.spec_from_file_location("w2_veto_fast_step05", STEP05_SCRIPT)
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


def iter_filtered(sim: Path, pattern: str):
    gzip_proc = subprocess.Popen(["gzip", "-dc", str(sim)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if gzip_proc.stdout is None:
        raise RuntimeError(f"failed to open gzip for {sim}")
    grep_proc = subprocess.Popen(
        ["grep", "-E", pattern],
        stdin=gzip_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    gzip_proc.stdout.close()
    if grep_proc.stdout is None:
        raise RuntimeError(f"failed to open grep for {sim}")
    try:
        for raw in grep_proc.stdout:
            yield raw.strip()
    finally:
        if grep_proc.stdout is not None:
            grep_proc.stdout.close()
    grep_stderr = grep_proc.stderr.read() if grep_proc.stderr is not None else ""
    gzip_stderr = gzip_proc.stderr.read() if gzip_proc.stderr is not None else ""
    grep_rc = grep_proc.wait()
    gzip_rc = gzip_proc.wait()
    if grep_rc not in (0, 1):
        raise RuntimeError(f"grep failed for {sim}: {grep_rc} {grep_stderr.strip()}")
    if gzip_rc != 0:
        raise RuntimeError(f"gzip failed for {sim}: {gzip_rc} {gzip_stderr.strip()}")


def parse_hit(line: str) -> tuple[str, float, float, float, float] | None:
    m = CC_RE.match(line)
    if not m:
        return None
    kv = dict(KV_RE.findall(m.group(2)))
    try:
        return m.group(1), float(kv["edep_keV"]), float(kv["x"]), float(kv["y"]), float(kv["z"])
    except Exception:
        return None


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
    return "other"


def hits_from_pix(pix: dict[str, dict[str, Any]]) -> tuple[float, list[Any]]:
    total = 0.0
    hits = []
    for uid, rec in sorted(pix.items()):
        e = float(rec["e"])
        if e <= 0:
            continue
        total += e
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
    return total, hits


def candidate_ids(sim: Path) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    cur_id: int | None = None
    pix: dict[str, dict[str, Any]] = {}

    def flush() -> None:
        nonlocal cur_id, pix
        if cur_id is None:
            return
        tes, hits = hits_from_pix(pix)
        if W2[0] <= tes < W2[1]:
            out[int(cur_id)] = {"tes_total_keV": tes, "tes_hits": hits, "tes_hit_count": len(hits)}
        cur_id = None
        pix = {}

    for line in iter_filtered(sim, TP_PATTERN):
        if line == "SE":
            flush()
            continue
        mid = ID_RE.match(line)
        if mid:
            cur_id = int(mid.group(1))
            pix = {}
            continue
        hit = parse_hit(line)
        if hit is None:
            continue
        vol, edep, x, y, z = hit
        mtp = TP_RE.match(vol)
        if not mtp:
            continue
        rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(mtp.group("layer"))})
        rec["e"] += edep
        rec["wx"] += edep * x
        rec["wy"] += edep * y
        rec["wz"] += edep * z
    flush()
    return out


def audit_sim(sim: Path, step05, geometry: str, particle: str) -> list[dict[str, Any]]:
    candidates = candidate_ids(sim)
    if not candidates:
        return []
    disk = step05.side_entry_disk()
    rows: list[dict[str, Any]] = []
    cur_id: int | None = None
    active = False
    sums: Counter[str] = Counter()
    plastic_vols: Counter[str] = Counter()
    legacy_vols: Counter[str] = Counter()

    def flush() -> None:
        nonlocal cur_id, active, sums, plastic_vols, legacy_vols
        if cur_id is None or not active:
            cur_id = None
            active = False
            sums = Counter()
            plastic_vols = Counter()
            legacy_vols = Counter()
            return
        cand = candidates[int(cur_id)]
        keep, cls = step05.side_keep_from_hits(cand["tes_hits"], disk, "keep")
        legacy = float(sums["legacy_active"])
        s1_plastic = float(sums["s1_plastic"])
        s2b_plastic = float(sums["s2b_plastic"])
        plastic = s1_plastic + s2b_plastic
        active_total = legacy + plastic
        rows.append(
            {
                "geometry": geometry,
                "particle": particle,
                "source_file": rel(sim),
                "local_id": int(cur_id),
                "tes_total_keV": float(cand["tes_total_keV"]),
                "tes_hit_count": int(cand["tes_hit_count"]),
                "legacy_active_keV": legacy,
                "s1_plastic_keV": s1_plastic,
                "s2b_plastic_keV": s2b_plastic,
                "plastic_skin_keV": plastic,
                "active_total_keV": active_total,
                "nonplastic_active_veto": legacy >= ACTIVE_THRESHOLD_KEV,
                "plastic_skin_veto": plastic >= ACTIVE_THRESHOLD_KEV,
                "active_veto": active_total >= ACTIVE_THRESHOLD_KEV,
                "side_compton_class": cls,
                "compton_fov_veto": cls == "veto",
                "final_pass": active_total < ACTIVE_THRESHOLD_KEV and keep,
                "plastic_hit_volumes": "; ".join(f"{k}:{v:.3g}" for k, v in plastic_vols.most_common(6)),
                "legacy_hit_volumes": "; ".join(f"{k}:{v:.3g}" for k, v in legacy_vols.most_common(6)),
            }
        )
        cur_id = None
        active = False
        sums = Counter()
        plastic_vols = Counter()
        legacy_vols = Counter()

    for line in iter_filtered(sim, VETO_PATTERN):
        if line == "SE":
            flush()
            continue
        mid = ID_RE.match(line)
        if mid:
            cur_id = int(mid.group(1))
            active = cur_id in candidates
            sums = Counter()
            plastic_vols = Counter()
            legacy_vols = Counter()
            continue
        if not active:
            continue
        hit = parse_hit(line)
        if hit is None:
            continue
        vol, edep, *_ = hit
        cat = category(vol)
        if cat in ("s1_plastic", "s2b_plastic", "legacy_active"):
            sums[cat] += edep
            if cat in ("s1_plastic", "s2b_plastic"):
                plastic_vols[vol] += edep
            else:
                legacy_vols[vol] += edep
    flush()
    return rows


def prompt_sims(geometry: str, particle: str) -> list[Path]:
    base = S1_PROMPT_DIR if geometry == "S1" else S2B_PROMPT_DIR
    return sorted(base.glob(f"Background_{particle}_fullsphere20_*.sim.gz"))


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
        "plastic_hit_volumes",
        "legacy_hit_volumes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for geometry, particle in sorted({(r["geometry"], r["particle"]) for r in rows}):
        group = [r for r in rows if r["geometry"] == geometry and r["particle"] == particle]
        active_pass = [r for r in group if not r["active_veto"]]
        final = [r for r in group if r["final_pass"]]
        out[f"{geometry}_{particle}"] = {
            "w2_raw_events": len(group),
            "active_vetoed_events": sum(1 for r in group if r["active_veto"]),
            "active_veto_pass_events": len(active_pass),
            "compton_fov_veto_after_active_pass_events": sum(1 for r in active_pass if r["compton_fov_veto"]),
            "final_pass_events": len(final),
            "raw_veto_reason_counts_priority": {
                "plastic_skin_veto": sum(1 for r in group if r["plastic_skin_veto"]),
                "nonplastic_active_veto_no_plastic": sum(1 for r in group if (not r["plastic_skin_veto"]) and r["nonplastic_active_veto"]),
                "compton_fov_veto_no_active": sum(1 for r in group if (not r["active_veto"]) and r["compton_fov_veto"]),
                "final_pass": sum(1 for r in group if r["final_pass"]),
            },
            "final_side_compton_class_counts": dict(Counter(str(r["side_compton_class"]) for r in final)),
            "final_tes_hit_count_counts": dict(Counter(str(r["tes_hit_count"]) for r in final)),
            "final_active_total_bins": {
                "zero": sum(1 for r in final if float(r["active_total_keV"]) == 0.0),
                "gt0_lt50": sum(1 for r in final if 0.0 < float(r["active_total_keV"]) < ACTIVE_THRESHOLD_KEV),
            },
            "final_plastic_bins": {
                "zero": sum(1 for r in final if float(r["plastic_skin_keV"]) == 0.0),
                "gt0_lt50": sum(1 for r in final if 0.0 < float(r["plastic_skin_keV"]) < ACTIVE_THRESHOLD_KEV),
            },
            "final_legacy_active_bins": {
                "zero": sum(1 for r in final if float(r["legacy_active_keV"]) == 0.0),
                "gt0_lt50": sum(1 for r in final if 0.0 < float(r["legacy_active_keV"]) < ACTIVE_THRESHOLD_KEV),
            },
        }
    return out


def main() -> int:
    step05 = load_step05()
    rows: list[dict[str, Any]] = []
    for geometry in ("S1", "S2b"):
        for particle in ("eplus", "n"):
            for sim in prompt_sims(geometry, particle):
                rows.extend(audit_sim(sim, step05, geometry, particle))
        sim = S1_ATM_SIM if geometry == "S1" else S2B_ATM_SIM
        rows.extend(audit_sim(sim, step05, geometry, "atm511"))

    csv_path = WORK / "w2_veto_failure_fast_events.csv"
    summary_path = WORK / "w2_veto_failure_fast_summary.json"
    write_csv(csv_path, rows)
    payload = {
        "status": "PASS_W2_VETO_FAILURE_FAST_AUDIT",
        "window_keV": list(W2),
        "active_threshold_keV": ACTIVE_THRESHOLD_KEV,
        "rows": len(rows),
        "event_csv": rel(csv_path),
        "summary": summarize(rows),
    }
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "rows": len(rows), "csv": rel(csv_path), "summary": rel(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
