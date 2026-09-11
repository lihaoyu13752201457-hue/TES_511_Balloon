#!/usr/bin/env python3
"""Auditable analytic shielding screen for the prompt-511 side-port background.

Reproduces the numbers in core_md/CLAUDE_PROMPT511_SIDEPORT_FIX_REVIEW_20260617.md
directly from the extracted current prompt-eplus final records.

THIS IS A GEOMETRIC ATTENUATION SCREEN, NOT A MONTE CARLO. It attenuates each
selected event's annihilation->TES straight line by hypothetical shield material.
It does NOT include: the shield's own e+ annihilation 511 (add-back), Compton
down-scatter refill, signal-cone clipping, or delayed activation. The suppression
factors are therefore UPPER BOUNDS and must be confirmed by MC. Do not quote the
derived rates/Z/flux as authority.

Run from repo root:
  python3 outputs/reports/prompt511_entry_audit_20260617/build_prompt511_fix_screen.py
"""
from __future__ import annotations
import csv, json, math, statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECS = HERE / "current_eplus_prompt_final_records.json"
LINE_CHORDS = HERE / "prompt511_raytrace_line_chords.csv"
OUT_JSON = HERE / "prompt511_fix_screen_summary.json"

# 511 keV attenuation: mass attenuation (cm2/g, NIST ~0.5 MeV) x density (g/cm3)
MU_RHO = {"Ta/TES":0.0910,"CsI":0.0866,"Aluminium":0.0844,"Copper":0.0836,"W":0.0918,
          "Be":0.0855,"Kapton":0.0855,"StainlessSteel":0.0831,"LowCarbonSteel":0.0840,
          "Nb":0.0843,"Cryoperm":0.0832,"Silicon":0.0869,"SilverSinterProxy":0.0810,
          "CuNi":0.0835,"G10":0.0850,"SaltProxy":0.0840,"CharcoalProxy":0.0850,
          "NbTiCableProxy":0.0840,"other":0.0850}
RHO   = {"Ta/TES":16.6,"CsI":4.51,"Aluminium":2.70,"Copper":8.96,"W":19.3,"Be":1.85,
         "Kapton":1.42,"StainlessSteel":8.00,"LowCarbonSteel":7.87,"Nb":8.57,"Cryoperm":8.7,
         "Silicon":2.33,"SilverSinterProxy":7.0,"CuNi":8.9,"G10":1.80,"SaltProxy":2.0,
         "CharcoalProxy":0.5,"NbTiCableProxy":6.0,"other":3.0}
MU_W = MU_RHO["W"] * RHO["W"]          # 1.771 /cm
R_WIN = 1.898                          # designed signal clear-aperture disc radius (cm)


def transmission(thick_by_mat, exclude_tes=True):
    tau = ad = 0.0
    for m, t in thick_by_mat.items():
        if t <= 0 or (exclude_tes and m == "Ta/TES"):
            continue
        ad += RHO.get(m, 3.0) * t
        tau += MU_RHO.get(m, 0.085) * RHO.get(m, 3.0) * t
    return ad, math.exp(-tau)


def seg_shell_chord(p0, p1, r0, r1, gap_lo, gap_hi, zlo=-12, zhi=2, N=600):
    """Chord length of segment p0->p1 inside a z-axis annulus r in [r0,r1],
    z in [zlo,zhi], EXCLUDING azimuth gap [gap_lo,gap_hi] deg (the open signal port)."""
    d = [p1[i] - p0[i] for i in range(3)]
    L = math.sqrt(sum(c * c for c in d))
    if L == 0:
        return 0.0
    inside = 0
    for i in range(N):
        t = (i + 0.5) / N
        x, y, z = (p0[j] + d[j] * t for j in range(3))
        r = math.hypot(x, y)
        phi = math.degrees(math.atan2(y, x)) % 360
        if r0 <= r <= r1 and zlo <= z <= zhi and not (gap_lo <= phi <= gap_hi):
            inside += 1
    return L * inside / N


def crosses_gap(p0, p1, r0, r1, gap_lo, gap_hi, N=600):
    d = [p1[i] - p0[i] for i in range(3)]
    for i in range(N):
        t = (i + 0.5) / N
        x, y = p0[0] + d[0] * t, p0[1] + d[1] * t
        r = math.hypot(x, y)
        phi = math.degrees(math.atan2(y, x)) % 360
        if r0 <= r <= r1 and gap_lo <= phi <= gap_hi:
            return True
    return False


