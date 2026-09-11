#!/usr/bin/env python3
"""Faithful schematic of Codex's active-CsI collar geometry, parsed from the .geo.
Two cross-sections through the TES (z=-5.2): radial (x-y) and axial (x-z, y=0)."""
import re, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Rectangle, FancyArrow

GEO = Path("/home/ubuntu/TES_511_Balloon/outputs/reports/prompt511_active_csi_collar_20260620/"
           "geometry_active_csi_collar/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_csi_collar_r4p25_5p95.geo")
OUT = Path("/home/ubuntu/TES_511_Balloon/outputs/reports/prompt511_collar_schematic_20260620/collar_schematic.png")
txt = GEO.read_text()

def vols():
    out = {}
    for m in re.finditer(r"^Volume (\S+)", txt, re.M):
        n = m.group(1)
        sh = re.search(rf"^{re.escape(n)}\.Shape\s+(.*)$", txt, re.M)
        po = re.search(rf"^{re.escape(n)}\.Position\s+(.*)$", txt, re.M)
        mo = re.search(rf"^{re.escape(n)}\.Mother\s+(\S+)", txt, re.M)
        if sh and po and mo and mo.group(1) == "InstrumentFrame":
            out[n] = (sh.group(1).split(), [float(x) for x in po.group(1).split()])
    return out
V = vols()

# color/style by family
def style(n):
    if "Prompt511_Collar" in n:                 return ("#e8a800", "CsI collar (NEW, active)", 1.0, 3)
    if n.startswith("TES_L"):                    return ("#d62728", "TES (science, Ta)", 1.0, 5)
    if "Cryoperm" in n:                          return ("#7b4fa3", "Cryoperm mag-shield (compacted)", 0.9, 2)
    if "Al_50mK_Local_Can" in n:                 return ("#1f77b4", "50mK can (compacted)", 0.8, 2)
    if "Nb_SideEntry_Sample_Can" in n:           return ("#17becf", "Nb sample can (compacted)", 0.8, 2)
    if "Vacuum_Jacket_Al" in n:                  return ("#444444", "vacuum jacket (511 born here)", 0.9, 1)
    if "CsI_Side_Segment" in n or "CsI_Bottom" in n or "CsI_TopAnnulus" in n:
                                                 return ("#f2e38a", "outer CsI well", 0.5, 1)
    if "Shield_60K" in n or "Shield_4K" in n or "Still_Shield" in n:
                                                 return ("#cccccc", "cold Al shells", 0.4, 1)
    if "Outer_Al_Mechanical" in n:               return ("#999999", "outer Al mech shell", 0.4, 1)
    return (None, None, 0, 0)

def pcon(sh):
    phi0, dphi, nz = float(sh[1]), float(sh[2]), int(sh[3])
    zs=[float(sh[4+3*i]) for i in range(nz)]; rmins=[float(sh[5+3*i]) for i in range(nz)]; rmaxs=[float(sh[6+3*i]) for i in range(nz)]
    return phi0,dphi,min(zs),max(zs),min(rmins),max(rmaxs)

Z0=-5.2
figdone=set()
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,7.5))

# ---------- Panel A: radial x-y at z=Z0 ----------
for n,(sh,p) in V.items():
    col,lab,al,zo=style(n)
    if col is None: continue
    if sh[0]=="PCON":
        phi0,dphi,zlo,zhi,rmin,rmax=pcon(sh)
        zc=p[2]
        if not (zc+zlo<=Z0<=zc+zhi): continue
        w=Wedge((p[0],p[1]),rmax,phi0,phi0+dphi,width=rmax-rmin,facecolor=col,edgecolor="k",lw=0.4,alpha=al,zorder=zo)
        axA.add_patch(w)
    elif sh[0]=="BRIK":
        hx,hy,hz=float(sh[1]),float(sh[2]),float(sh[3])
        if not (p[2]-hz<=Z0<=p[2]+hz): continue
        axA.add_patch(Rectangle((p[0]-hx,p[1]-hy),2*hx,2*hy,facecolor=col,edgecolor="k",lw=0.4,alpha=al,zorder=zo))
    if lab and (lab,'A') not in figdone:
        axA.plot([],[],'s',color=col,label=lab,alpha=al); figdone.add((lab,'A'))
