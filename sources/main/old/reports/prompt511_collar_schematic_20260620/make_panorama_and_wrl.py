#!/usr/bin/env python3
"""Panoramic 2D (full instrument) + WRL 3D of the active-CsI-collar geometry, parsed from .geo."""
import re, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Rectangle

D = Path("/home/ubuntu/TES_511_Balloon/outputs/reports/prompt511_collar_schematic_20260620")
GEO = Path("/home/ubuntu/TES_511_Balloon/outputs/reports/prompt511_active_csi_collar_20260620/"
           "geometry_active_csi_collar/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_csi_collar_r4p25_5p95.geo")
txt = GEO.read_text()

def vols():
    out=[]
    for m in re.finditer(r"^Volume (\S+)", txt, re.M):
        n=m.group(1)
        sh=re.search(rf"^{re.escape(n)}\.Shape\s+(.*)$",txt,re.M)
        po=re.search(rf"^{re.escape(n)}\.Position\s+(.*)$",txt,re.M)
        mo=re.search(rf"^{re.escape(n)}\.Mother\s+(\S+)",txt,re.M)
        if sh and po and mo and mo.group(1)=="InstrumentFrame":
            out.append((n,sh.group(1).split(),[float(x) for x in po.group(1).split()]))
    return out
V=vols()

# color, label, alpha, zorder, rgb(for wrl), transparency(for wrl), include_in_wrl
def style(n):
    if "Prompt511_Collar" in n:       return ("#e8a800","CsI collar (NEW)",1.0,6,(0.91,0.66,0.0),0.0,True)
    if n.startswith("TES_L"):         return ("#d62728","TES (Ta)",1.0,7,(0.84,0.15,0.16),0.0,True)
    if "Cryoperm" in n:               return ("#7b4fa3","Cryoperm (compacted)",0.95,5,(0.48,0.31,0.64),0.25,True)
    if "Al_50mK_Local_Can" in n:      return ("#1f77b4","50mK can (compacted)",0.9,5,(0.12,0.47,0.71),0.25,True)
    if "Nb_SideEntry_Sample_Can" in n:return ("#17becf","Nb sample can (compacted)",0.9,5,(0.09,0.75,0.81),0.3,True)
    if "Vacuum_Jacket_Al" in n:       return ("#444444","vacuum jacket (511 born)",0.85,2,(0.27,0.27,0.27),0.55,True)
    if any(s in n for s in ("CsI_Side_Segment","CsI_Bottom","CsI_TopAnnulus")):
                                      return ("#f2e38a","outer CsI well",0.55,2,(0.95,0.89,0.54),0.6,True)
    if any(s in n for s in ("Shield_60K","Shield_4K","Still_Shield")):
                                      return ("#cccccc","cold Al shells",0.4,1,(0.8,0.8,0.8),0.75,True)
    if "Outer_Al_Mechanical" in n:    return ("#9a9a9a","outer Al mech shell",0.4,1,(0.6,0.6,0.6),0.8,True)
    if any(s in n for s in ("W_Side_Aperture","Win_")):
                                      return ("#2ca02c","window/collimator",0.6,3,(0.17,0.63,0.17),0.3,True)
    return ("#eeeeee",None,0.18,0,(0.9,0.9,0.9),0.85,False)  # other clutter: faint in 2D, skip in wrl

def pcon(sh):
    nz=int(sh[3]); zs=[float(sh[4+3*i]) for i in range(nz)]
    rmins=[float(sh[5+3*i]) for i in range(nz)]; rmaxs=[float(sh[6+3*i]) for i in range(nz)]
    return float(sh[1]),float(sh[2]),min(zs),max(zs),min(rmins),max(rmaxs)

# ---------------- PANORAMIC 2D ----------------
fig,(axA,axB)=plt.subplots(1,2,figsize=(17,8.5)); seen=set()
Z0=-5.2
for n,sh,p in V:
    col,lab,al,zo,_,_,_=style(n)
    if sh[0]=="PCON":
        phi0,dphi,zlo,zhi,rmin,rmax=pcon(sh)
        # x-y panel at z=Z0
        if p[2]+zlo<=Z0<=p[2]+zhi:
            axA.add_patch(Wedge((p[0],p[1]),rmax,phi0,phi0+dphi,width=rmax-rmin,facecolor=col,edgecolor="k",lw=0.3,alpha=al,zorder=zo))
        # x-z panel at y=0
        z1,z2=p[2]+zlo,p[2]+zhi
        cov=lambda a:((a-phi0)%360)<=dphi
        if cov(0):   axB.add_patch(Rectangle((rmin,z1),rmax-rmin,z2-z1,facecolor=col,edgecolor="k",lw=0.3,alpha=al,zorder=zo))
        if cov(180): axB.add_patch(Rectangle((-rmax,z1),rmax-rmin,z2-z1,facecolor=col,edgecolor="k",lw=0.3,alpha=al,zorder=zo))
    elif sh[0]=="BRIK":
        hx,hy,hz=float(sh[1]),float(sh[2]),float(sh[3])
        if p[2]-hz<=Z0<=p[2]+hz:
            axA.add_patch(Rectangle((p[0]-hx,p[1]-hy),2*hx,2*hy,facecolor=col,edgecolor="k",lw=0.3,alpha=al,zorder=zo))
        if p[1]-hy<=0<=p[1]+hy:
            axB.add_patch(Rectangle((p[0]-hx,p[2]-hz),2*hx,2*hz,facecolor=col,edgecolor="k",lw=0.3,alpha=al,zorder=zo))
    if lab and lab not in seen:
        axA.plot([],[],'s',color=col,label=lab,alpha=max(al,0.5)); seen.add(lab)
