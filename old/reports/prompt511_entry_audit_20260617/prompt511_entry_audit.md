# Prompt 511 Entry Audit, 2026-06-17
Current authority: `fullstat_v2_exactpos_m50000_s260613`. Window: `510.58-511.42 keV`; active-veto threshold `50 keV`.
## Rate Decomposition
| case | final prompt cps | final delayed cps | ratio | final prompt eplus cps | prompt eplus events |
|---|---:|---:|---:|---:|---:|
| old (delayed/prompt) | 0.0323247092031 | 0.151456825339 | 4.68548 | 0.0244744226824 | 106 |
| current (prompt/delayed) | 0.0590827246325 | 0.00389763720735 | 15.1586 | 0.0543377485018 | 80 |

## Eplus Prompt Stage Ratios
| stage | old events/cps | current events/cps | current/old cps | surface-normalized efficiency ratio |
|---|---:|---:|---:|---:|
| raw | 126 / 0.0290922382828 | 97 / 0.0658845200584 | 2.26468 | 0.770619 |
| active | 116 / 0.0267833304826 | 85 / 0.0577338577832 | 2.15559 | 0.733499 |
| final | 106 / 0.0244744226824 | 80 / 0.0543377485018 | 2.22019 | 0.75548 |

## Difference-Source Diagnosis
The current/old final prompt-eplus rate ratio is `2.22019`, but this is not because current selects more events. Current selects fewer final eplus events: `80/106 = 0.754717`. The absolute cps rises because the per-event source weight rises from `0.0002308907800224599` to `0.0006792218562725798` cps, a factor of `2.94175`, matching the far-field area ratio `(60/35)^2 = 2.93878`. If current's `80` final events are weighted with the old per-event weight, the rate is only `0.0184713` cps, i.e. `0.754717` of the old prompt-eplus rate. Thus the absolute old/current prompt-eplus cps increase is dominated by source-surface normalization / enclosing far-field radius, while the geometry-only selected-event efficiency is lower in the current chain.

The geometry change still matters, but in a different way: it changes where the surviving prompt-eplus events enter. Old selected prompt-eplus events are dominated by the old outer/top shell and axial stack (`Outer_Al_Mech_Shell` is the first-primary volume for `90/106` events), with TES centroids in the old axial stack. Current selected prompt-eplus events are dominated by side-port/side-wall volumes (`61/80` first-primary and last-primary categories), and `77/80` are non-window paths under the side-window crossing proxy. So the mass-model/geometry issue is not "the Be window transmits too much"; it is that the current side-entry aperture creates a non-window side-wall/side-port leakage mode that old `new_geo_re` did not have. Old `new_geo_re` blocks the corresponding side line with solid CsI plus passive/cryostat material.

## Source Card / Normalization Check
- eplus flux is identical: old `0.116980545723`, current `0.116980545723` cm^-2 s^-1.
- base eplus events are identical: old/current `243727` / `243727` per source card; full prompt run uses 8 non-gamma replicas in both.
- far-field radius changed `35.0` -> `60.0` cm, area ratio `2.93878`; current geometry bounding radius is `49.5718` cm.
- current pointing policy: incoming side-axis `[0.7071067811865476, -0.0, -0.7071067811865475]`; local side window looks `[-0.7071067811865476, 0.0, 0.7071067811865475]`.

## TES Centroids
| case | events | weighted centroid x,y,z,layer cm | x quantiles | z quantiles | layer counts rounded |
|---|---:|---|---|---|---|
| old_eplus_prompt_final | 106 | (-0.2824, 0.09301, 4.576, 2.83) | [-1.503, -1.338, -1.021, -0.513, 0.497, 1.097, 1.487] | [1.038, 1.19, 2.317, 4.89, 7.117, 7.223, 7.299] | {'0': 20, '1': 15, '2': 9, '3': 10, '4': 24, '5': 28} |
| current_eplus_prompt_final | 80 | (-3.843, 0.1281, -3.264, 2.16) | [-6.508, -5.558, -5.025, -4.12, -2.466, -1.77, -0.518] | [-6.783, -5.349, -4.515, -2.95, -2.129, -1.111, -0.491] | {'0': 17, '1': 19, '2': 9, '3': 12, '4': 15, '5': 8} |
| old_prompt_final | 126 | (-0.1426, 0.03843, 4.48, 2.752) | [-1.503, -1.31, -1.012, -0.223, 0.556, 1.115, 1.487] | [1.027, 1.185, 2.252, 4.854, 6.079, 7.21, 7.299] | {'0': 29, '1': 17, '2': 10, '3': 12, '4': 28, '5': 30} |
| current_prompt_final | 87 | (-3.811, 0.09368, -3.266, 2.177) | [-6.508, -5.605, -5.014, -4.101, -2.463, -1.748, -0.518] | [-6.783, -5.364, -4.477, -3.016, -1.965, -1.141, -0.491] | {'0': 18, '1': 21, '2': 9, '3': 13, '4': 18, '5': 8} |

