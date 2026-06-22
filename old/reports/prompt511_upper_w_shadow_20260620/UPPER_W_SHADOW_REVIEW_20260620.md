# Prompt-511 Upper W Shadow Review 2026-06-20

Status: `DIAGNOSTIC_PROMPT_PASS__NO_PROMOTION`

This is a local prompt/isotope smoke for the notched upper-W-shadow candidate.
It is not a rate authority, delayed-source result, Step06/07/08 result, or final
geometry recommendation.

## Geometry

- Candidate setup:
  `outputs/reports/prompt511_upper_w_shadow_20260620/geometry_upper_w_shadow/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_upper_w_shadow_r12p35_12p8.geo.setup`
- Added W:
  - lower non-port arc: `r=12.35..12.8 cm`, `z=-13..1 cm`, `phi=189..531 deg`
  - port fill below/above the real signal gap: `phi=171..189 deg`, `z=-13..-7.2` and `z=-3.2..1 cm`
  - upper notched band: `r=12.35..12.8 cm`, `z=1.05..28 cm`, `phi=5..355 deg`
- Signal sector left open: `phi=171..189 deg`, `z=-7.2..-3.2 cm`.
- Estimated added W mass: `27.4494 kg`.
- Overlap/load gate: pass. `overlap_upper_w_shadow.log` has no `GeomVol`/overlap/error report and completed the `Minimum` run.

## Why This Replaces VariantB

VariantB's proxy only tested one mid-radius crossing and missed the actual z
coverage of its W volumes.  The corrected ray gate integrates path length through
the real PCON z/phi coverage.

Corrected selected-event proxy for this candidate:

- caught selected current e+ prompt events: `77/80`
- caught rate: `0.0523001 cps`
- missed rate: `0.00203767 cps`
- W path-length stats: median `0.553784 cm`, rate-weighted mean `0.599953 cm`
- path-weighted residual estimates:
  - with `mu/rho=0.0918 cm2/g`: `0.0208324 cps`
  - with `mu/rho=0.137 cm2/g`: `0.0136561 cps`

## Prompt Smoke

Prompt-only runs used the current fullsphere source cards with only `Geometry`
changed, `farfield-radius-cm=60.0`, and `--disable-isotope-store`.

High-stat Step05-like proxy results:

| tag | current L1-like cps | upper-W-shadow L1-like cps |
|---|---:|---:|
| eplus | `0.0543377` | `0.0149278` |
| n | `0.00407166` | `0.0101780` |
| muplus | `0.000673320` | `0.000135707` |

Total prompt projection:

- current prompt total: `0.0590827 cps`
- candidate eplus+n+muplus prompt: `0.0252415 cps`
- old `new_geo_re` prompt total: `0.0323247 cps`
- candidate/old ratio: `0.780874`

Low-stat all-particle gross prompt smoke found no nonzero L1-like tags outside
the high-stat eplus/n/muplus channels. This is a screen only, not a zero-channel
upper limit.

## Isotope Recording Smoke

Buildup run:
`outputs/reports/prompt511_upper_w_shadow_20260620/runs/upper_w_shadow_buildup_isotope_g1m_r2`

- jobs: `16/16 PASS`
- generated particles: `1,380,258`
- `.dat.inc1.dat` files: `16/16`
- `.sim.gz` files: `16/16`, gzip check passed
- job sources retained `StoreIsotopes true` and `DecayMode ActivationBuildUp`

Raw isotope-store inventory:

- total raw isotope-store value: `7884`
- added W-shadow raw value: `1693`
- dominant particles: `n=7710`, `p=66`, `muminus=102`, `alpha=5`, `gamma=1`
- top total nuclides: `Cs-134`, `I-128`, `W-183`, `W-187`, `W-185`
- top added-W-shadow records:
  - `Prompt511_UpperWShadow_upper_notched / W-183 / n`: `642`
  - `Prompt511_UpperWShadow_upper_notched / W-187 / n`: `502`
  - `Prompt511_UpperWShadow_lower_nonport_arc / W-183 / n`: `215`
  - `Prompt511_UpperWShadow_upper_notched / W-185 / n`: `137`

Inventory outputs:

- `upper_w_shadow_isotope_inventory_summary.md`
- `upper_w_shadow_isotope_inventory_summary.json`
- `upper_w_shadow_isotope_by_nuclide.csv`
- `upper_w_shadow_isotope_by_volume.csv`
- `upper_w_shadow_isotope_by_particle_nuclide.csv`
- `upper_w_shadow_isotope_w_shadow_records.csv`

## Interpretation

This candidate proves the important mechanism point: the missed current prompt
component is dominated by upper/side non-window leakage paths, and a real
upper-z material column can reduce prompt below old `new_geo_re` order even after
the neutron increase is included.

It should not be promoted as the final geometry.  The fix is W-only, passive,
adds about `27.45 kg` W, increases selected neutron prompt, and records many W
activation products.  The next design route should use this as a geometry
diagnostic and move toward an old-like active/material topology with less W
activation risk, then repeat the same gates.
