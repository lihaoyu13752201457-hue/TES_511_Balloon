# Step09 Detector-Coupled Focus Response

Status: `PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST`.

This report parses the full non-smoke Step09 focused EventList Cosima output and normalizes it with the Step04 B-FULL A_eff(511) authority. The science source is the focused EventList, not a homogeneous Be-window beam.

## Optics Authority

- design: `balloon511_f9m_ge111_511line`
- focal length: `9000` mm
- A_eff(511): `15.2993` cm2
- target residual: `0.043795` against the 16 cm2 design target
- W1: `500.994-521.006` keV
- W2: `510.58-511.42` keV

## Detector Response

- focused source triggers parsed: `11910`
- focused TES events kept: `11910`
- W1 after both: signal `9.009895e-04` cps at 1e-4, background `0.783047` cps, Z20d `1.33844`
- W2 after both: signal `8.982878e-04` cps at 1e-4, background `0.184347` cps, Z20d `2.75023`

## Spatial Cut

- detector-coupled focused W2 r90: `0.523692` cm
- headline cut: `spot_r90`, signal fraction `0.90001`, background `0.0551005` cps, Z20d `4.52748`
- best robust cut: `spot_r68` at `0.188229` cm, Z20d `5.94863`

## Outputs

- JSON: `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json`
- windows: `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_windows.csv`
- W1/W2 veto table: `stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv`
- spatial cuts: `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_spatial_line_cuts.csv`
- spectrum: `stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_spectrum_480_550.csv`
- figures: `stepwise_maintenance/step09_optics_bridge/outputs/figures`
