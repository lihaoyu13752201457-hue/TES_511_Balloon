#!/usr/bin/env python3
"""Re-parse the FULL weighted RPIP production record for exact-position sampling.

Addresses review Findings #1/#3: the 50k reservoir sample misses 992 low-activity
species (0.76% activity gap) and carries no upstream `wfile` (gamma vs non-gamma
1/div) weight. This script re-scans the buildup SIM files and emits the complete
delayed-relevant RPIP record, one row per `CC IP RP` point, keeping the fields a
faithful production-grade exact-point source needs:

    VN, ZA, exc_keV, wfile, source_file, x_cm, y_cm, z_cm, nuclide, in_fixed_inventory

`wfile` mirrors `makedecaysourcewithplot_rpip.py`: gamma files weight 1.0,
non-gamma files weight 1/non_gamma_div (production used 8). canon_vn matches the
upstream parser. Positions are kept in cm (SIM native; PointSource beam wants cm).

All outputs land in this test directory (tests/realpos_delayed_smoke/outputs/);
nothing in the production Step03 tree is touched.

Usage:
    python3 reparse_full_rpip_table.py [--limit-files N] [--non-gamma-div 8] [--workers W]
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import multiprocessing as mp
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "outputs"
BUILDUP = ROOT / "runs" / "step02_buildup_equiv2602_aligned"
INVENTORY = (
    ROOT
    / "stepwise_maintenance"
    / "step03_delay_source"
    / "source_snapshots"
    / "activation_inventory_day15.csv"
)
FIXED_SOURCE = (
    ROOT
    / "runs"
    / "step02_delay_fix_equiv2602_aligned"
    / "activation_decay_day15_groundstate_fixed.source"
)

TABLE_OUT = OUT / "full_weighted_rpip_table.csv"
SUMMARY_OUT = OUT / "full_weighted_rpip_summary.json"

SYMBOLS = [
    None, "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg",
    "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr",
    "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf",
    "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po",
]

TAG_RE = re.compile(r"Background_([^_]+)_", re.IGNORECASE)
RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP = re.compile(r"^TP_L(?P<l>\d+)_\d+$", re.I)
RE_TESPIX = re.compile(r"^TES_Pixel_L(?P<l>\d+)$", re.I)
RE_COLLBAR = re.compile(r"^(CollBar[XY])_\d+$", re.I)
_NUM = r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
IP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    rf"(?P<x>{_NUM})\s+(?P<y>{_NUM})\s+(?P<z>{_NUM})\s+"
    rf"(?P<za>\d+)\s+(?P<exc>{_NUM})\s+(?P<t>{_NUM})"
)


def canon_vn(vn: str) -> str:
    if not vn:
        return "Other"
    n = str(vn)
    m = RE_SEG_SHIELD.match(n)
    if m:
        return m.group(1)
    m = RE_TESPIX.match(n)
    if m:
        return f"TES_L{int(m.group('l'))}"
    if n.startswith("TES_L"):
        return n
    m = RE_TP.match(n)
    if m:
        return f"TES_L{int(m.group('l'))}"
    m = RE_COLLBAR.match(n)
    if m:
        return m.group(1)
    if n in ("Cu_Base", "Cu_SupportPole", "CU_BASE", "CU_SUPPORT", "Copper"):
        return "Copper"
    if n in ("Collimator", "CollimatorVac", "CollimatorEnvelope"):
        return "CollimatorVac"
    if "window" in n.lower() or n.lower().startswith("win"):
        return "Window"
    return n


def nuclide_label(za: int) -> str:
    z, a = za // 1000, za % 1000
    return f"{SYMBOLS[z]}-{a}" if 0 < z < len(SYMBOLS) else str(za)


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def load_fixed_inventory_keys() -> set[tuple[str, int]]:
    """(VN, ZA) keys that survive into the ground-state-fixed source blocks."""
    keys: set[tuple[str, int]] = set()
    name_re = re.compile(r"^S_(?P<vn>.+)_(?P<za>\d+)_z\d+\.ParticleType\s+(?P<za2>\d+)")
    with FIXED_SOURCE.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            m = name_re.match(raw.strip())
            if m:
                keys.add((m.group("vn"), int(m.group("za2"))))
    return keys


def parse_one(args_tuple) -> dict:
    fp_str, non_gamma_div = args_tuple
    fp = Path(fp_str)
    tag = (TAG_RE.search(fp.name).group(1).lower() if TAG_RE.search(fp.name) else "unknown")
    wfile = 1.0 if tag == "gamma" else 1.0 / float(non_gamma_div)
    rows = []
    n_cc_ip = 0
    with open_text(fp) as handle:
        for raw in handle:
            if not raw.startswith("CC IP RP"):
                if raw.startswith("CC IP"):
                    n_cc_ip += 1
                continue
            n_cc_ip += 1
            m = IP_RE.match(raw.strip())
            if not m:
                continue
            za = int(m.group("za"))
            exc = float(m.group("exc"))
            if abs(exc) < 1e-6:
                exc = 0.0
            rows.append(
                (
                    canon_vn(m.group("vn")),
                    za,
                    exc,
                    wfile,
                    fp.name,
                    float(m.group("x")),
                    float(m.group("y")),
                    float(m.group("z")),
                )
            )
    return {"file": fp.name, "tag": tag, "wfile": wfile, "n_cc_ip": n_cc_ip, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-files", type=int, default=0, help="0 = all 60 files")
    ap.add_argument("--non-gamma-div", type=float, default=8.0)
    ap.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 2))
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(BUILDUP.glob("*.sim.gz"))
    if args.limit_files > 0:
        files = files[: args.limit_files]
    if not files:
        raise SystemExit(f"No SIM files in {BUILDUP}")

    fixed_keys = load_fixed_inventory_keys()
    print(f"[info] {len(files)} files, {len(fixed_keys)} fixed-source (VN,ZA) keys, "
          f"non_gamma_div={args.non_gamma_div}, workers={args.workers}", flush=True)

    t0 = time.time()
    ctx = mp.get_context("fork") if sys.platform.startswith("linux") else mp.get_context("spawn")
    task_args = [(str(f), args.non_gamma_div) for f in files]
    results = []
    with ctx.Pool(processes=args.workers) as pool:
        for i, res in enumerate(pool.imap_unordered(parse_one, task_args), 1):
            results.append(res)
            print(f"[{i:02d}/{len(files):02d}] {res['file']}: {len(res['rows'])} RP rows "
                  f"(wfile={res['wfile']:.4f})", flush=True)

    tag_counts: Counter[str] = Counter()
    weighted_yield: dict[tuple, float] = defaultdict(float)
    total_cc_ip = 0
    n_rows = 0
    n_rows_in_fixed = 0
    with TABLE_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["VN", "ZA", "exc_keV", "wfile", "source_file",
                         "x_cm", "y_cm", "z_cm", "nuclide", "in_fixed_inventory"])
        for res in results:
            total_cc_ip += res["n_cc_ip"]
            tag_counts[res["tag"]] += len(res["rows"])
            for vn, za, exc, wfile, src, x, y, z in res["rows"]:
                in_fixed = (vn, za) in fixed_keys
                n_rows += 1
                n_rows_in_fixed += int(in_fixed)
                weighted_yield[(vn, za, exc)] += wfile
                writer.writerow([vn, za, f"{exc:.6g}", f"{wfile:.6f}", src,
                                 f"{x:.6f}", f"{y:.6f}", f"{z:.6f}",
                                 nuclide_label(za), int(in_fixed)])

    summary = {
        "files_parsed": len(files),
        "non_gamma_div": args.non_gamma_div,
        "total_cc_ip_lines_seen": total_cc_ip,
        "rp_rows_written": n_rows,
        "rp_rows_in_fixed_inventory": n_rows_in_fixed,
        "distinct_VN_ZA_exc": len(weighted_yield),
        "rp_rows_by_tag": dict(tag_counts),
        "elapsed_s": round(time.time() - t0, 1),
        "table": str(TABLE_OUT),
        "note": (
            "Full weighted RPIP record (cm). wfile = 1.0 gamma else 1/non_gamma_div. "
            "in_fixed_inventory flags (VN,ZA) present in the ground-state-fixed source "
            "blocks; use it to align exact-point sampling with the fixed Step03 semantics."
        ),
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\n[OK] wrote {TABLE_OUT}")
    print(f"[OK] wrote {SUMMARY_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
