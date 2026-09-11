# S3d-O8 LG1 paired smoke diagnostic

Status: `PASS_LG1_SMOKE_PHYSICS_DIAGNOSTIC_NO_RATE_OR_PROMOTION_AUTHORITY`

This is a finite-tape physical diagnostic with no sky normalization. Counts and fractions below are conditional on the prerecorded focused, directional, or forced back-to-back-511 inputs. They are not background rates, mission sensitivities, or a geometry-promotion result.

Diagnostic JSON SHA256: `53cb16dde42148fc9734a71e57dda09074e8d8bdbf8e7d9223e57d303180c330`

## Exact-volume contract

Original active volumes:

- `BGO_S3C_FullWrap_SideShell_WindowCut_40mm`
- `BGO_S3D_O8_FullWrap_BottomCap_30mm`
- `BGO_S3D_O8_FullWrap_TopAnnulus_10mm`
- `GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm`
- `GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm`
- `GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm`

LG1 volumes:

- `BGO_S3D_O8_LG1_OpticalAxis_OpenWell_Side_5mm`
- `BGO_S3D_O8_LG1_OpticalAxis_BackAnnulus_3mm`

## Per-job raw diagnostics

| job | geometry | generated | PAIR events/records | ANNI events/records | TES-hit | raw W2 | old6 ≥50 keV | LG1 ≥1 keV | LG1 ≥50 keV |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| focused_first1000__A | A_baseline | 1000 | 0/0 | 0/0 | 978 | 826 | 64 | 0 | 0 |
| focused_first1000__B | B_lg1 | 1000 | 0/0 | 0/0 | 962 | 817 | 64 | 68 | 66 |
| gamma_root_4148keV_rep01__A | A_baseline | 512 | 152/304 | 152/304 | 14 | 0 | 420 | 0 | 0 |
| gamma_root_4148keV_rep01__B | B_lg1 | 512 | 159/318 | 159/318 | 19 | 3 | 418 | 58 | 57 |
| gamma_root_4148keV_rep02__A | A_baseline | 512 | 155/310 | 155/310 | 13 | 3 | 428 | 0 | 0 |
| gamma_root_4148keV_rep02__B | B_lg1 | 512 | 186/372 | 186/375 | 18 | 3 | 420 | 62 | 62 |
| gamma_root_4148keV_rep03__A | A_baseline | 512 | 173/348 | 173/348 | 14 | 3 | 408 | 0 | 0 |
| gamma_root_4148keV_rep03__B | B_lg1 | 512 | 160/320 | 160/320 | 21 | 2 | 397 | 58 | 58 |
| gamma_root_5769keV_rep01__A | A_baseline | 512 | 260/524 | 259/522 | 1 | 0 | 479 | 0 | 0 |
| gamma_root_5769keV_rep01__B | B_lg1 | 512 | 266/532 | 266/533 | 4 | 2 | 477 | 9 | 9 |
| gamma_root_5769keV_rep02__A | A_baseline | 512 | 239/478 | 239/479 | 3 | 0 | 472 | 0 | 0 |
| gamma_root_5769keV_rep02__B | B_lg1 | 512 | 247/496 | 247/498 | 2 | 0 | 472 | 6 | 6 |
| gamma_root_5769keV_rep03__A | A_baseline | 512 | 263/530 | 262/529 | 1 | 0 | 461 | 0 | 0 |
| gamma_root_5769keV_rep03__B | B_lg1 | 512 | 246/498 | 246/500 | 0 | 0 | 469 | 5 | 5 |
| back_to_back511_successor__A | A_baseline | 24 | 0/0 | 0/0 | 5 | 3 | 13 | 0 | 0 |
| back_to_back511_successor__B | B_lg1 | 24 | 0/0 | 0/0 | 3 | 2 | 13 | 6 | 6 |

## A/B event-count differences

| cell | kind | ΔPAIR events | ΔANNI events | ΔTES-hit | Δraw W2 |
|---|---|---:|---:|---:|---:|
| back_to_back511_successor | forced_back_to_back511_diagnostic | 0 | 0 | -2 | -1 |
| focused_first1000 | focused_signal_prefix | 0 | 0 | -16 | -9 |
| gamma_root_4148keV_rep01 | serialized_directional_gamma | 7 | 7 | 5 | 3 |
| gamma_root_4148keV_rep02 | serialized_directional_gamma | 31 | 31 | 5 | 0 |
| gamma_root_4148keV_rep03 | serialized_directional_gamma | -13 | -13 | 7 | -1 |
| gamma_root_5769keV_rep01 | serialized_directional_gamma | 6 | 7 | 3 | 2 |
| gamma_root_5769keV_rep02 | serialized_directional_gamma | 8 | 8 | -1 | 0 |
| gamma_root_5769keV_rep03 | serialized_directional_gamma | -17 | -16 | -1 | 0 |

## Focused first-1000 diagnostic

TES-hit A/B: 978/962 (B−A -16). Raw-W2 A/B: 826/817 (B−A -9).

