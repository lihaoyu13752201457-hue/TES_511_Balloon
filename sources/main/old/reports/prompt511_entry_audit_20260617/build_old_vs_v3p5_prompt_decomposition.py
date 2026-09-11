#!/usr/bin/env python3
"""Why is new_geo_re's prompt-511 small, and what is the MINIMAL mass-model change?

Decomposes old (new_geo_re, top-entry) vs v3p5 (side-entry) prompt-eplus by 511
origin region, from the extracted final W2 prompt-eplus records. Shows old has NO
side term (solid active-CsI side barrel) and v3p5's entire excess is a side-port
side-wall leak -> the minimal fix targets only that one term. NOT ROI.

Run from repo root:
  python3 outputs/reports/prompt511_entry_audit_20260617/build_old_vs_v3p5_prompt_decomposition.py
"""
from __future__ import annotations
import json, math, statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "prompt511_old_vs_v3p5_decomposition_summary.json"


def region(v: str) -> str:
    if not v or v == "None":
        return "MISSING"
    s = v.lower()
    if "side_port" in s or "side_wall" in s:
        return "SIDE-PORT side-wall (v3p5-only leak)"
    if "outer_al_mech" in s or "mechanical_shell" in s:
        return "outer Al mech shell (top/axial residual)"
    if "vacuum_jacket" in s:
        return "vacuum jacket"
    if "csi" in s:
        return "CsI active shield"
    if "win" in s or "collimator" in s:
        return "window/collimator"
    if "liner" in s:
        return "liner (Cu/W)"
    if "tes" in s or "tp_l" in s or "substrate" in s or "si_" in s:
        return "detector stack"
    return v[:30]


def decompose(path: Path):
    recs = json.loads(path.read_text())
    tot = sum(r["rate_s-1"] for r in recs)
    by = defaultdict(lambda: [0, 0.0, []])
    for r in recs:
        reg = region(r.get("last_primary_volume") or r.get("first_primary_volume"))
        al = r.get("annihilation_local_cm") or r.get("last_primary_cm") or [0, 0, 0]
        by[reg][0] += 1
        by[reg][1] += r["rate_s-1"]
        by[reg][2].append(math.hypot(al[0], al[1]))  # birth radius about local z
    rows = []
    for reg, (n, rate, rads) in sorted(by.items(), key=lambda x: -x[1][1]):
        rows.append({"region": reg, "events": n, "rate_cps": rate,
                     "frac": rate / tot, "birth_r_z_median_cm": round(st.median(rads), 1) if rads else None})
    return tot, rows


def minr_in_band(p0, p1, zlo, zhi, N=400):
    d = [p1[i] - p0[i] for i in range(3)]
    best = 1e9
    for i in range(N):
        t = (i + 0.5) / N
        x, y, z = (p0[j] + d[j] * t for j in range(3))
        if zlo <= z <= zhi:
            best = min(best, math.hypot(x, y))
    return best


def window_vs_wall():
    """Clean window-leak (511 path through the optical foil aperture) vs wall-leak,
    for EACH geometry at ITS OWN window location. Apples-to-apples (window<->window,
    wall<->wall) per user critique: do not mix v3p5's side-wall with old's top window."""
    RWIN = 1.898
    res = {}
    # OLD: top window foils at z~9-13 cm (records frame), aperture r<1.898 about z-axis
    old = json.loads((HERE / "old_eplus_prompt_final_records.json").read_text())
    tot = sum(r["rate_s-1"] for r in old)
    win = sum(r["rate_s-1"] for r in old
              if r.get("annihilation_cm") and r.get("tes_centroid_cm")
              and minr_in_band(r["annihilation_cm"], r["tes_centroid_cm"], 9, 13) < RWIN)
    res["old_top_window"] = {"total_cps": tot, "window_leak_cps": round(win, 5),
                             "wall_leak_cps": round(tot - win, 5)}
    # v3p5: side foils, from audit side_window_leakage_class (path through Be/Al discs)
    cur = json.loads((HERE / "current_eplus_prompt_final_records.json").read_text())
    tot = sum(r["rate_s-1"] for r in cur)
    strict = sum(r["rate_s-1"] for r in cur if r.get("side_window_leakage_class", "").startswith("strict"))
    foilish = sum(r["rate_s-1"] for r in cur
                  if r.get("side_window_leakage_class", "").startswith("strict")
                  or "foil" in r.get("side_window_leakage_class", ""))
    res["v3p5_side_window"] = {"total_cps": tot, "window_leak_strict_cps": round(strict, 5),
                               "window_leak_foilish_cps": round(foilish, 5),
                               "wall_leak_cps": round(tot - foilish, 5)}
    res["verdict"] = ("window<->window: both ~0.001-0.002 cps, v3p5 side window NOT worse than old top window. "
                      "wall<->wall: v3p5 0.052 vs old 0.022 (2.4x) -> the leak is WALL, not the optical window. "
                      "v3p5 non-side-port wall ~0.010 < old wall 0.022 (v3p5 top is solid); the side-port wall adds ~0.041.")
    return res


