#!/usr/bin/env python3
"""Transform the frozen 37,194-ray Step09 EventList to the SH3 OptV3 chimney
focal plane (design intent B).

Old beam (SG3B-era contract):
  - injection plane  : local x = -13.1
  - beam line        : local z = -5.2 (through SG3B Be window center)
New beam (OptV3 chimney focal plane):
  - injection plane  : local x = -46.0  (just outside chimney far end -45.75)
  - beam line        : local z = -2.8   (chimney axis; W-box/window/TES center)

Transform: local += (-32.9, 0, +2.4)  ==  world += R_y(45)*(-32.9,0,2.4)
R_y(45)*v: (x cos45 + z sin45, y, -x sin45 + z cos45)
=> world translation T = (-32.9+2.4, 0, 32.9+2.4) * sin45 = (-21.567, 0, +24.961)
"""
import sys
import numpy as np
from pathlib import Path

SRC = Path("/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat")
DST = Path("/home/ubuntu/TES_511_Balloon/DEEPSEEK_CODE/outputs/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger_optv3_focal_z2p8.eventlist.dat")

SIN45 = 0.5 * np.sqrt(2.0)
T = np.array([(-32.9 + 2.4) * SIN45, 0.0, (32.9 + 2.4) * SIN45])  # world translation

def rot_y_minus45(p):
    x, y, z = p
    return np.array([SIN45 * (x - z), y, SIN45 * (x + z)])

rows = []
with SRC.open() as f:
    for line in f:
        t = line.split()
        if len(t) < 13:
            continue
        pos = np.array([float(t[5]), float(t[6]), float(t[7])], dtype=np.float64)
        d = np.array([float(t[8]), float(t[9]), float(t[10])], dtype=np.float64)
        d /= np.linalg.norm(d)
        rows.append((t, pos, d))
print(f"parsed rays: {len(rows)}")

# --- beam envelope in local frame, before and after transform ---
def beam_radius_local(rows, local_x):
    """Distance from beam centerline (local) for all rays crossing plane x=local_x."""
    center_local = np.array([local_x, 0.0, -2.8])   # new beam line (z=-2.8)
    # beam local direction = +x (unit)
    radii = []
    for t, pos_w, d_w in rows:
        pos_l = rot_y_minus45(pos_w + T)   # new local position
        d_l = rot_y_minus45(d_w)
        d_l /= np.linalg.norm(d_l)
        v = pos_l - center_local
        tt = -v[0] / d_l[0]                # go from current local x to plane local_x
        cross = pos_l + tt * d_l
        r = np.sqrt(cross[1] ** 2 + (cross[2] + 2.8) ** 2)  # offset from beam line z=-2.8
        radii.append(r)
    radii = np.array(radii)
    return radii

planes = [("chimney_far_end_x-45.75", -45.75), ("W_box_x-44.7", -44.7),
          ("window_L1_x-39.4", -39.4), ("window_L6_x-42.0", -42.0),
          ("TES_x-32.55", -32.55)]
for name, x in planes:
    r = beam_radius_local(rows, x)
    print(f"{name:24s} beam radius r99={np.percentile(r,99):.3f} cm  max={r.max():.3f} cm")

# --- W-box opening check at x=-44.7 (local) ---
# W box: Top z=+0.05(plate z -0.025..0.125, y±1.5), Bottom z=-5.65(z -5.725..-5.575),
#        PosY y=+2.85(y 2.775..2.925, z -4.15..-1.45), NegY y=-2.85(y -2.925..-2.775)
# Opening: |y| < 2.775  and  -4.15 < z < -1.45
hits_bottom = 0
hits_side = 0
total = 0
hits_top = 0
hits_bottom = 0
hits_side = 0
total = 0
for t, pos_w, d_w in rows:
    pos_l = rot_y_minus45(pos_w + T)
    d_l = rot_y_minus45(d_w); d_l /= np.linalg.norm(d_l)
    tt = -(pos_l[0] + 44.7) / d_l[0]
    cross = pos_l + tt * d_l
    y, z = cross[1], cross[2]
    if abs(y) < 2.775 and -4.15 < z < -1.45:
        total += 1
    else:
        if z > -1.45 and abs(y) < 1.5:  hits_top += 1
        elif z < -4.15 and abs(y) < 1.5: hits_bottom += 1
        else: hits_side += 1
print(f"\nW-box crossing at x=-44.7: through opening {total}, top-clip {hits_top}, bottom-clip {hits_bottom}, side-clip {hits_side}")

# --- write transformed eventlist ---
DST.parent.mkdir(parents=True, exist_ok=True)
with DST.open("w") as f:
    for t, pos_w, d_w in rows:
        new_pos = pos_w + T
        out = t[:]
        out[5] = f"{new_pos[0]:.10f}"; out[6] = f"{new_pos[1]:.10f}"; out[7] = f"{new_pos[2]:.10f}"
        f.write(" ".join(out) + "\n")
print(f"\nwrote {DST}")
print(f"transform T = {np.round(T,6)}  (local dx=-32.9, dz=+2.4)")
EOF_MARKER = None