| threshold (keV) | A guard∩TES | B guard∩TES | Δ | A guard∩raw-W2 | B guard∩raw-W2 | Δ | B raw-W2 after old6+LG1 | matched A raw-W2 intercepted in B |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 64 | +64 | 0 | 0 | +0 | 817 | 49/826 (0.059322) |
| 5 | 0 | 64 | +64 | 0 | 0 | +0 | 817 | 49/826 (0.059322) |
| 10 | 0 | 64 | +64 | 0 | 0 | +0 | 817 | 49/826 (0.059322) |
| 20 | 0 | 63 | +63 | 0 | 0 | +0 | 817 | 48/826 (0.0581114) |
| 50 | 0 | 62 | +62 | 0 | 0 | +0 | 817 | 47/826 (0.0569007) |
| 80 | 0 | 60 | +60 | 0 | 0 | +0 | 817 | 44/826 (0.0532688) |

## Directional and forced-511 conditional LG1 interception (candidate B)

The denominator is always shown. Undefined zero-denominator conditions are not silently converted to zero probability.

| cell | threshold (keV) | given generated | given IA PAIR | given IA ANNI | given old6 pass | given raw-W2 & old6 pass |
|---|---:|---:|---:|---:|---:|---:|
| back_to_back511_successor | 1 | 6/24 (0.25) | 0/0 (undefined) | 0/0 (undefined) | 5/11 (0.454545) | 0/1 (0) |
| back_to_back511_successor | 5 | 6/24 (0.25) | 0/0 (undefined) | 0/0 (undefined) | 5/11 (0.454545) | 0/1 (0) |
| back_to_back511_successor | 10 | 6/24 (0.25) | 0/0 (undefined) | 0/0 (undefined) | 5/11 (0.454545) | 0/1 (0) |
| back_to_back511_successor | 20 | 6/24 (0.25) | 0/0 (undefined) | 0/0 (undefined) | 5/11 (0.454545) | 0/1 (0) |
| back_to_back511_successor | 50 | 6/24 (0.25) | 0/0 (undefined) | 0/0 (undefined) | 5/11 (0.454545) | 0/1 (0) |
| back_to_back511_successor | 80 | 6/24 (0.25) | 0/0 (undefined) | 0/0 (undefined) | 5/11 (0.454545) | 0/1 (0) |
| gamma_root_4148keV_rep01 | 1 | 58/512 (0.113281) | 24/159 (0.150943) | 24/159 (0.150943) | 25/92 (0.271739) | 0/0 (undefined) |
| gamma_root_4148keV_rep01 | 5 | 58/512 (0.113281) | 24/159 (0.150943) | 24/159 (0.150943) | 25/92 (0.271739) | 0/0 (undefined) |
| gamma_root_4148keV_rep01 | 10 | 58/512 (0.113281) | 24/159 (0.150943) | 24/159 (0.150943) | 25/92 (0.271739) | 0/0 (undefined) |
| gamma_root_4148keV_rep01 | 20 | 58/512 (0.113281) | 24/159 (0.150943) | 24/159 (0.150943) | 25/92 (0.271739) | 0/0 (undefined) |
| gamma_root_4148keV_rep01 | 50 | 57/512 (0.111328) | 23/159 (0.144654) | 23/159 (0.144654) | 24/94 (0.255319) | 0/0 (undefined) |
| gamma_root_4148keV_rep01 | 80 | 56/512 (0.109375) | 22/159 (0.138365) | 22/159 (0.138365) | 24/95 (0.252632) | 0/0 (undefined) |
| gamma_root_4148keV_rep02 | 1 | 62/512 (0.121094) | 23/186 (0.123656) | 23/186 (0.123656) | 32/90 (0.355556) | 3/3 (1) |
| gamma_root_4148keV_rep02 | 5 | 62/512 (0.121094) | 23/186 (0.123656) | 23/186 (0.123656) | 32/90 (0.355556) | 3/3 (1) |
| gamma_root_4148keV_rep02 | 10 | 62/512 (0.121094) | 23/186 (0.123656) | 23/186 (0.123656) | 32/91 (0.351648) | 3/3 (1) |
| gamma_root_4148keV_rep02 | 20 | 62/512 (0.121094) | 23/186 (0.123656) | 23/186 (0.123656) | 32/91 (0.351648) | 3/3 (1) |
| gamma_root_4148keV_rep02 | 50 | 62/512 (0.121094) | 23/186 (0.123656) | 23/186 (0.123656) | 32/92 (0.347826) | 3/3 (1) |
| gamma_root_4148keV_rep02 | 80 | 62/512 (0.121094) | 23/186 (0.123656) | 23/186 (0.123656) | 32/97 (0.329897) | 3/3 (1) |
| gamma_root_4148keV_rep03 | 1 | 58/512 (0.113281) | 24/160 (0.15) | 24/160 (0.15) | 38/113 (0.336283) | 2/2 (1) |
| gamma_root_4148keV_rep03 | 5 | 58/512 (0.113281) | 24/160 (0.15) | 24/160 (0.15) | 38/113 (0.336283) | 2/2 (1) |
| gamma_root_4148keV_rep03 | 10 | 58/512 (0.113281) | 24/160 (0.15) | 24/160 (0.15) | 38/114 (0.333333) | 2/2 (1) |
| gamma_root_4148keV_rep03 | 20 | 58/512 (0.113281) | 24/160 (0.15) | 24/160 (0.15) | 38/115 (0.330435) | 2/2 (1) |
| gamma_root_4148keV_rep03 | 50 | 58/512 (0.113281) | 24/160 (0.15) | 24/160 (0.15) | 38/115 (0.330435) | 2/2 (1) |
| gamma_root_4148keV_rep03 | 80 | 56/512 (0.109375) | 24/160 (0.15) | 24/160 (0.15) | 37/117 (0.316239) | 2/2 (1) |
| gamma_root_5769keV_rep01 | 1 | 9/512 (0.0175781) | 5/266 (0.018797) | 5/266 (0.018797) | 2/35 (0.0571429) | 0/2 (0) |
| gamma_root_5769keV_rep01 | 5 | 9/512 (0.0175781) | 5/266 (0.018797) | 5/266 (0.018797) | 2/35 (0.0571429) | 0/2 (0) |
| gamma_root_5769keV_rep01 | 10 | 9/512 (0.0175781) | 5/266 (0.018797) | 5/266 (0.018797) | 2/35 (0.0571429) | 0/2 (0) |
| gamma_root_5769keV_rep01 | 20 | 9/512 (0.0175781) | 5/266 (0.018797) | 5/266 (0.018797) | 2/35 (0.0571429) | 0/2 (0) |
| gamma_root_5769keV_rep01 | 50 | 9/512 (0.0175781) | 5/266 (0.018797) | 5/266 (0.018797) | 2/35 (0.0571429) | 0/2 (0) |
| gamma_root_5769keV_rep01 | 80 | 9/512 (0.0175781) | 5/266 (0.018797) | 5/266 (0.018797) | 2/42 (0.047619) | 0/2 (0) |
| gamma_root_5769keV_rep02 | 1 | 6/512 (0.0117188) | 3/247 (0.0121457) | 3/247 (0.0121457) | 2/40 (0.05) | 0/0 (undefined) |
| gamma_root_5769keV_rep02 | 5 | 6/512 (0.0117188) | 3/247 (0.0121457) | 3/247 (0.0121457) | 2/40 (0.05) | 0/0 (undefined) |
| gamma_root_5769keV_rep02 | 10 | 6/512 (0.0117188) | 3/247 (0.0121457) | 3/247 (0.0121457) | 2/40 (0.05) | 0/0 (undefined) |
| gamma_root_5769keV_rep02 | 20 | 6/512 (0.0117188) | 3/247 (0.0121457) | 3/247 (0.0121457) | 2/40 (0.05) | 0/0 (undefined) |
| gamma_root_5769keV_rep02 | 50 | 6/512 (0.0117188) | 3/247 (0.0121457) | 3/247 (0.0121457) | 2/40 (0.05) | 0/0 (undefined) |
| gamma_root_5769keV_rep02 | 80 | 5/512 (0.00976562) | 2/247 (0.00809717) | 2/247 (0.00809717) | 1/41 (0.0243902) | 0/0 (undefined) |
| gamma_root_5769keV_rep03 | 1 | 5/512 (0.00976562) | 4/246 (0.0162602) | 4/246 (0.0162602) | 1/38 (0.0263158) | 0/0 (undefined) |
| gamma_root_5769keV_rep03 | 5 | 5/512 (0.00976562) | 4/246 (0.0162602) | 4/246 (0.0162602) | 1/39 (0.025641) | 0/0 (undefined) |
| gamma_root_5769keV_rep03 | 10 | 5/512 (0.00976562) | 4/246 (0.0162602) | 4/246 (0.0162602) | 1/39 (0.025641) | 0/0 (undefined) |
| gamma_root_5769keV_rep03 | 20 | 5/512 (0.00976562) | 4/246 (0.0162602) | 4/246 (0.0162602) | 2/41 (0.0487805) | 0/0 (undefined) |
| gamma_root_5769keV_rep03 | 50 | 5/512 (0.00976562) | 4/246 (0.0162602) | 4/246 (0.0162602) | 2/43 (0.0465116) | 0/0 (undefined) |
| gamma_root_5769keV_rep03 | 80 | 5/512 (0.00976562) | 4/246 (0.0162602) | 4/246 (0.0162602) | 2/44 (0.0454545) | 0/0 (undefined) |

## Claim boundary

First-pass geometry/load and event-record smoke only; no physical rate, activation, delayed, response, sensitivity, or geometry-promotion conclusion.

The raw W2 count uses unbroadened TES CC HIT energy only. No pixel threshold, energy response, topology, active-veto timing, accidental coincidence, activation, or delayed-background model is applied here.