## Selected Eplus SIM Track Proxy
| case | events | first-primary volume categories | last-primary volume categories | ann z quantiles | init-dir dot(side-axis) q | ann-to-TES dot(side-axis) q | side-disk segment proxy |
|---|---:|---|---|---|---|---|---:|
| old_eplus_prompt_final | 106 | {'outer_shell_or_jacket': 90, 'missing': 12, 'other': 4} | {'outer_shell_or_jacket': 88, 'missing': 12, 'other': 3, 'passive_liner': 2, 'window': 1} | [-6.641, -3.246, 0.982, 7.201, 13.933, 15.748, 15.985] | [-0.903, -0.814, -0.557, -0.006, 0.376, 0.697, 0.94] | [-0.988, -0.608, -0.433, 0.045, 0.549, 0.806, 0.998] | 0/106 |
| current_eplus_prompt_final | 80 | {'side_port_or_side': 61, 'outer_shell_or_jacket': 14, 'missing': 5} | {'side_port_or_side': 61, 'outer_shell_or_jacket': 14, 'missing': 5} | [-18.393, -10.901, -3.09, 4.004, 12.249, 14.549, 54.207] | [-0.995, -0.785, -0.602, -0.048, 0.426, 0.776, 0.994] | [-0.991, -0.711, -0.538, 0.178, 0.631, 0.816, 0.997] | 1/80 |

## Forced Current-Side-Axis Subset
Definition: final prompt eplus events with annihilation-to-TES unit vector dot the current side-entry axis above the threshold. This is a direct stress test of the proposed "corresponding direction" comparison.
| threshold | case | events | rate cps | last-primary category counts | TES z quantiles | rounded TES layer counts |
|---:|---|---:|---:|---|---|---|
| 0.5 | old | 30 | 0.00692672340067 | {'outer_shell_or_jacket': 24, 'other': 3, 'missing': 1, 'window': 1, 'passive_liner': 1} | [1.038, 1.19, 2.355, 5.879, 7.299] | {'0': 12, '4': 5, '5': 5, '1': 4, '2': 2, '3': 2} |
| 0.5 | current | 27 | 0.0183389901194 | {'side_port_or_side': 19, 'outer_shell_or_jacket': 5, 'missing': 3} | [-6.783, -3.154, -2.305, -1.673, -0.491] | {'1': 10, '0': 7, '2': 4, '4': 2, '3': 2, '5': 2} |
| 0.7 | old | 16 | 0.00369425248036 | {'outer_shell_or_jacket': 14, 'passive_liner': 1, 'other': 1} | [1.084, 1.084, 3.521, 6.343, 7.299] | {'0': 5, '5': 4, '1': 3, '3': 2, '4': 2} |
| 0.7 | current | 16 | 0.0108675497004 | {'side_port_or_side': 12, 'outer_shell_or_jacket': 2, 'missing': 2} | [-6.783, -2.805, -2.115, -1.6, -0.491] | {'0': 6, '1': 6, '4': 1, '2': 1, '3': 1, '5': 1} |
| 0.8 | old | 11 | 0.00253979858025 | {'outer_shell_or_jacket': 10, 'passive_liner': 1} | [1.084, 1.084, 2.343, 5.359, 7.227] | {'0': 5, '3': 2, '4': 2, '1': 1, '5': 1} |
| 0.8 | current | 13 | 0.00882988413154 | {'side_port_or_side': 10, 'missing': 2, 'outer_shell_or_jacket': 1} | [-6.783, -2.863, -2.464, -1.746, -0.491] | {'1': 5, '0': 4, '4': 1, '2': 1, '3': 1, '5': 1} |

