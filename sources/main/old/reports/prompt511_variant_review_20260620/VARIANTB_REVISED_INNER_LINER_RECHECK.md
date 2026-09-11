# VariantB Revised Inner W Liner Recheck 2026-06-20

Status: `NO_PROMOTION__PREDICTOR_Z_BUG__UPPER_Z_UNCOVERED`

This recheck covers:

`outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_variantB_megalib_proxy`

## Geometry Delta

Relative to `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy`, the revised
VariantB geometry only adds three passive W volumes:

- `Inner_W_JacketLiner_arc`: `PCON 189 342`, `r=11.9..12.8 cm`,
  local `z=-13..1 cm`.
- `Inner_W_JacketLiner_port_below`: port-sector fill below the beam tunnel.
- `Inner_W_JacketLiner_port_above`: port-sector fill above the beam tunnel.

The remaining open signal tunnel is approximately:

- `phi=171..189 deg`
- `z=-7.2..-3.2 cm`
- `r=11.9..12.8 cm`

This port is not smaller than the current side Be window in the transverse
proxy sense: the current Be window is `BRIK 0.0075 1.898 1.898`, i.e. full
height/width about `3.796 cm`, while the W liner port is about `4.0 cm` high
and `12.35 * 18 deg = 3.88 cm` wide at the liner radius.

## Load / Overlap

Fresh command:

```bash
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_variantB_megalib_proxy/overlap_check.source
```

Result: exit code 0. No `GeomVol`, `G4Exception`, or overlap warning appeared
in the fresh run output. The existing saved `cosima_overlap.log` also has no
`GeomVol`/`Overlap` diagnostic beyond the command line.

This means the geometry is loadable and overlap-clean at the smoke level.

## Main Finding

The README/predictor claim of `77/80` caught events is not supported by the
actual W volume extent in the `.geo`.

Root cause: `predict_jacket_liner_catch.py` checks whether the ray crosses
`r=12.35 cm` and whether that crossing is inside the signal port, but it does
not require the crossing to be inside the liner total z extent (`z=-13..1 cm`).
Many selected prompt-511 rays cross the liner radius above `z=1 cm`, where this
geometry has no W.

Independent ray-shell recheck against
`outputs/reports/prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json`
using the actual W volume:

| category | events | rate cps |
|---|---:|---:|
| hit actual W volume | 33/80 | 0.022414321 |
| miss above liner (`z>1`) | 45/80 | 0.030564984 |
| through signal port | 1/80 | 0.000679222 |
| no radius crossing / born inside | 1/80 | 0.000679222 |

Using the same attenuation assumption as the predictor
(`0.9 cm W = 91% removal`), the exact shell-intersection residual estimate is:

`0.033940716 cps`

This is consistent with the earlier `prompt511_variant_review_20260620` result
(`33/80`, residual about `0.034 cps`) and is not enough margin against old
`new_geo_re` once neutron and muon prompt components are included.

## Z-Extent Sensitivity

Keeping the same radius and port, but changing the upper z extent gives:

| W liner z range cm | W-hit events | attenuated residual cps |
|---|---:|---:|
| `[-13, 1]` | 33/80 | 0.033940716 |
| `[-13, 5]` | 50/80 | 0.023433154 |
| `[-13, 10]` | 67/80 | 0.012925592 |
| `[-13, 13.35]` | 71/80 | 0.010453224 |
| `[-13, 20]` | 76/80 | 0.007362765 |
| `[-13, 30]` | 78/80 | 0.006126581 |

Approximate W mass for this shell, with only the signal port removed:

| upper z cm | mass kg |
|---:|---:|
| 1 | 18.60 |
| 5 | 23.99 |
| 10 | 30.73 |
| 13.35 | 35.25 |
| 20 | 44.21 |
| 30 | 57.69 |

Therefore the current revised VariantB is in the right geometric family, but it
stops too low in z. Extending upward may solve the e+ proxy leakage, but the
mass, neutron production, and W activation costs become the central risks.

## Review Decision

Do not promote this geometry as fixed.

Acceptable next step: build a new candidate that extends this liner or an
old-like active/passive side column upward enough to cover the upper
OVC/side-wall ray crossings, then run:

1. overlap check;
2. prompt-only e+ L1 proxy with no ROI and no isotope store;
3. prompt-only n and mu+ L1 proxy if e+ passes;
4. isotope-record buildup smoke only after prompt passes;
5. focused signal replay to prove the physical side aperture does not clip the
   Laue spot.

Do not use `predict_jacket_liner_catch.py` as written for promotion decisions.