# signal beam + leak arrows
axA.add_patch(FancyArrow(-9,0,4.5,0,width=0.25,head_width=0.8,head_length=0.8,color="green",zorder=6,length_includes_head=True))
axA.text(-9.2,0.6,"signal in (through 40° port)",color="green",fontsize=9,ha='left')
axA.add_patch(FancyArrow(13*math.cos(math.radians(125)),13*math.sin(math.radians(125)),
                         -8*math.cos(math.radians(125)),-8*math.sin(math.radians(125)),
                         width=0.12,head_width=0.6,head_length=0.6,color="crimson",zorder=6,length_includes_head=True))
axA.text(-6.5,7.2,"leak 511 (born @jacket) → hits CsI collar",color="crimson",fontsize=9)
axA.set_title("A) radial cross-section (x–y) through TES, z=-5.2 cm",fontsize=11)
axA.set_xlabel("x (cm)  [port/signal at -x]"); axA.set_ylabel("y (cm)")
axA.set_xlim(-15,15); axA.set_ylim(-15,15); axA.set_aspect('equal'); axA.legend(loc='upper right',fontsize=7.5)

# ---------- Panel B: axial x-z at y=0 ----------
figB=set()
for n,(sh,p) in V.items():
    col,lab,al,zo=style(n)
    if col is None: continue
    if sh[0]=="PCON":
        phi0,dphi,zlo,zhi,rmin,rmax=pcon(sh)
        z1,z2=p[2]+zlo,p[2]+zhi
        # +x side present if phi-range covers 0/360 ; -x side if covers 180
        def covers(a):
            d=(a-phi0)%360; return d<=dphi
        if covers(0):
            axB.add_patch(Rectangle((rmin,z1),rmax-rmin,z2-z1,facecolor=col,edgecolor="k",lw=0.4,alpha=al,zorder=zo))
        if covers(180):
            axB.add_patch(Rectangle((-rmax,z1),rmax-rmin,z2-z1,facecolor=col,edgecolor="k",lw=0.4,alpha=al,zorder=zo))
    elif sh[0]=="BRIK":
        hx,hy,hz=float(sh[1]),float(sh[2]),float(sh[3])
        if not (p[1]-hy<=0<=p[1]+hy): continue
        axB.add_patch(Rectangle((p[0]-hx,p[2]-hz),2*hx,2*hz,facecolor=col,edgecolor="k",lw=0.4,alpha=al,zorder=zo))
    if lab and (lab,'B') not in figB:
        axB.plot([],[],'s',color=col,label=lab,alpha=al); figB.add((lab,'B'))
axB.add_patch(FancyArrow(-9,-5.2,4.0,0,width=0.2,head_width=0.7,head_length=0.7,color="green",zorder=6,length_includes_head=True))
axB.text(-9,-4.3,"signal in (-x port)",color="green",fontsize=9)
axB.set_title("B) axial cross-section (x–z) at y=0",fontsize=11)
axB.set_xlabel("x (cm)  [-x = signal port side]"); axB.set_ylabel("z (cm)  [TES at z=-5.2]")
axB.set_xlim(-15,15); axB.set_ylim(-16,8); axB.set_aspect('equal'); axB.legend(loc='upper right',fontsize=7.5)

fig.suptitle("Codex active-CsI collar (r4.25-5.95, 1.7cm) — a CsI sleeve around the TES, signal port at -x\n"
             "(cold cans/shield/fingers were compacted inward to make room)",fontsize=12)
fig.tight_layout(rect=[0,0,1,0.96])
fig.savefig(OUT,dpi=110)
print("wrote",OUT)
