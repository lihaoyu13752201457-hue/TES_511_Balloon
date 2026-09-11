#!/usr/bin/env python3
"""Hard gate for the prompt-511 refix: constraints are ENFORCED, not remembered.
Usage: check_prompt511_constraints.py <candidate.geo> [candidate_dir]
Exits nonzero (and prints FAIL) if any constraint is violated."""
import re, sys, math
from pathlib import Path

BASELINE = Path("/home/ubuntu/TES_511_Balloon/outputs/geometry/"
                "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/"
                "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo")
SCINT = {"CsI","BGO","NaI","LYSO","GAGG","LaBr3","CeBr3","BaF2","GSO"}
ALLOWED_SHIELD = {"W","Ta","Pb","Cu","Sn","Au","Aluminium"}
COLD_R = 11.0  # r<this = DR cold region (inside 60K ~11.4); a passive metal liner must sit OUTSIDE
# the three forbidden-to-modify functional layers (name-protected, CRITICAL):
CRITICAL = ("TES_", "Cu_ColdFinger_", "Cryoperm_")   # detector / thermal / magnetic
# result-gate thresholds (objective in CONSTRAINTS_PROMPT511.md):
OLD_PROMPT_CPS = 0.0323247   # new_geo_re total prompt target
DELAYED_TOL = 0.10           # delayed must not rise > +10%
SIGNAL_KEEP_MIN = 0.99

def parse(geo):
    t = Path(geo).read_text(); V = {}
    for m in re.finditer(r"^Volume (\S+)", t, re.M):
        n = m.group(1)
        g = lambda a: (re.search(rf"^{re.escape(n)}\.{a}\s+(.*)$", t, re.M) or [None,None])
        sh = g("Shape")[1]; po = g("Position")[1]; ma = g("Material")[1]
        V[n] = (sh, po, ma)
    sphere = re.search(r"SurroundingSphere\s+(\S+)", t)
    return V, (sphere.group(1) if sphere else None), t

def rmin_of(sh, po):
    if not sh: return 1e9
    p = [float(x) for x in (po or "0 0 0").split()]
    s = sh.split()
    if s[0]=="PCON":
        nz=int(s[3]); return min(float(s[5+3*i]) for i in range(nz))  # min rmin over planes
    if s[0]=="BRIK":
        hx,hy=float(s[1]),float(s[2]); return max(0.0, math.hypot(p[0],p[1])-math.hypot(hx,hy))
    return math.hypot(p[0],p[1])

def main():
    args=[a for a in sys.argv[1:] if not a.startswith("--")]
    results=None
    if "--results" in sys.argv:
        import json
        results=json.loads(Path(sys.argv[sys.argv.index("--results")+1]).read_text())
    cand = args[0]; cdir = Path(args[1]) if len(args)>1 else Path(cand).parent
    Vb,sb,_ = parse(BASELINE); Vc,sc,tc = parse(cand)
    fails=[]; warns=[]

    # C1: no baseline volume modified (only ADDING new volumes is allowed)
    modified=[n for n in Vb if n in Vc and Vc[n]!=Vb[n]]
    removed=[n for n in Vb if n not in Vc]
    # name-protected CRITICAL layers (TES / cold finger / Cryoperm) reported first & explicitly
    crit=[n for n in modified+removed if n.startswith(CRITICAL)]
    if crit:
        fails.append(f"C1-CRITICAL forbidden layer changed (TES/coldfinger/Cryoperm): "+", ".join(crit[:6]))
    other_mod=[n for n in modified if not n.startswith(CRITICAL)]
    if other_mod:
        fails.append(f"C1 baseline structure MODIFIED ({len(other_mod)}): "+", ".join(other_mod[:6])
                     +("..." if len(other_mod)>6 else ""))
    if [n for n in removed if not n.startswith(CRITICAL)]:
        fails.append(f"C1 baseline volume REMOVED: "+", ".join([n for n in removed if not n.startswith(CRITICAL)][:6]))
    added=[n for n in Vc if n not in Vb]

    # C2: added shield must be passive metal, NOT a scintillator in the cold region
    for n in added:
        sh,po,ma = Vc[n]
        if ma in SCINT and rmin_of(sh,po) < COLD_R:
            fails.append(f"C2 scintillator '{ma}' added in cold region (r={rmin_of(sh,po):.1f}<{COLD_R}): {n}")
        if ma not in ALLOWED_SHIELD and ma not in SCINT:
            warns.append(f"C2? added volume material '{ma}' not in allowed shield set: {n}")

    # C3: same SurroundingSphere (flux normalization base)
    if sb != sc: fails.append(f"C3 SurroundingSphere changed: baseline {sb} vs candidate {sc}")

    # C4: no ROI/PointSource/HomogeneousBeam in BACKGROUND/signal source cards.
    # (overlap-check sources legitimately use a PointSource for the geometry test -> excluded)
    for src in list(cdir.glob("**/*.source"))[:500]:
        if "overlap" in src.name.lower(): continue
        s=src.read_text()
        for bad in ("PointSource","HomogeneousBeam","ROI"):
            if re.search(rf"\b{bad}\b", s): fails.append(f"C4 forbidden '{bad}' in production source {src.name}")

    # C5: overlap log clean if present
    for log in list(cdir.glob("**/*overlap*.log"))[:10]:
        no=log.read_text().count("Overlap is detected")
        if no>0: fails.append(f"C5 geometry has {no} overlaps in {log.name}")

    # RESULT GATES (only when MC results JSON is supplied): prompt / delayed / signal
    if results is not None:
        pr=results.get("prompt_cps"); de=results.get("delayed_cps"); deb=results.get("baseline_delayed_cps")
        sk=results.get("signal_keep")
        if pr is None or pr>OLD_PROMPT_CPS:
            fails.append(f"G-prompt: prompt_cps={pr} not ≤ old {OLD_PROMPT_CPS}")
        if de is not None and deb is not None:
            if de>deb*(1+DELAYED_TOL):
                fails.append(f"G-delayed: delayed {de} > baseline {deb}×(1+{DELAYED_TOL})  (NET balance, must be MC)")
        else:
            fails.append("G-delayed: delayed_cps / baseline_delayed_cps missing (delayed MC not closed)")
        if sk is None or sk<SIGNAL_KEEP_MIN:
            fails.append(f"G-signal: signal_keep={sk} not ≥ {SIGNAL_KEEP_MIN}")

    print(f"candidate: {cand}" + ("  [+results gate]" if results is not None else "  [geometry-only]"))
    print(f"  added volumes: {len(added)} | baseline modified: {len(modified)} | removed: {len(removed)}")
    for w in warns: print("  WARN:", w)
    if fails:
        print("RESULT: FAIL"); [print("  FAIL:",f) for f in fails]; sys.exit(1)
    print("RESULT: PASS (all hard constraints satisfied)"); sys.exit(0)

if __name__=="__main__": main()