for ax,t,xl,yl in [(axA,"FULL radial (x-y) @ z=-5.2","x (cm)  [signal port at -x]","y (cm)"),
                   (axB,"FULL axial (x-z) @ y=0","x (cm)","z (cm)")]:
    ax.set_title(t); ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_aspect('equal')
axA.set_xlim(-20,20); axA.set_ylim(-20,20); axB.set_xlim(-22,22); axB.set_ylim(-24,18)
axA.legend(loc='upper left',fontsize=7,ncol=1)
axA.annotate("",xy=(-6,0),xytext=(-13,0),arrowprops=dict(color="green",width=2,headwidth=8)); axA.text(-13,0.8,"signal",color="green",fontsize=9)
fig.suptitle("Active-CsI-collar instrument — full 2D panorama (collar = gold ring hugging the TES, inside the cold shells)",fontsize=13)
fig.tight_layout(rect=[0,0,1,0.96]); fig.savefig(D/"collar_panorama_2d.png",dpi=110)
print("wrote",D/"collar_panorama_2d.png")

# ---------------- WRL 3D ----------------
def wedge_ifs(phi0,dphi,zlo,zhi,rmin,rmax):
    N=max(6,int(abs(dphi)/7.5))
    pts=[]; 
    for i in range(N+1):
        a=math.radians(phi0+dphi*i/N); c,s=math.cos(a),math.sin(a)
        pts += [(rmin*c,rmin*s,zlo),(rmax*c,rmax*s,zlo),(rmin*c,rmin*s,zhi),(rmax*c,rmax*s,zhi)]
    idx=[]
    for i in range(N):
        b=i*4; nb=(i+1)*4
        ib,ob,it,ot=b,b+1,b+2,b+3; nib,nob,nit,not_=nb,nb+1,nb+2,nb+3
        idx += [ob,nob,not_,ot,-1, ib,it,nit,nib,-1, it,ot,not_,nit,-1, ib,nib,nob,ob,-1]
    if abs(dphi)<359.9:
        b=0; e=N*4
        idx += [b,b+2,b+3,b+1,-1, e,e+1,e+3,e+2,-1]
    return pts,idx
def box_pts(hx,hy,hz):
    P=[(-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),(-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)]
    I=[0,1,2,3,-1,4,5,6,7,-1,0,1,5,4,-1,1,2,6,5,-1,2,3,7,6,-1,3,0,4,7,-1]
    return P,I
out=["#VRML V2.0 utf8","WorldInfo { title \"active CsI collar\" }",
     "NavigationInfo { type [\"EXAMINE\",\"ANY\"] }","Background { skyColor [1 1 1] }"]
def shape(pts,idx,rgb,tr,trans=(0,0,0)):
    ps=" ".join(f"{x:.3f} {y:.3f} {z:.3f}" for x,y,z in pts)
    ix=" ".join(str(i) for i in idx)
    return (f"Transform {{ translation {trans[0]} {trans[1]} {trans[2]} children [ Shape {{ "
            f"appearance Appearance {{ material Material {{ diffuseColor {rgb[0]} {rgb[1]} {rgb[2]} "
            f"transparency {tr} }} }} geometry IndexedFaceSet {{ solid FALSE coord Coordinate {{ point [{ps}] }} "
            f"coordIndex [{ix}] }} }} ] }}")
nw=0
for n,sh,p in V:
    col,lab,al,zo,rgb,tr,inc=style(n)
    if not inc: continue
    if sh[0]=="PCON":
        phi0,dphi,zlo,zhi,rmin,rmax=pcon(sh)
        pts,idx=wedge_ifs(phi0,dphi,p[2]+zlo,p[2]+zhi,rmin,rmax)
        out.append(shape(pts,idx,rgb,tr,(p[0],p[1],0)))
    else:
        hx,hy,hz=float(sh[1]),float(sh[2]),float(sh[3])
        pts,idx=box_pts(hx,hy,hz)
        out.append(shape(pts,idx,rgb,tr,(p[0],p[1],p[2])))
    nw+=1
(D/"collar_geometry.wrl").write_text("\n".join(out)+"\n")
print("wrote",D/"collar_geometry.wrl",f"({nw} shapes)")