def main():
    out = {"question": "why is new_geo_re prompt small; minimal mass-model change (NOT ROI)"}
    out["window_vs_wall_leak"] = window_vs_wall()
    for label, fn in [("v3p5_side_entry", "current_eplus_prompt_final_records.json"),
                      ("old_new_geo_re_top_entry", "old_eplus_prompt_final_records.json")]:
        tot, rows = decompose(HERE / fn)
        out[label] = {"prompt_eplus_total_cps": tot, "by_region": rows}
        print(f"\n### {label}: prompt-eplus {tot:.5f} cps")
        for r in rows:
            print(f"   {r['rate_cps']:.5f} cps {100*r['frac']:4.0f}% ({r['events']:3d} ev, birth r~{r['birth_r_z_median_cm']}cm)  {r['region']}")

    # minimal-change sizing: leak removal from W2 depends only on areal density (mu/rho ~0.085 for all @511)
    v3 = {r["region"]: r for r in out["v3p5_side_entry"]["by_region"]}
    old = {r["region"]: r for r in out["old_new_geo_re_top_entry"]["by_region"]}
    leak = v3.get("SIDE-PORT side-wall (v3p5-only leak)", {}).get("rate_cps", 0.0)
    v3_tot = out["v3p5_side_entry"]["prompt_eplus_total_cps"]
    old_tot = out["old_new_geo_re_top_entry"]["prompt_eplus_total_cps"]
    out["minimal_change"] = {
        "target": "ONLY the side-port side-wall leak; leave everything else (v3p5 already <= old there)",
        "side_port_leak_cps": leak,
        "v3p5_residual_if_leak_removed_cps": round(v3_tot - leak, 5),
        "old_total_cps": old_tot,
        "verdict": f"removing the side-port leak -> v3p5 prompt ~{v3_tot-leak:.4f} cps, BELOW old {old_tot:.4f}, with NO ROI",
        "shield_areal_density_for_removal": {
            "rule": "W2 removal = 1-exp(-0.085*g_cm2) (any material; mu/rho~0.085 @511keV)",
            "g_cm2_for_90pct": round(-math.log(0.10) / 0.085, 1),
            "g_cm2_for_95pct": round(-math.log(0.05) / 0.085, 1),
            "examples_90pct": "27 g/cm2 = 1.4cm W = 3.8cm BGO = 6cm CsI = 10cm Al",
            "old_side_column_g_cm2": 48.3, "old_side_transmission": 0.016,
        },
        "placement": "between TES (r~3) and emitters (r~13-19), in the side-port solid angle, "
                     "hole only at the signal aperture (~28deg phi band at z=-5.2); close-to-TES minimizes area->mass",
        "framing": "= restore old's solid-shield-except-entrance topology; minpatch over-cut the active shield "
                   "far beyond the signal aperture (left thin Al). Minimal = shrink that hole to the aperture.",
        "active_vs_passive": "CsI/BGO shield doubles as active veto (catches residual + partner 511, as old does); "
                             "W is most compact passive. Removal-from-W2 itself depends only on areal density.",
        "mc_caveats": ["shield's own e+ annihilation 511 add-back", "delayed activation of added Cu/W/CsI (BGO lesson)"],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\nminimal change: remove side-port leak {leak:.4f} -> v3p5 prompt ~{v3_tot-leak:.4f} < old {old_tot:.4f} (NO ROI)")
    print(f"shield: ~27 g/cm2 (1.4cm W / 4cm BGO / 6cm CsI) over side-port solid angle, signal aperture open")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
