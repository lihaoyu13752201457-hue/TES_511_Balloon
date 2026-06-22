# Prompt-511 Hybrid W/CsI Shroud Review 2026-06-20

Status: `PROMPT_OLDLIKE_ORDER__NEUTRON_COST__ISOTOPE_RED_FLAG__NO_AUTHORITY_PROMOTION`

This review separates two objects:

- Claude's revised `jacket_W_liner_variantB` geometry remains
  `NO_PROMOTION`: its W liner stops at `z=1 cm`, so many upper-z side-wall
  prompt-511 rays are not actually intercepted. The predictor over-counted
  caught events because it did not require the ray/radius crossing to be inside
  the W liner z extent.
- The hybrid W/CsI shroud tested here is a separate candidate built after that
  finding. It is not a delayed-source, Step06, Step07, Step08, or paper
  authority.

## Candidate Geometry

Candidate directory:

`outputs/reports/prompt511_hybrid_w_csi_shroud_20260620`

Generated setup:

`geometry_hybrid_w_csi_shroud/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_hybrid_w_csi_shroud.geo.setup`

Added material:

| family | geometry | mass |
|---|---|---:|
| thin W shadow | `r=12.35..12.8 cm`, lower/port-side `z=-13..1 cm`, upper-notched `z=1.05..13.35 cm` | `17.675652 kg` |
| active CsI upper shroud | 8 segments, `r=13.6..18.0 cm`, `z=5.55..15.35 cm` | `19.305998 kg` |
| total added | W + CsI | `36.98165 kg` |

The side signal port is preserved rather than ROI-cut:

- approximate port azimuth: `phi=171..189 deg`;
- approximate port z range: `z=-7.2..-3.2 cm`;
- no source spot/ROI restriction was used in prompt tests.

## Mechanical / Source Checks

- Geometry/source builders passed `python3 -m py_compile`.
- Source-card audit found 8 full-sphere particle cards with 20
  `FarFieldAreaSource` beams each, `farfield_radius_cm=60`, and no
  `PointSource`, focal spot, or ROI source restriction.
- Fresh `cosima` overlap/load smoke exited 0 with no visible `GeomVol`,
  `G4Exception`, or overlap warning.

## Prompt L1-Like Proxy

Prompt-only transport completed successfully:

| particle | jobs | failures |
|---|---:|---:|
| eplus | 4 | 0 |
| n | 16 | 0 |
| muplus | 80 | 0 |

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold in the proxy: `50 keV`.

| tag | case | raw events | raw cps | L1-like events | L1-like cps |
|---|---:|---:|---:|---:|---:|
| eplus | current baseline | 97 | 0.0658845 | 80 | 0.0543377 |
| eplus | hybrid | 20 | 0.0271414 | 17 | 0.0230702 |
| n | current baseline | 115 | 0.0780401 | 6 | 0.00407166 |
| n | hybrid | 206 | 0.0698892 | 35 | 0.0118744 |
| muplus | current baseline | 11 | 0.00740652 | 1 | 0.00067332 |
| muplus | hybrid | 63 | 0.00427478 | 0 | 0 |

Total prompt projection:

- current official prompt total: `0.0590827 cps`;
- hybrid prompt projection: `0.0349446 cps`;
- old `new_geo_re` prompt total: `0.0323247 cps`;
- hybrid/old ratio: `1.08105`.

Interpretation: the hybrid candidate fixes most of the current e+ prompt
excess and brings the prompt rate back to old-like order, but it does not beat
old `new_geo_re`. The main remaining cost is neutron-driven hard-window
survival: `n` L1-like prompt rises from `0.00407166` to `0.0118744 cps`.

## Isotope-Store Smoke

Buildup isotope-store smoke:

| item | value |
|---|---:|
| jobs | 16 |
| failures | 0 |
| events generated | 1,380,258 |
| DAT files | 16 |
| all-volume RP smoke value | 8557 |
| added-volume RP smoke value | 2425 |
| added-volume fraction | 28.339% |
| added Hybrid CsI smoke value | 1749 |
| added Hybrid W smoke value | 676 |

Added-volume isotope records are dominated by neutrons:

| particle | added-volume smoke value |
|---|---:|
| n | 2386 |
| muminus | 27 |
| p | 10 |
| alpha | 2 |

Top added-volume nuclides:

| nuclide | smoke value |
|---|---:|
| Cs-134 | 1015 |
| I-128 | 679 |
| W-183 | 364 |
| W-187 | 199 |
| W-185 | 89 |

Interpretation: the isotope store works and shows a real added-material
activation signal. This is not yet a delayed-rate result, because no half-life
folding, RPIP delayed source build, day-20 normalization, delayed transport, or
W2/Step08 selection was run.

## Review Decision

Do not promote Claude's revised VariantB as fixed.

Do not promote the hybrid W/CsI shroud to authority yet either. It is the first
tested candidate that gets current prompt close to old `new_geo_re` order
without ROI/source restriction, but it has two unresolved costs:

1. prompt neutron L1-like rate increases by about `2.92x` versus current;
2. added W/CsI volumes contribute `28.339%` of the smoke RP inventory in this
   low-stat isotope-store run.

Acceptable next step: tune the hybrid, keeping the thin W shadow that suppresses
e+ prompt while reducing neutron/activation burden, then repeat exactly the
same gate sequence:

1. overlap/load smoke;
2. prompt-only e+ L1 proxy, no ROI and no isotope store;
3. n and mu+ prompt-only proxy only if e+ passes;
4. isotope-store buildup smoke only if prompt remains old-like;
5. focused signal replay to prove the side aperture does not clip the Laue spot.