## Window Versus Non-Window Leakage
Strict window definition: the selected eplus annihilation-to-TES line must cross both the current outer Al filter and Be side-window discs inside `r=1.898 cm`. Under that strict definition, window leakage is `1/80` events (`0.000679221856273 cps`), while non-window leakage is `77/80` events (`0.052300082933 cps`). Even the broad "any window/foil disc" proxy is only `3/80` events (`0.00203766556882 cps`).

Non-window selected events are dominated by side-port/side-wall or outer-shell primary volumes: `{'side_port_or_side_wall': 59, 'outer_shell_or_jacket': 14, 'missing': 4}`. This means the current prompt eplus W2 excess is mostly not photons entering through the intended thin Be/window stack; it is 511 photons born in or near the side-port/side-wall mass and then reaching TES through non-window geometry around the side aperture.

## Old Geometry Blocker At Current Leak Region
Place the current side-entry axis into old `new_geo_re` as the side line `y=0, z=-5.2 cm`. The old optical windows are not there; they are axial/top windows at `z≈8.55-13.41 cm` plus the top W aperture at `z≈16 cm`. On the side line, old `new_geo_re` instead has solid shielding. The dominant piece is the solid CsI active side shield, `r=10.05-14.05 cm`, i.e. `4.0 cm` of CsI, followed outside by Al/Kapton packaging and the outer Al mechanical shell; inside it also has Al vacuum jacket plus Cu/W passive liners.

Old side-line material thickness proxy, outside-to-inside, is summarized in `/home/ubuntu/TES_511_Balloon/outputs/reports/prompt511_entry_audit_20260617/prompt511_entry_audit_summary.json` under `old_new_geo_re_current_side_region_blocker`. The main physical answer is: old `new_geo_re` blocked the current high-leakage side region primarily with the active CsI side panel, while current v3p5 explicitly cuts a side hole through the CsI/liners/outer shell and inserts only a W sleeve around the open bore.

## Old Geometry Current-Like Region Check
Using the current final eplus 10-90% TES global x envelope `[-5.558087982764141, -1.7700753374726166]` and z envelope `[-5.3493099839098806, -1.1107841320592435]`, old final eplus has `0` events (`0 s^-1`) in that region.

## Direction-Filtered Old Check
Filtering by `dot(annihilation_to_TES, current_side_axis) >= 0.8` gives old `11` events (`0.00253979858025 s^-1`) with TES z quantiles `[1.084, 1.084, 2.343, 5.359, 7.227]` and last-primary volumes dominated by `Outer_Al_Mech_Shell` (`10/11`). The same filter in current gives `13` events (`0.00882988413154 s^-1`) with TES z quantiles `[-6.783, -2.863, -2.464, -1.746, -0.491]` and side-wall/side-port last-primary volumes. This says the old geometry's corresponding direction subset still deposits in the old axial/top-stack geometry, not in the current side-port TES region.

## Prompt Incidence 2D Schematic
Generated diagnostic figure:

- PNG: `outputs/reports/prompt511_entry_audit_20260617/prompt511_prompt_incidence_xz_comparison.png`
- SVG: `outputs/reports/prompt511_entry_audit_20260617/prompt511_prompt_incidence_xz_comparison.svg`
- Builder: `outputs/reports/prompt511_entry_audit_20260617/build_prompt511_prompt_incidence_figure.py`

The figure uses the last primary eplus interaction position when available, otherwise the annihilation point, and draws a proxy 511 path to the selected TES centroid. The current panel is in the v3p5 local side-entry x-z frame, while the old panel is in the old global x-z frame. The visual conclusion is the same as the numeric audit: current final eplus prompt leakage is dominated by non-window side-port/side-wall paths (`77/80`, `0.052300082933 s^-1`), while the old geometry's corresponding side line is a solid material column dominated by `4.0 cm` of CsI plus Cu/Fe/Al passive mass, not a side window.

## Prompt Interaction-Track 2D Schematic
Generated detailed interaction-track figure:

- PNG: `outputs/reports/prompt511_entry_audit_20260617/prompt511_track_interactions_xz_comparison.png`
- SVG: `outputs/reports/prompt511_entry_audit_20260617/prompt511_track_interactions_xz_comparison.svg`
- IA point CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_track_interaction_points.csv`
- Builder: `outputs/reports/prompt511_entry_audit_20260617/build_prompt511_track_interaction_figure.py`

This figure parses original SIM event blocks and plots IA interaction processes (`ANNI`, `COMP`, `PHOT`, `BREM`, `PAIR`, `RAYL`) with parent-child IA links. For readability it samples up to `32` final W2 selected prompt-eplus events per geometry and up to `100` no-TES side-shield/side-material events per geometry. It is therefore a track-level diagnostic, not a replacement for the rate table above. The bottom panels are the direct "where does it get stopped" view: old `new_geo_re` side-line events concentrate in the solid side shield/material column, while current v3p5 no-TES events concentrate around the side-port/side-wall neighborhood.

## Prompt Material Ledger Diagnostic
Generated event-level material/path ledger:

- Report: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger.md`
- Event CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger_events.csv`
- Segment CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger_segments.csv`
- Stack figure PNG: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_path_stacks.png`
- Builder: `outputs/reports/prompt511_entry_audit_20260617/build_prompt511_material_ledger.py`

This ledger uses the same selected/shielded samples as the interaction-track
figure (`32` selected plus `100` no-TES side/shield samples per geometry). SIM
does not contain full material-boundary step logs, so the reported path length
is a straight-line IA parent-child distance after annihilation, grouped by the
downstream interaction material inferred from the nearest CC hit. It is not an
exact passive-volume chord integral.

The current selected sample has `32/32` TES stops and is dominated by
post-annihilation branches whose downstream endpoint material is `Ta/TES`
(median path proxy `47.8 cm`, median shield/material CC energy deposition
`56.6 keV`). The current no-TES side/shield sample has `0/100` TES stops and
terminates mainly in `CsI` (`49/100`) and `Aluminium` (`37/100`), with median
shield/material energy deposition `517 keV`. This is the quantitative track
picture of the side-port problem: the events that are stopped are stopped by
side shield material; the selected survivors are not traversing a continuous
old-style side material column before reaching TES.

## Prompt Geometry Ray-Trace Ledger
Generated deterministic straight-line geometry chord ledger:

- Report: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_ledger.md`
- Event chord CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_event_chords.csv`
- Volume segment CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_volume_segments.csv`
- Fixed-line CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_line_chords.csv`
- Summary JSON: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_summary.json`
- Builder: `outputs/reports/prompt511_entry_audit_20260617/build_prompt511_raytrace_ledger.py`

This audit traces SIM annihilation-to-TES proxy lines and fixed side-axis lines
through the old/current MEGAlib `.geo` files. It uses the deepest placed volume
on each line segment, so mother/child geometry overlaps are not double-counted.
It is a geometry chord audit only; it does not model attenuation, scattering, or
Geant4 step histories.

The fixed side-axis blocker test is the strongest result. In current v3p5, the
intended side-window segment has only `Be:0.015 cm` plus `Aluminium:0.013 cm`
before the detector region. Along the corresponding old `new_geo_re`
outer-to-inner side line, the path has `CsI:4.0 cm`, `Copper:1.63 cm`,
`LowCarbonSteel:1.17 cm`, `Aluminium:1.10 cm`, `StainlessSteel:0.25 cm`,
`G10:0.16 cm`, `W:0.06 cm`, and `Kapton:0.05 cm`. This directly supports the geometry
interpretation: old `new_geo_re` blocks the current high-leakage side region
with a real side-shield material column, while current v3p5 exposes a thin
side-window/side-port path.

For current selected final prompt-eplus events, the median non-Ta material
chord from annihilation to TES is `3.865 cm`; for the current non-window subset
it is `4.412 cm`. These survivor lines are therefore usually born in the
side-wall/side-port neighborhood after the outer blocker has already been
bypassed, not through the nominal Be/Al window disc.

## Interpretation Boundaries
- This audit uses catalog TES centroids and SIM annihilation/primary-volume records; it is not a full boundary-crossing replay through every passive surface.
- The selected eplus samples are low-count but are the full final hard-window selected samples available in the old/current catalogs.
- The interaction-track schematic samples events for legibility; use `prompt511_entry_audit_summary.json` for quantitative rates and class fractions.
