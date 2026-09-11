#!/usr/bin/env python3
"""Static 37,194-ray, retained-MXC sightline, mass, and conditional F3 audit."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sg3b_analysis_mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle, Wedge


SCRIPT = Path(__file__).resolve(); PACKAGE = SCRIPT.parents[1]
REPO = SCRIPT.parents[4]
GEO = PACKAGE / "geometry/DEMO2_DR_v3p5_SG3B.geo"
MASS = PACKAGE / "data/sg3b_mass_delta.json"
OUTPUT = PACKAGE / "data/sg3b_static_and_f3_estimate.json"
FIGURE = PACKAGE / "figures/sg3b_correct_bi_halfcylinder_sections.png"
ORIGINS = REPO / "engineering/geometry_optimization_20260815/52_se3_sf3_activation_prompt_section_tool_20260816/TOOL/inputs/selected_delayed_event_origins.csv"
MESH = REPO / "engineering/geometry_optimization_20260815/52_se3_sf3_activation_prompt_section_tool_20260816/TOOL/inputs/se3_geometry_mesh_products.npz"
EVENTLIST = Path("/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/config/signal_eventlists/signal_full_envelope_se3.eventlist.dat")

RI, RO = 3.5154, 3.995
X_INTERVALS = ((-3.8, 3.24), (3.60, 4.0))
CENTER_Z = -5.2
FLAT_LO = np.array((-3.8, -2.25, -2.39)); FLAT_HI = np.array((4.0, 2.25, -1.9104))


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()


def ray_box(source: np.ndarray, target: np.ndarray) -> bool:
    direction=target-source
    with np.errstate(divide="ignore",invalid="ignore"):
        a=(FLAT_LO-source)/direction; b=(FLAT_HI-source)/direction
    parallel=np.abs(direction)<1e-14
    if np.any(parallel & ((source<FLAT_LO)|(source>FLAT_HI))): return False
    enter=max(0.0,float(np.max(np.where(parallel,-np.inf,np.minimum(a,b)))))
    leave=min(1.0,float(np.min(np.where(parallel,np.inf,np.maximum(a,b)))))
    return leave>=enter


def ray_halfcylinder(source: np.ndarray, target: np.ndarray) -> bool:
    direction=target-source; yz=np.array((source[1],source[2]-CENTER_Z)); dyz=direction[1:3]
    breaks=[0.0,1.0]
    qa=float(dyz@dyz); qb=float(2*yz@dyz)
    for radius in (RI,RO):
        qc=float(yz@yz-radius*radius); disc=qb*qb-4*qa*qc
        if qa>0 and disc>=0:
            for value in ((-qb-math.sqrt(disc))/(2*qa),(-qb+math.sqrt(disc))/(2*qa)):
                if 0<value<1: breaks.append(value)
    if abs(direction[0])>1e-14:
        for lo,hi in X_INTERVALS:
            for x in (lo,hi):
                value=(x-source[0])/direction[0]
                if 0<value<1: breaks.append(value)
    if abs(direction[2])>1e-14:
        value=(CENTER_Z-source[2])/direction[2]
        if 0<value<1: breaks.append(value)
    breaks=sorted(set(breaks))
    for a,b in zip(breaks[:-1],breaks[1:]):
        p=source+0.5*(a+b)*direction; radius=math.hypot(p[1],p[2]-CENTER_Z)
        if RI<radius<RO and p[2]>CENTER_Z and any(lo<p[0]<hi for lo,hi in X_INTERVALS): return True
    return False


def targets(geo: str) -> np.ndarray:
    layers={int(n):np.array((float(x),float(y),float(z))) for n,x,y,z in re.findall(r"^TES_L([0-5])\.Position\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)$",geo,re.M)}
    points=[layers[int(n)]+np.array((float(x),float(y),float(z))) for n,x,y,z in re.findall(r"^TP_L([0-5])_\d+\.Position\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)$",geo,re.M)]
    if len(points)!=2256: raise RuntimeError(f"TES target closure failed: {len(points)}")
    return np.asarray(points)


def mxc_sources() -> tuple[np.ndarray,np.ndarray,list[dict[str,str]]]:
    rows=[]
    with ORIGINS.open(newline="") as f:
        for row in csv.DictReader(f):
            if row["source_volume"]=="ColdPlate_MXC_50mK_SD_anchor": rows.append(row)
    points=np.asarray([[float(r[f"production_local_{axis}_cm"]) for axis in "xyz"] for r in rows])
    weights=np.asarray([float(r["event_weight_cps"]) for r in rows])
    return points,weights,rows


def focused_audit() -> dict[str,object]:
    with np.load(MESH) as a: rotation=a["instrument_from_world_rotation"]
    event=np.loadtxt(EVENTLIST); point=event[:,5:8]@rotation.T; direction=event[:,8:11]@rotation.T
    maxima=[]; minima=[]
    for lo,hi in X_INTERVALS:
        for x in (lo,hi):
            u=(x-point[:,0])/direction[:,0]; y=point[:,1]+u*direction[:,1]; z=point[:,2]+u*direction[:,2]
            radius=np.hypot(y,z-CENTER_Z); maxima.append(float(radius.max())); minima.append(float(radius.min()))
    max_radius=max(maxima)
    return {"rays":len(event),"intersections":0 if max_radius<RI else None,"maximum_radial_distance_in_bi_x_ranges_cm":max_radius,"minimum_clearance_to_bi_inner_radius_cm":RI-max_radius}


def coverage(geo: str) -> dict[str,object]:
    target=targets(geo); source,weights,rows=mxc_sources(); per=[]
    for index,s in enumerate(source):
        flat=np.asarray([ray_box(s,t) for t in target]); cyl=np.asarray([ray_halfcylinder(s,t) for t in target])
        per.append({"family":rows[index]["family"],"local_event_id":int(rows[index]["local_event_id"]),"weight_cps":weights[index],"flat_fraction":float(flat.mean()),"halfcylinder_fraction":float(cyl.mean())})
    flat=np.asarray([p["flat_fraction"] for p in per]); cyl=np.asarray([p["halfcylinder_fraction"] for p in per])
    return {"method":"straight sightlines from 7 retained MXC origins to all 2,256 TES pixel centers; geometric screen only, not event tracks","per_origin":per,"flat_weighted_fraction":float(np.average(flat,weights=weights)),"halfcylinder_weighted_fraction":float(np.average(cyl,weights=weights)),"flat_unweighted_fraction":float(flat.mean()),"halfcylinder_unweighted_fraction":float(cyl.mean())}


def f3(screen: dict[str,object]) -> dict[str,object]:
    parent_f3=5.769833354236724e-5; parent_remaining=0.6161049133882954
    nbti_share=0.07005367355364235; bi_upper=0.13212569580666114; old_bi_fraction=0.5
    scenarios={"conservative":{"al_harness_suppression":0.5,"new_bi_fraction":0.65},"central":{"al_harness_suppression":0.9,"new_bi_fraction":float(screen["halfcylinder_weighted_fraction"])},"optimistic":{"al_harness_suppression":1.0,"new_bi_fraction":1.0}}
    for s in scenarios.values():
        extra=nbti_share*s["al_harness_suppression"]+bi_upper*max(0.0,s["new_bi_fraction"]-old_bi_fraction)
        remaining=parent_remaining-extra
        s.update({"extra_baseline_background_reduction_fraction":extra,"estimated_remaining_fraction_vs_se3":remaining,"conditional_F3_ph_cm2_s":parent_f3*math.sqrt(remaining/parent_remaining),"accepted_prompt_increment_assumption_cps":0.0,"signal_retention_assumption":1.0})
    return {"authority":"PRETRANSPORT_CONDITIONAL_ESTIMATE_ONLY","parent_sg3a_central_F3_ph_cm2_s":parent_f3,"scenarios":scenarios,"headline_central_F3_ph_cm2_s":scenarios["central"]["conditional_F3_ph_cm2_s"],"headline_range_F3_ph_cm2_s":[scenarios["optimistic"]["conditional_F3_ph_cm2_s"],scenarios["conservative"]["conditional_F3_ph_cm2_s"]],"unmodeled_risk":"410 g passive near-field Bi may create new accepted prompt/pair events; Al proxy produces a new activation inventory; either can move F3 outside this range"}


def draw() -> None:
    FIGURE.parent.mkdir(parents=True,exist_ok=True)
    fig,(a,b)=plt.subplots(1,2,figsize=(12.2,5.6))
    a.add_patch(Wedge((0,CENTER_Z),4.2,0,360,width=.2,facecolor="#9DD9E8",edgecolor="#14798E",alpha=.65,label="retained 2 mm Al near-field cylinder"))
    a.add_patch(Wedge((0,CENTER_Z),RO,0,180,width=RO-RI,facecolor="#B896C9",edgecolor="#5A3472",hatch="...",alpha=.8,label="SG3B 4.796 mm Bi upper half-cylinder"))
    a.add_patch(Rectangle((-1.8,-7.0),3.6,3.6,fill=False,edgecolor="#B22222",lw=1.2,label="TES y'-z' envelope"))
    a.set_aspect("equal");a.set_xlim(-5,5);a.set_ylim(-10.2,.2);a.set_xlabel("y' [cm]");a.set_ylabel("z' [cm]");a.set_title("Cross-section normal to x': correct nested half-cylinder");a.grid(alpha=.25);a.legend(fontsize=7,loc="lower left")
    b.add_patch(Rectangle((-3.85,-9.4),7.95,.2,facecolor="#9DD9E8",edgecolor="#14798E",alpha=.65))
    b.add_patch(Rectangle((-3.85,-1.2),7.95,.2,facecolor="#9DD9E8",edgecolor="#14798E",alpha=.65))
    for lo,hi in X_INTERVALS: b.add_patch(Rectangle((lo,-1.6854),hi-lo,.4796,facecolor="#B896C9",edgecolor="#5A3472",hatch="...",alpha=.8))
    b.add_patch(Rectangle((-3.8,-2.39),7.8,.4796,fill=False,edgecolor="#777",ls="--",label="removed flat Bi plate"))
    b.add_patch(Rectangle((3.245,-8.0),.35,5.6,fill=False,edgecolor="#A64B1A",hatch="//",label="retained L0 ring; axial Bi gap"))
    b.set_xlim(-5,5);b.set_ylim(-10.2,.2);b.set_xlabel("x' [cm]");b.set_ylabel("z' [cm]");b.set_title("y'=0 side section: Bi follows the Al cylinder top arc");b.grid(alpha=.25);b.legend(fontsize=7,loc="lower left")
    fig.tight_layout();fig.savefig(FIGURE,dpi=220);plt.close(fig)


def main() -> int:
    geo=GEO.read_text(); screen=coverage(geo); rays=focused_audit(); estimate=f3(screen); draw()
    payload={"status":"PASS__SG3B_STATIC_RAY_AND_ESTIMATE","transport_launched":False,"geometry":str(GEO),"focused_signal":rays,"mxc_geometric_screen":screen,"f3_estimate":estimate,"mass":json.loads(MASS.read_text()),"inputs":{"geo_sha256":sha(GEO),"origins_sha256":sha(ORIGINS),"mesh_sha256":sha(MESH),"eventlist_sha256":sha(EVENTLIST)},"figure":{"path":str(FIGURE),"sha256":sha(FIGURE)}}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":payload["status"],"focused_signal":rays,"screen":{"flat":screen["flat_weighted_fraction"],"halfcylinder":screen["halfcylinder_weighted_fraction"]},"f3":estimate},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
