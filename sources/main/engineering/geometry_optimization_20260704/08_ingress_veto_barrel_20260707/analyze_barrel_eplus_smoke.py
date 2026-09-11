#!/usr/bin/env python3
"""Analyze a W-barrel e+ SIM with CsI-only active veto."""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
RUN_DIR = ROOT / "runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707"
SLOW_SCRIPT = WORK / "build_ingress_veto_audit.py"

WINDOWS = {
    "w2_510p58_511p42": (510.58, 511.42),
    "broad_480_550": (480.0, 550.0),
}
ACTIVE_THRESHOLD_KEV = 50.0
POISSON_ZERO_95_UPPER_EVENTS = 2.995732273553991
ID_RE = re.compile(r"^ID\s+(\d+)")
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")


def load_helpers():
    spec = importlib.util.spec_from_file_location("barrel_ingress_helpers", SLOW_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SLOW_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_obs_time() -> float:
    for line in LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if nums:
                return float(nums[0])
    raise RuntimeError(f"Observation time not found in {LOG}")


def parse_generated() -> int:
    for line in LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Total number of generated particles:" in line:
            nums = re.findall(r"\d+", line)
            if nums:
                return int(nums[-1])
    return 0


def is_csi(vol: str) -> bool:
    return vol.upper().startswith("CSI_")


def parse_hit(line: str) -> dict[str, Any] | None:
    m = CC_HIT_RE.match(line)
    if m is None:
        return None
    vol = m.group(1)
    kv = dict(KV_RE.findall(m.group(2)))
    out: dict[str, Any] = {"volume": vol}
    for key in ("edep_keV", "x", "y", "z"):
        if key in kv:
            try:
                out[key] = float(kv[key])
            except ValueError:
                pass
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default="Background_eplus_barrelW_smoke")
    parser.add_argument("--tag", default="barrel_eplus_smoke")
    parser.add_argument(
        "--scope",
        default="200k e+ smoke only; not full-stat, not 20-day performance",
        help="Reader-facing scope note written to JSON/MD outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sim = RUN_DIR / f"{args.run_name}.inc1.id1.sim.gz"
    log = RUN_DIR / f"cosima_{args.run_name}.log"
    source = RUN_DIR / f"{args.run_name}.source"
    if not sim.exists():
        raise FileNotFoundError(sim)
    h = load_helpers()
    step05 = h.load_step05_module()
    disk = step05.side_entry_disk()
    global LOG
    LOG = log
    obs = parse_obs_time()
    generated = parse_generated()
    rate_per_event = 1.0 / obs if obs > 0 and generated > 0 else 0.0

    tp_re = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)
    rows: list[dict[str, Any]] = []

    cur_id: int | None = None
    init: dict[str, Any] | None = None
    first_hit: dict[str, Any] | None = None
    tes_total = 0.0
    csi_total = 0.0
    pix: dict[str, dict[str, Any]] = {}

    def side_hits() -> list[Any]:
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
        nonlocal cur_id, init, first_hit, tes_total, csi_total, pix
        if cur_id is None:
            return
        entry = h.classify_envelope_entry(
            None if init is None else (init["init_x_cm"], init["init_y_cm"], init["init_z_cm"]),
            None if init is None else (init["dir_x"], init["dir_y"], init["dir_z"]),
        )
        keep = False
        cls = "not_active_veto_pass"
        active_pass = csi_total < ACTIVE_THRESHOLD_KEV
        if active_pass:
            keep, cls = step05.side_keep_from_hits(side_hits(), disk, "keep")
        for window, (emin, emax) in WINDOWS.items():
            if not (emin <= tes_total < emax):
                continue
            row = {
                "local_id": int(cur_id),
                "window": window,
                "tes_total_keV": float(tes_total),
                "csi_active_keV": float(csi_total),
                "stage_raw": True,
                "stage_active_veto_pass": active_pass,
                "stage_side_compton_fov_pass": bool(keep),
                "side_compton_class": cls,
                "first_hit_volume": None if first_hit is None else first_hit.get("volume"),
                "entry_surface_proxy": entry.get("entry_surface_proxy"),
                "entry_region_proxy": entry.get("entry_region_proxy"),
                "rate_s-1": rate_per_event,
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
                        "init_energy_keV": init.get("init_energy_keV"),
                    }
                )
            rows.append(row)
        cur_id = None
        init = None
        first_hit = None
        tes_total = 0.0
        csi_total = 0.0
        pix = {}

    with gzip.open(sim, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                continue
            if cur_id is None:
                continue
            if line.startswith("IA INIT"):
                init = h.parse_ia_init(line)
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parse_hit(line)
            if hit is None:
                continue
            if first_hit is None:
                first_hit = hit
            vol = str(hit["volume"])
            edep = float(hit.get("edep_keV") or 0.0)
            x = float(hit.get("x") or 0.0)
            y = float(hit.get("y") or 0.0)
            z = float(hit.get("z") or 0.0)
            mtp = tp_re.match(vol)
            if mtp:
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(mtp.group("layer"))})
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
                tes_total += edep
            elif is_csi(vol):
                csi_total += edep
        flush()

    summary_rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        wr = [r for r in rows if r["window"] == window]
        raw = len(wr)
        active = sum(1 for r in wr if r["stage_active_veto_pass"])
        final = sum(1 for r in wr if r["stage_side_compton_fov_pass"])
        raw_rate = raw / obs if obs else 0.0
        active_rate = active / obs if obs else 0.0
        final_rate = final / obs if obs else 0.0
        summary_rows.append(
            {
                "window": window,
                "generated_events": generated,
                "observation_time_s": obs,
                "raw_events": raw,
                "active_veto_pass_events": active,
                "side_compton_fov_pass_events": final,
                "raw_rate_s-1": raw_rate,
                "active_veto_pass_rate_s-1": active_rate,
                "side_compton_fov_pass_rate_s-1": final_rate,
                "raw_zero_count_95cl_upper_rate_s-1": POISSON_ZERO_95_UPPER_EVENTS / obs if raw == 0 and obs else "",
                "active_zero_count_95cl_upper_rate_s-1": POISSON_ZERO_95_UPPER_EVENTS / obs if active == 0 and obs else "",
                "final_zero_count_95cl_upper_rate_s-1": POISSON_ZERO_95_UPPER_EVENTS / obs if final == 0 and obs else "",
                "active_veto_rejection_fraction": 1.0 - active / raw if raw else "",
                "compton_fov_rejection_fraction_vs_active": 1.0 - final / active if active else "",
                "total_rejection_fraction": 1.0 - final / raw if raw else "",
                "side_compton_class_counts_json": json.dumps(dict(Counter(str(r["side_compton_class"]) for r in wr if r["stage_active_veto_pass"])), sort_keys=True),
            }
        )

    h.write_csv(
        WORK / f"{args.tag}_summary.csv",
        summary_rows,
        [
            "window",
            "generated_events",
            "observation_time_s",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
            "raw_rate_s-1",
            "active_veto_pass_rate_s-1",
            "side_compton_fov_pass_rate_s-1",
            "raw_zero_count_95cl_upper_rate_s-1",
            "active_zero_count_95cl_upper_rate_s-1",
            "final_zero_count_95cl_upper_rate_s-1",
            "active_veto_rejection_fraction",
            "compton_fov_rejection_fraction_vs_active",
            "total_rejection_fraction",
            "side_compton_class_counts_json",
        ],
    )
    h.write_csv(
        WORK / f"{args.tag}_events.csv",
        rows,
        [
            "local_id",
            "window",
            "tes_total_keV",
            "csi_active_keV",
            "stage_active_veto_pass",
            "stage_side_compton_fov_pass",
            "side_compton_class",
            "first_hit_volume",
            "entry_surface_proxy",
            "entry_region_proxy",
            "rate_s-1",
            "init_x_cm",
            "init_y_cm",
            "init_z_cm",
            "dir_x",
            "dir_y",
            "dir_z",
            "init_energy_keV",
        ],
    )
    payload = {
        "status": "PASS_BARREL_EPLUS_ANALYZED",
        "scope": args.scope,
        "inputs": {
            "source": rel(source),
            "sim": rel(sim),
            "log": rel(log),
            "geometry": "engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup",
        },
        "active_veto_rule": "CsI-only at 50 keV; passive W/Al barrel deposits are not active veto.",
        "rows": summary_rows,
    }
    (WORK / f"{args.tag}_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Barrel W e+ Analysis",
        "",
        "Status: `PASS_BARREL_EPLUS_ANALYZED`",
        "",
        f"Scope: {args.scope}.",
        "",
        "Active veto: CsI only, 50 keV threshold. Passive W/Al barrel deposits are diagnostics only.",
        "",
        "| window | raw | active pass | final pass | raw cps | final cps |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in summary_rows:
        md.append(
            f"| {r['window']} | {r['raw_events']} | {r['active_veto_pass_events']} | {r['side_compton_fov_pass_events']} | "
            f"{float(r['raw_rate_s-1']):.6g} | {float(r['side_compton_fov_pass_rate_s-1']):.6g} |"
        )
    md.extend(
        [
            "",
            "For any zero-count stage, the JSON/CSV include the one-sided 95% Poisson upper rate using 2.995732 events divided by the observation time.",
        ]
    )
    (WORK / f"{args.tag}_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
