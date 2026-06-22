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
- focused TES events kept: `36586`
- W1 after both: signal `0.00106815` cps at 1e-4, background `0.0597796` cps, Z20d `5.74283`
- W2 after both: signal `0.00106462` cps at 1e-4, background `0.0569112` cps, Z20d `5.86634`

## Spatial Cut

- detector-coupled focused W2 r90: `1.05573` cm
- headline cut: `spot_r90`, signal fraction `0.900033`, background `0.0186698` cps, Z20d `9.21837`
- best robust cut: `spot_r90` at `1.05573` cm, Z20d `9.21837`

## Outputs

- JSON: `stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/detector_coupled_focus_response.json`
- windows: `stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/detector_coupled_focus_windows.csv`
- W1/W2 veto table: `stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/non_xray_background_w1_w2_veto_table.csv`
- spatial cuts: `stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/detector_coupled_spatial_line_cuts.csv`
- spectrum: `stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/non_xray_background_spectrum_480_550.csv`
- figures: `stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/figures`
