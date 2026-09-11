# Mass_model_511 Staged-Diameter Final Review

This is the final review for the generated heavy DR draft with cold-plate diameters, ordered from 50mK to 300K:

`300, 300, 300, 350, 350, 400 mm`

## Outputs

- Geometry: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy`
- MEGAlib setup: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- WRL: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400.wrl`
- FreeCAD OBJ: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_freecad_mm.obj`
- FreeCAD MTL: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_freecad_mm.mtl`
- 2D full panorama schematic: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_2d_schematic.png`
- Manifest: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_manifest.json`
- Mass audit: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/MASS_MODEL_511_STAGE_DIAM_300_300_300_350_350_400_MASS_AUDIT.md`
- Overlap log: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_overlap.log`

## Cold Plates

| Stage | Material | Diameter mm | Radius cm | Thickness cm | Volume cm3 | Mass kg |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 50mK | Copper | 300 | 15.0 | 0.6 | 424.115 | 3.800 |
| 100mK | Copper | 300 | 15.0 | 0.6 | 424.115 | 3.800 |
| Still | Copper | 300 | 15.0 | 0.6 | 424.115 | 3.800 |
| 4K | Copper | 350 | 17.5 | 0.6 | 577.268 | 5.172 |
| 60K | Aluminium | 350 | 17.5 | 0.6 | 577.268 | 1.559 |
| 300K | Aluminium | 400 | 20.0 | 0.6 | 753.982 | 2.036 |

Cold-plate and 300K lid total: `20.166904 kg`.

## Mass Summary

- Heavy total including CsI: `180.509 kg`
- Heavy total without CsI: `101.756 kg`
- Baseline without CsI: `53.161 kg`
- Heavy minus baseline without CsI: `+48.594 kg`

Major heavy categories:

| Category | Heavy kg |
| --- | ---: |
| DR cold plates and 300K lid | 20.167 |
| DR thermal/vacuum shells | 24.137 |
| External detector-bay non-CsI support | 17.745 |
| NF2 nearfield outer mechanical support | 18.130 |
| XS400 group1-4 proxies | 18.044 |
| Active CsI scintillator | 78.753 |

## Geometry Notes

- The internal DR shell radii were expanded to clear the staged cold plates while preserving shell wall thicknesses.
- The external CsI, Kapton active shield, and aluminium detector-bay radial envelopes were expanded to clear the 400 mm 300K lid.
- `DR_Still_PumpLine_SS_to_300K_top` was moved to `x=21.4 cm` to avoid the enlarged 4K/60K cold plates.
- `W_Multihole_CollimatorVac` was moved to `x=-25.9 cm` to follow the resized detector-bay side-window envelope; W grid dimensions and child placement remain unchanged.
- The previous single Still-4K group1 member is now split into four symmetric equal-volume stainless-steel rods. Total Still-4K support volume remains `142.151 cm3`, mass remains `1.137 kg`.
- The previous copied top feedthrough block was replaced with an XS400-like pipe bank above the 300K lid: 12 stainless-steel pipe centers represented by 36 hollow-pipe/flange/sleeve solids. The pipe bodies and top sleeves are now 2x radius; base flanges are unchanged. Added volume is `197.300 cm3`, added mass is `1.578 kg`.
- The NF2 detector-nearfield mechanical support overlay is imported as an `InstrumentFrame` child cage: bottom Al mount annulus, top Al mount annulus, six G10 perimeter rods, and twelve stainless-steel hardpoints. Each support solid uses inverse-transformed local position plus `Rotation 0 -45 0`, so its exported/world-space support axis remains vertical while avoiding `WorldVolume` sibling overlap with the large tilted `InstrumentFrame` vacuum container. Relative to the previous local support version, the rod count was changed from 4 to 6, ring radial width was doubled (`1.20 -> 2.40` scale), and G10 rod half-width was doubled (`1.25 -> 2.50` scale). Added volume is `7393.806 cm3`, added mass is `18.130 kg` (`13.672 kg` Al, `4.267 kg` G10, `0.192 kg` stainless steel).

## Validation

- Python syntax check passed for `code/tools/build_Mass_model_511_geometry.py`, `code/tools/audit_Mass_model_511_mass.py`, and `code/tools/export_wrl_to_freecad_obj.py`.
- NF2 outer support axis check passed:
  - All `20` NF2 outer support solids have `InstrumentFrame` as mother.
  - All `20` support solids have `Rotation 0 -45 0`; inverse-transform recovery of their intended world positions is better than `1e-6 cm`.
  - The exported/world-space support z axis and tilted refrigerator z axis have angle `45.0 deg`.
  - Static clearance estimate gives bottom/top annulus inner-radius margins of `15.770 cm` and `14.977 cm` relative to the largest cold plate, and `9.470 cm` and `8.677 cm` relative to the largest external detector-bay envelope. G10 rod XY box margins are `20.225 cm` relative to the largest cold plate.
- Sensitive geometry diff passed:
  - TES, Si substrate, copper support/cold-finger, and MXC clamp Shape/Position lines match the source geometry.
  - W multihole collimator solid dimensions and child lattice Shape/Position lines match the source geometry, excluding the intentional mother-volume x shift.
  - Window Shape lines match the source geometry.
- MEGAlib `cosima` overlap check passed after the support-parent repair; see the post-review below.

## Post-Review: Overlap, Window Axis, And Shield Closure

Review date: `2026-07-01`.

- MEGAlib `cosima` with `CheckForOverlaps 10000 0.0001` is clean after the support-parent repair. The run completed with `cosima_status=0`, reached Stage 12 / volume-tree optimization, stored the single minimum event, and the saved log has no `GeomVol`, `Overlap is detected`, `overlapping by`, `G4Exception`, `Error`, or `Exception` matches. Log: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_overlap_after_support_parent_fix.log`.
- Side-window axis check passed. All side-window foils are aligned on `y=0, z=-5.2 cm`; the rectangular cuts keep `1.898 cm` half size in both y and z and extend from the resized outer radius to the centerline. The W multihole collimator has `624` W bar copies and none intersects the central window axis; the nearest W-bar clearance to the central hole is `0.071 cm`.
- Window-exterior side-wall closure check passed for the represented side layers. The Cu/Al cryostat side-wall pieces, CsI side active-veto segments, Kapton active-shield side layer, and outer Al detector-bay shell have zero axial gaps between below-window, rectcut-window-band, and above-window pieces. The only modeled opening is the intended `3.796 cm x 3.796 cm` side-window aperture.
- Passive side-wall caveat: the generated geometry contains `Passive_W_Bottom_Plate_detector_bay`, but no full W/Pb passive side-wall liner. If a W/Pb side passive shield is required outside the window, it is not currently present.
