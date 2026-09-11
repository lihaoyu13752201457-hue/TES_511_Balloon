# Mass_model_511 Staged-Diameter Mass Audit

This audit is computed from the generated MEGAlib proxy solids. It is not a vendor BOM.

- Base geometry: `outputs/geometry/DEMO2_DR_v3p5_xs400_shell_thickness_rework_20260630_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- Heavy geometry: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- JSON: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_mass_audit.json`
- CSV: `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_mass_by_category.csv`

## Totals

- Base total including CsI: `115.836 kg`
- Heavy total including CsI: `180.509 kg`
- Base without CsI: `53.161 kg`
- Heavy without CsI: `101.756 kg`
- Heavy minus base, without CsI: `+48.594 kg`

## Category Breakdown

| Category | Base kg | Heavy kg | Delta kg |
| --- | ---: | ---: | ---: |
| `active_csi_scintillator` | 62.675 | 78.753 | +16.078 |
| `dr_cold_plates_and_300k_lid` | 7.475 | 20.167 | +12.692 |
| `dr_thermal_vacuum_shells` | 13.252 | 24.137 | +10.885 |
| `external_detector_bay_non_csi` | 12.437 | 17.745 | +5.309 |
| `magnetic_shields` | 0.928 | 0.928 | +0.000 |
| `nearfield_outer_mechanical_support` | 0.000 | 18.130 | +18.130 |
| `other_dr_service_or_proxy` | 2.410 | 2.410 | +0.000 |
| `side_windows_and_foils` | 0.001 | 0.001 | +0.000 |
| `tes_payload_and_thermal_link` | 0.158 | 0.158 | +0.000 |
| `w_collimator` | 0.035 | 0.035 | +0.000 |
| `xs400_group1_interplate_supports` | 4.419 | 4.419 | -0.000 |
| `xs400_group2_contact_stack` | 9.640 | 9.640 | +0.000 |
| `xs400_group3_aux_service` | 1.607 | 1.607 | +0.000 |
| `xs400_group4_upper_port_fittings` | 0.799 | 2.378 | +1.578 |

## XS400 CAD Group Reference

- Source CAD group1-4 mass estimate: `50.763 kg`
- Project-scaled group1-4 proxy mass in yesterday geometry: `16.465 kg`

The remaining gap to the full XS400 CAD estimate comes mostly from large outer shells/flanges and unproxied service/room-temperature hardware.
