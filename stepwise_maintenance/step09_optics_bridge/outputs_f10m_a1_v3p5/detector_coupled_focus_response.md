# Step09 Detector-Coupled Focus Response

Status: `PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST`.

This report parses the full non-smoke Step09 focused EventList Cosima output and normalizes it with the Step04 B-FULL A_eff(511) authority. The science source is the focused EventList, not a homogeneous Be-window beam.

## Optics Authority

- design: `balloon511_f10m_ge111_511line_a1`
- focal length: `10000` mm
- A_eff(511): `20.0848` cm2
- target residual: `0.004238` against the 16 cm2 design target
- W1: `500.994-521.006` keV
- W2: `510.58-511.42` keV

## Detector Response

- focused source triggers parsed: `37194`
- focused TES events kept: `35707`
- W1 after both: signal `0.00106592` cps at 1e-4, background `0.0878776` cps, Z20d `4.72668`
- W2 after both: signal `0.00106232` cps at 1e-4, background `0.0730017` cps, Z20d `5.16844`

## Spatial Cut

- detector-coupled focused W2 r90: `1.05164` cm
- headline cut: `spot_r90`, signal fraction `0.900004`, background `0.023251` cps, Z20d `8.24231`
- best robust cut: `spot_r90` at `1.05164` cm, Z20d `8.24231`

## Outputs

- JSON: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_focus_response.json`
- windows: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_focus_windows.csv`
- W1/W2 veto table: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/non_xray_background_w1_w2_veto_table.csv`
- spatial cuts: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_spatial_line_cuts.csv`
- spectrum: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/non_xray_background_spectrum_480_550.csv`
- figures: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/figures`