def main():
    recs = json.loads(RECS.read_text())
    tot = sum(r["rate_s-1"] for r in recs)
    out = {"baseline_prompt_eplus_cps": tot, "n_events": len(recs),
           "method": "analytic geometric attenuation screen (NOT MC); suppression = UPPER BOUND",
           "excludes": ["shield self-emission 511 add-back", "Compton refill",
                        "signal-cone clipping", "delayed activation"]}

    # --- window vs non-window ---
    from collections import Counter
    cls = Counter(r.get("side_window_leakage_class", "?") for r in recs)
    out["window_class_counts"] = dict(cls)

    # --- side-line transmission (fixed chords) ---
    side = {}
    with LINE_CHORDS.open() as f:
        for row in csv.DictReader(f):
            mats = {k[len("ray_cm_"):]: float(v) for k, v in row.items()
                    if k and k.startswith("ray_cm_") and v not in ("", "0.0", None) and float(v) > 1e-6}
            ad, T = transmission(mats)
            side[row["line"]] = {"areal_density_g_cm2": round(ad, 2), "transmission_511": round(T, 5)}
    out["side_line_transmission"] = side

    # --- candidate A: window-plane annular baffle ---
    def cr(r):
        pr = r.get("side_window_crossings_local_proxy") or []
        rs = [c.get("radius_cm") for c in pr if c.get("crosses_plane")]
        return min(rs) if rs else None
    A = {}
    for r_clear in (R_WIN, 2.5):
        for t in (1.0, 2.0, 3.0):
            res = 0.0
            for r in recs:
                c = cr(r); cth = max(abs(r.get("ann_to_tes_dot_current_side_axis") or 0.0), 0.05)
                res += r["rate_s-1"] * (math.exp(-MU_W * t / cth) if (c is not None and r_clear <= c <= 9.0) else 1.0)
            A[f"r_clear={r_clear:.2f}_t={t:.0f}"] = {"residual_cps": round(res, 5),
                                                     "frac": round(res / tot, 3), "suppression_x": round(tot / res, 2)}
    out["candidateA_window_plane_baffle"] = A
    have = [cr(r) for r in recs if cr(r) is not None]
    out["candidateA_note"] = {"events_crossing_window_plane": len(have), "events_total": len(recs),
                              "reason_ineffective": "most leak does not cross the window plane"}

    # --- candidate B: cryostat-wall W liner about z-axis, port phi-sector OPEN ---
    rows = [(r["rate_s-1"], r["annihilation_local_cm"], r["tes_centroid_local_cm"]) for r in recs]
    B = {}
    for (r0, r1) in ((4, 6), (5, 7), (5, 8)):
        for (glo, ghi) in ((160, 200),):
            res = 0.0; blocked = 0
            for w, b, te in rows:
                ch = seg_shell_chord(b, te, r0, r1, glo, ghi)
                if ch > 0.05:
                    blocked += 1
                res += w * math.exp(-MU_W * ch)
            B[f"r=[{r0},{r1}]_gap[{glo},{ghi}]"] = {"residual_cps": round(res, 5), "frac": round(res / tot, 3),
                                                    "suppression_x": round(tot / res, 2), "events_hitting_liner": blocked}
    out["candidateB_wall_liner_port_open"] = B
    port = sum(w for w, b, te in rows if crosses_gap(b, te, 5, 7, 160, 200))
    out["irreducible_port_sector_cps"] = round(port, 5)
    out["irreducible_port_sector_frac"] = round(port / tot, 3)
    out["irreducible_note"] = (
        "enters through the open signal port sector; simple passive shielding cannot remove it "
        "without coupling to the signal port. Treat as a side-port design residual/constraint; "
        "do not promote focal-spot ROI as the prompt-suppression strategy."
    )

    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"baseline prompt-eplus = {tot:.6f} cps ({len(recs)} events)")
    print(f"window class: {dict(cls)}")
    print(f"candidate A (window baffle) best: {min(A.values(), key=lambda d: d['residual_cps'])}")
    print(f"candidate B (wall liner) best:    {min(B.values(), key=lambda d: d['residual_cps'])}")
    print(f"irreducible port-sector: {port:.5f} cps ({100*port/tot:.1f}%)")
    print(f"wrote {OUT_JSON.relative_to(HERE.parents[2])}")


if __name__ == "__main__":
    main()
