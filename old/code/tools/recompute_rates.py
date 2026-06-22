#!/usr/bin/env python3
"""Independent numerical verifier for a prompt-511 shield candidate.
Re-derives, from RAW primitives (line-event count, rate_per_event, N_generated), the things
that are easy to fake by mis-normalization or over-claim:
  1. flux x area  = rate_per_event * N_generated   -> MUST match baseline (the x8-bug zone)
  2. suppression  = baseline_cps / candidate_cps   (+ Poisson errors)
  3. significance of "candidate <= old"            (is the win real or within noise?)
This is the Verifier's TOOL: it runs a script, it does not eyeball a report.

Usage:
  recompute_rates.py --base-events 80 --base-rate 6.792218562725798e-4 --base-ngen 1949816 \
                     --cand-events 19 --cand-rate 1.3570704138236578e-3 --cand-ngen 974908 \
                     [--old-cps 0.0323247] [--label eplus]
"""
import sys, math

def arg(name, default=None, cast=float):
    if name in sys.argv:
        return cast(sys.argv[sys.argv.index(name)+1])
    return default

def main():
    be=arg("--base-events"); br=arg("--base-rate"); bn=arg("--base-ngen")
    ce=arg("--cand-events"); cr=arg("--cand-rate"); cn=arg("--cand-ngen")
    old=arg("--old-cps", None); label=arg("--label","", str)
    for v,n in [(be,"--base-events"),(br,"--base-rate"),(bn,"--base-ngen"),
                (ce,"--cand-events"),(cr,"--cand-rate"),(cn,"--cand-ngen")]:
        if v is None: print(f"missing {n}"); sys.exit(2)
    fails=[]
    print(f"=== recompute_rates [{label}] ===")

    # 1. normalization consistency (convention-independent: flux*area must be equal)
    fa_b = br*bn; fa_c = cr*cn
    rel = abs(fa_b-fa_c)/fa_b
    print(f"flux*area  baseline={fa_b:.3f}  candidate={fa_c:.3f}  rel.diff={100*rel:.2f}%")
    if rel > 0.02:
        fails.append(f"NORMALIZATION mismatch {100*rel:.1f}% (flux*area must match; suspect x8-family bug)")
    else:
        print("  -> normalization CONSISTENT (per-event weight correctly tracks N_generated)")

    # 2. rates + Poisson errors
    bcps=be*br; ccps=ce*cr
    bcps_e=math.sqrt(be)*br; ccps_e=math.sqrt(ce)*cr
    print(f"baseline  cps={bcps:.5f} +/- {bcps_e:.5f} ({be} ev, Ngen={bn:.0f})")
    print(f"candidate cps={ccps:.5f} +/- {ccps_e:.5f} ({ce} ev, Ngen={cn:.0f})")
    if ccps>0:
        supp=bcps/ccps; supp_e=supp*math.sqrt(1/be+1/ce)
        print(f"suppression = {supp:.2f} +/- {supp_e:.2f}")
    if ce < 30:
        print(f"  WARN: candidate has {ce} line events (<30) -> large Poisson error; treat as smoke")

    # 3. significance of candidate <= old
    if old is not None:
        z=(old-ccps)/ccps_e if ccps_e>0 else float('inf')
        print(f"old target={old:.5f};  (old-candidate)/sigma_candidate = {z:.2f} sigma")
        if z < 2:
            print(f"  -> 'below old' is NOT established (<2 sigma); honest claim = 'same order'")
        else:
            print(f"  -> candidate below old at {z:.1f} sigma")

    print("VERDICT:", "FAIL" if fails else "PASS (numbers self-consistent)")
    for f in fails: print("  FAIL:", f)
    sys.exit(1 if fails else 0)

if __name__=="__main__": main()
