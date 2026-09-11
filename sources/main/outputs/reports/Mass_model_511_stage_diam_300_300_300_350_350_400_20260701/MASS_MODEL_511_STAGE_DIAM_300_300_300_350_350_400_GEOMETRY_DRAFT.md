# Mass_model_511 Staged-Diameter Geometry Draft

This report is a generation record for the derived heavy draft. It does not promote the geometry to project authority.

## Inputs and outputs

- Source: `outputs/geometry/DEMO2_DR_v3p5_xs400_shell_thickness_rework_20260630_megalib_proxy`
- Geometry output: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy`
- Manifest: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_manifest.json`
- 2D schematic: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_2d_schematic.png` and `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_2d_schematic.svg`
- WRL: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400.wrl`

## Applied transform

- Cold plate / 300K lid diameters from 50mK to 300K are `[300, 300, 300, 350, 350, 400]` mm; all are 6 mm thick.
- Cryostat shells use explicit target outer radii `{'50mK_Cu_can': 15.3, 'Still_Al_thermal_shield': 15.8, '4K_Al_thermal_shield': 18.0, '60K_Al_thermal_shield': 18.5, '266mmClass_vacuum_jacket': 20.6}` cm.
- External CsI/active-shield/outer-detector bay envelopes use explicit target outer radii `{'CsI_detector_bay_side': 25.2, 'CsI_detector_bay_top_annulus': 25.2, 'ActiveShield_Flex_Kapton_detector_bay': 25.4, 'Outer_Al_Mechanical_Shell_detector_bay': 26.3, 'Outer_Al_Mechanical_Shell_detector_bay_top_annulus': 26.3}` cm to clear the enlarged DR stack.
- Shell wall thicknesses are preserved by setting the outer radius and then subtracting the original wall thickness for the inner radius.
- Side-window cut boxes keep the same 3.796 cm by 3.796 cm aperture and are recomputed from the new shell outer radius, so the Boolean cut still reaches from outside the shell to the centerline.
- Foil/window half-sizes are unchanged. Their x positions are moved to the corresponding resized shell mid-wall, except the outer Al filter, which keeps its source offset outside the resized vacuum jacket.
- W multihole collimator dimensions are unchanged, but the collimator mother volume is shifted outward to the resized detector-bay window; detector/sample/cold-finger dimensions are unchanged.
- XS400 group-1 rods are refit to the 6 mm cold-plate surfaces with volume preserved; `Still_to_4K_single_edge` is split from one source member into four equal-volume rods.
- A new XS400-like top pipe bank is added above the 300K lid using hollow stainless-steel pipe proxies, base flanges, and top sleeves.
- NF2 nearfield outer support is imported from `add_mass/TES_511_Balloon_nearfield_mass_proxy_v2/detector/overlays/SupportProxy_DetectorNearfieldMechanical_v2.geo` as an InstrumentFrame child cage with inverse-transformed positions and a -45 degree counter-rotation; its exported/world-space support axis is vertical while the refrigerator axis remains the `InstrumentFrame.Rotation 0 45 0` axis, giving a 45 degree axis angle. Added support mass is `18.130 kg`.
- Group2 upper proxy placement plus the still pump line and SQUID/uMUX readout service proxy are adjusted for clearance; TES detector, cold-finger, window, and collimator dimensions remain unchanged.

## Shell radius table

| family | volume | old rin-rout cm | new rin-rout cm | wall cm |
| --- | --- | ---: | ---: | ---: |
| 50mK_Cu_can | `Cu_50mK_StillLike_Can_side_wall_below_side_port` | 7.45-7.65 | 15.1-15.3 | 0.2 |
| 50mK_Cu_can | `Cu_50mK_StillLike_Can_side_wall_above_side_port` | 7.45-7.65 | 15.1-15.3 | 0.2 |
| 50mK_Cu_can | `Cu_50mK_StillLike_Can_side_wall_rectcut_window_band` | 7.45-7.65 | 15.1-15.3 | 0.2 |
| Still_Al_thermal_shield | `Still_Shield_Al_side_window_side_wall_below_side_port` | 8.5-8.8 | 15.5-15.8 | 0.3 |
| Still_Al_thermal_shield | `Still_Shield_Al_side_window_side_wall_above_side_port` | 8.5-8.8 | 15.5-15.8 | 0.3 |
| Still_Al_thermal_shield | `Still_Shield_Al_side_window_side_wall_rectcut_window_band` | 8.5-8.8 | 15.5-15.8 | 0.3 |
| 4K_Al_thermal_shield | `Shield_4K_Al_side_window_side_wall_below_side_port` | 9.9-10.2 | 17.7-18 | 0.3 |
| 4K_Al_thermal_shield | `Shield_4K_Al_side_window_side_wall_above_side_port` | 9.9-10.2 | 17.7-18 | 0.3 |
| 4K_Al_thermal_shield | `Shield_4K_Al_side_window_side_wall_rectcut_window_band` | 9.9-10.2 | 17.7-18 | 0.3 |
| 60K_Al_thermal_shield | `Shield_60K_Al_side_window_side_wall_below_side_port` | 11.4-11.7 | 18.2-18.5 | 0.3 |
| 60K_Al_thermal_shield | `Shield_60K_Al_side_window_side_wall_above_side_port` | 11.4-11.7 | 18.2-18.5 | 0.3 |
| 60K_Al_thermal_shield | `Shield_60K_Al_side_window_side_wall_rectcut_window_band` | 11.4-11.7 | 18.2-18.5 | 0.3 |
| 266mmClass_vacuum_jacket | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_below_side_port` | 12.9-13.4 | 20.1-20.6 | 0.5 |
| 266mmClass_vacuum_jacket | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | 12.9-13.4 | 20.1-20.6 | 0.5 |
| 266mmClass_vacuum_jacket | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_rectcut_window_band` | 12.9-13.4 | 20.1-20.6 | 0.5 |

## External detector-bay radial envelope table

| family | representative volume | old rin-rout cm | new rin-rout cm | wall cm |
| --- | --- | ---: | ---: | ---: |
| CsI_detector_bay_side | `CsI_Side_Segment_00` | 14-18 | 21.2-25.2 | 4 |
| CsI_detector_bay_top_annulus | `CsI_TopAnnulus_Segment_00` | 13.6-18 | 20.8-25.2 | 4.4 |
| ActiveShield_Flex_Kapton_detector_bay | `ActiveShield_Flex_Kapton_detector_bay_below_side_port` | 18.17-18.2 | 25.37-25.4 | 0.03 |
| Outer_Al_Mechanical_Shell_detector_bay | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` | 18.3-19.1 | 25.5-26.3 | 0.8 |
| Outer_Al_Mechanical_Shell_detector_bay_top_annulus | `Outer_Al_Mechanical_Shell_detector_bay_top_annulus` | 13.7-19.1 | 20.9-26.3 | 5.4 |

## NF2 outer support proxy

- Solids: `20`
- Volume: `7393.806 cm3`
- Mass: `18.130 kg`
- Contents: bottom Al mount annulus, top Al mount annulus, 6 G10 perimeter rods, and 12 stainless-steel hardpoints.
- Axis policy: support solids are `InstrumentFrame` children with `Rotation 0 -45 0`; exported/world-space support axis remains vertical, 45 degrees from the tilted refrigerator axis.

## Validation status

- Script-level checks verified that all requested source files exist, all targeted Shape/Position lines were found, shell inner radii remain positive, and the generated sidecars were written.
- Run MEGAlib `cosima` with the generated `overlap_check.source` and inspect the saved log for `GeomVol` warnings before production simulation.
