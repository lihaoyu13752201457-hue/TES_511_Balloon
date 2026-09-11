#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
check_sim_gz_format_and_ia_contrib.py

Goal:
- Inspect your modified MEGAlib/Cosima sim(.gz) text format (SE/HTsim/IA/CC lines)
- Summarize line-type counts and show representative samples
- Parse IA lines to:
  * extract PROC token
  * extract trackID/parentID/time/x/y/z
  * try to interpret the LAST field as Edep (keV) and accumulate in volumes (TES/BGO/Other)
  * classify volume using bounds.json (same identify_vol logic as your merge_v3)
- Output a single TXT report you can paste back.

Usage example:
  python3 check_sim_gz_format_and_ia_contrib.py \
    --sim "run/*.sim.gz" \
    --bounds XZTES/bounds.json \
    --pos-scale 1 \
    --out report_check_sim.txt \
    --max-sample 8
"""

import argparse
import gzip
import math
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

# -----------------------------
# bounds helpers (copied style)
# -----------------------------
def load_bounds(bounds_path: str) -> dict:
    txt = Path(bounds_path).read_text(encoding="utf-8", errors="ignore").strip()
    if not txt:
        raise SystemExit(f"[ERROR] bounds file empty: {bounds_path}")
    if not txt.lstrip().startswith("{"):
        i0 = txt.find("{")
        i1 = txt.rfind("}")
        if i0 >= 0 and i1 > i0:
            txt = txt[i0:i1 + 1]
    return json.loads(txt)

def in_shell(r, z, s):
    if s["z_out_bot"] <= z <= s["z_in_bot"] and r <= s["r_out"]:
        return True
    if s["z_in_bot"] <= z <= s["z_in_top"] and (s["r_in"] <= r <= s["r_out"]):
        return True
    if s["z_in_top"] <= z <= s["z_out_top"] and (s["hole_r"] <= r <= s["r_out"]):
        return True
    return False

def identify_vol(x, y, z, b):
    r = math.hypot(x, y)

    for name in ["CU_BASE", "CU_SUPPORT"]:
        obj = b.get(name)
        if obj and obj["z_bot"] <= z <= obj["z_top"] and r <= obj["r_max"]:
            return "Copper"

    for i, t in enumerate(b.get("TES_LAYERS", [])):
        if abs(z - t["z_center"]) <= (t["hz"] + 0.05) and r <= (t["r_max"] + 0.05):
            return f"TES_L{i}"

    for w in b.get("WINDOWS", []):
        if abs(z - w["z_center"]) <= (w["thick"] / 2.0 + 0.01) and r <= w["r_max"]:
            return "Window"

    c = b.get("COLLIMATOR")
    if c and abs(z - c["z_center"]) <= (c["hz"] + 0.01) and r <= c["r_max"]:
        return "Collimator"

    for name, s in b.get("SHIELDS", {}).items():
        if in_shell(r, z, s):
            return name

    return "Other"

def open_text_gz(path: str):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore")

# -----------------------------
# IA parsing (robust, exploratory)
# -----------------------------
def parse_ia_line(line: str):
    """
    Your IA lines look like:
      IA BREM 7;2;4;5.06e-09; x; y; z; ... ; ... ; ... ; 5.128

    We don't assume full schema yet.
    We extract:
      proc (token after IA)
      fields[] split by ';'
      track_id = int(fields[0]) if possible
      parent_id = int(fields[1]) if possible
      time = float(fields[3]) if possible
      x,y,z = float(fields[4:7]) if possible
      last = float(fields[-1]) if possible  (often looks like Edep in keV in your file)
    """
    if not line.startswith("IA "):
        return None
    sp = line.strip().split(None, 2)
    if len(sp) < 3:
        return None
    proc = sp[1].strip()
    rest = sp[2].strip()
    fields = [f.strip() for f in rest.split(";")]

    out = {"proc": proc, "fields": fields}
    # optional extracts
    try:
        out["track_id"] = int(float(fields[0]))
    except Exception:
        out["track_id"] = None
    try:
        out["parent_id"] = int(float(fields[1]))
    except Exception:
        out["parent_id"] = None
    try:
        out["time"] = float(fields[3])
    except Exception:
        out["time"] = None
    try:
        out["x"] = float(fields[4])
        out["y"] = float(fields[5])
        out["z"] = float(fields[6])
    except Exception:
        out["x"] = out["y"] = out["z"] = None
    try:
        out["last"] = float(fields[-1])
    except Exception:
        out["last"] = None

    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True, help="Glob for *.sim or *.sim.gz (can be a single file path too)")
    ap.add_argument("--bounds", required=True, help="bounds.json path (mm)")
    ap.add_argument("--pos-scale", type=float, default=1.0, help="Multiply sim xyz by this before identify_vol()")
    ap.add_argument("--out", default="report_check_sim.txt")
    ap.add_argument("--max-sample", type=int, default=8, help="Max sample lines per category to print")
    args = ap.parse_args()

    import glob
    files = sorted(glob.glob(args.sim))
    if not files:
        raise SystemExit(f"[ERROR] no files matched: {args.sim}")

    bounds = load_bounds(args.bounds)
    pos_scale = float(args.pos_scale)

    # line type counters
    type_cnt = Counter()
    samples = defaultdict(list)

    # IA diagnostics
    ia_len_cnt = Counter()
    ia_proc_cnt = Counter()
    ia_proc_in_tes_cnt = Counter()
    ia_proc_in_tes_edep_sum = defaultdict(float)

    ia_primary_in_tes_edep = 0.0
    ia_secondary_in_tes_edep = 0.0
    ia_unknown_in_tes_edep = 0.0

    # For volume distribution of IA lines
    ia_vol_cnt = Counter()

    # quick regex for CC IP RP
    is_cc_ip = lambda s: s.startswith("CC IP")
    is_cc_store = lambda s: s.startswith("CC Storing isotope:")

    # scan
    for fp in files:
        opener = open_text_gz if fp.endswith(".gz") else open
        with opener(fp) as f:
            for line in f:
                if not line:
                    continue
                s = line.rstrip("\n")

                # classify
                if s.startswith("SE"):
                    k = "SE"
                elif s.startswith("HTsim"):
                    k = "HTsim"
                elif s.startswith("IA "):
                    k = "IA"
                elif is_cc_ip(s):
                    k = "CC_IP"
                elif is_cc_store(s):
                    k = "CC_STORE"
                elif s.startswith("VN"):
                    k = "DAT_VN_LIKE"
                elif s.startswith("RP"):
                    k = "DAT_RP_LIKE"
                elif s.startswith("#"):
                    k = "COMMENT"
                else:
                    k = "OTHER"

                type_cnt[k] += 1
                if len(samples[k]) < args.max_sample:
                    samples[k].append(s)

                # IA deep scan
                if k == "IA":
                    ia = parse_ia_line(s)
                    if not ia:
                        continue
                    fields = ia["fields"]
                    ia_len_cnt[len(fields)] += 1
                    ia_proc_cnt[ia["proc"]] += 1

                    # locate volume if xyz exists
                    if ia["x"] is not None:
                        x = ia["x"] * pos_scale
                        y = ia["y"] * pos_scale
                        z = ia["z"] * pos_scale
                        vol = identify_vol(x, y, z, bounds)
                    else:
                        vol = "UnknownXYZ"

                    ia_vol_cnt[vol] += 1

                    # if in TES, accumulate
                    if str(vol).startswith("TES_L"):
                        ia_proc_in_tes_cnt[ia["proc"]] += 1
                        edep = ia["last"]
                        if edep is not None and math.isfinite(edep):
                            ia_proc_in_tes_edep_sum[ia["proc"]] += float(edep)
                            # primary/secondary guess
                            pid = ia.get("parent_id")
                            if pid is None:
                                ia_unknown_in_tes_edep += float(edep)
                            elif pid == 0:
                                ia_primary_in_tes_edep += float(edep)
                            else:
                                ia_secondary_in_tes_edep += float(edep)

    # write report
    out = []
    out.append("=== FILES ===")
    out.append(f"N_files = {len(files)}")
    out.extend([f"  - {fp}" for fp in files[:10]])
    if len(files) > 10:
        out.append(f"  ... ({len(files)-10} more)")

    out.append("\n=== LINE TYPE COUNTS ===")
    for k, v in type_cnt.most_common():
        out.append(f"{k:10s} : {v}")

    out.append("\n=== SAMPLE LINES (truncated) ===")
    for k in ["SE","HTsim","IA","CC_IP","CC_STORE","OTHER"]:
        if k in samples:
            out.append(f"\n--- {k} samples ---")
            for s in samples[k]:
                out.append(s[:260])

    out.append("\n=== IA FIELD-LENGTH DISTRIBUTION ===")
    for L, c in ia_len_cnt.most_common():
        out.append(f"IA fields = {L:3d} : {c}")

    out.append("\n=== IA PROC COUNTS (top 30) ===")
    for proc, c in ia_proc_cnt.most_common(30):
        out.append(f"{proc:8s} : {c}")

    out.append("\n=== IA VOLUME COUNTS (top 30) ===")
    for vol, c in ia_vol_cnt.most_common(30):
        out.append(f"{vol:20s} : {c}")

    out.append("\n=== IA PROC IN TES (counts + sum(last_field)) ===")
    # sort by edep sum desc
    items = sorted(ia_proc_in_tes_edep_sum.items(), key=lambda kv: kv[1], reverse=True)
    for proc, ssum in items[:50]:
        out.append(f"{proc:8s} : n={ia_proc_in_tes_cnt.get(proc,0):8d}  sum_last={ssum:.6g}")

    out.append("\n=== IA TES Edep primary/secondary (using parent_id==0 heuristic) ===")
    out.append(f"primary_sum   = {ia_primary_in_tes_edep:.6g}")
    out.append(f"secondary_sum = {ia_secondary_in_tes_edep:.6g}")
    out.append(f"unknown_sum   = {ia_unknown_in_tes_edep:.6g}")
    out.append("NOTE: This assumes IA field[1] is parent_id; we will confirm from your report.")

    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[OK] wrote {args.out}")

if __name__ == "__main__":
    main()
