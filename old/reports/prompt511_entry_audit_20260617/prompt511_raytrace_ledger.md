# Prompt 511 Geometry Ray-Trace Ledger

This is a straight-line geometry diagnostic through the MEGAlib proxy `.geo`
files. It traces selected prompt-eplus annihilation-to-TES proxy lines and a
fixed side-axis line through old/current geometry. It does not model scattering,
attenuation, or Geant4 step history. For each line segment it uses the deepest
placed volume containing that segment, so mother/child volume overlaps are not
double-counted.

## Main Result

The fixed side-axis blocker test is the cleanest result. In the current
geometry, the intended side-window segment has only
`Be:0.015; Aluminium:0.013` before the detector region. Along the
corresponding old-geometry outer-to-inner side line, the path has
`CsI:4; Copper:1.63; LowCarbonSteel:1.17; Aluminium:1.1; StainlessSteel:0.25; G10:0.16; W:0.06; Kapton:0.05`. In other words, old `new_geo_re` puts a real
side-shield material column in the region where the current geometry has a thin
window/side-port path.

For all current selected final prompt-eplus events, the median non-Ta material
chord between annihilation and TES is `3.865`
cm. In the current non-window subset, it is
`4.412` cm. Those survivor
lines are typically born in the side-wall/side-port neighborhood after the
outer blocker has already been bypassed; they are not entering through the
nominal Be/Al window disc.

Old selected final prompt-eplus events have a median non-Ta material chord of
`6.456` cm after leaf-volume tracing, but
those events are an old-geometry axial/top population. They are not used as the
direct side-port counterpart.

## Fixed Side-Axis Lines

| line | material chord summary | top volume chords |
|---|---|---|
| `current_side_axis_centerline` | Ta/TES:1.8; Copper:0.35; Silicon:0.18; Be:0.015; Aluminium:0.013 | Cu_SubstrateSupport_SolidDisk_L0_deepest:0.35; TP_L0_00188:0.3; TP_L4_00188:0.3; TP_L5_00188:0.3; TP_L1_00188:0.3; TP_L2_00188:0.3; TP_L3_00188:0.3; Si_Substrate_Stack_side_entry_L2:0.03; Si_Substrate_Stack_side_entry_L3:0.03; Si_Substrate_Stack_side_entry_L4:0.03; Si_Substrate_Stack_side_entry_L5:0.03; Si_Substrate_Stack_side_entry_L0:0.03 |
| `old_same_side_axis_centerline` | SaltProxy:4.6; CsI:4; Copper:3.5; LowCarbonSteel:1.69; Aluminium:1.22; StainlessSteel:0.5; G10:0.16; W:0.06; Kapton:0.05 | ADR_SaltPill_Proxy:4.6; CsI_Active_Shield_Side04:4; ADR_Magnet_Coil_Cu:3.1; ADR_Magnet_Yoke_Fe:1.69; ADR_HeatSwitch_Stainless_Link:0.5; Vacuum_Jacket_Al:0.4; ADR_SaltPill_Cu_Can:0.32; Thermal_4K_Al_Shield:0.24; Outer_Al_Mech_Shell:0.2; Support_G10_Post_B:0.16; Thermal_60K_Al_Shield:0.15; Vacuum_Jacket_Al_Reinforcement:0.12 |
| `current_side_axis_window_only` | Be:0.015; Aluminium:0.013 | Win_Be_Vacuum_150um_side:0.015; Win_Outer_Al_Filter_side:0.003; Win_Still_Al_foil_side:0.0025; Win_60K_Al_foil_side:0.0025; Win_50mK_Al_foil_side:0.0025; Win_4K_Al_foil_side:0.0025 |
| `old_corresponding_outer_to_inner` | CsI:4; Copper:1.63; LowCarbonSteel:1.17; Aluminium:1.1; StainlessSteel:0.25; G10:0.16; W:0.06; Kapton:0.05 | CsI_Active_Shield_Side04:4; ADR_Magnet_Coil_Cu:1.55; ADR_Magnet_Yoke_Fe:1.17; Vacuum_Jacket_Al:0.4; ADR_HeatSwitch_Stainless_Link:0.25; Outer_Al_Mech_Shell:0.2; Support_G10_Post_B:0.16; Thermal_60K_Al_Shield:0.15; Vacuum_Jacket_Al_Reinforcement:0.12; Thermal_4K_Al_Shield:0.12; ActiveShield_Al_Backplane_Liner:0.11; Passive_Cu_Inner_Liner:0.08 |

## Current Non-Window Selected Event Examples

| source:id | first/last primary volume | ray materials | passive before TES cm | top chord volumes |
|---|---|---|---:|---|
| `rep01_part01:51708` | `Passive_W_Liner_detector_bay_above_side_port -> Passive_Cu_Liner_detector_bay_above_side_port` | Aluminium:0.879; Ta/TES:0.165; Copper:0.0913 | 0.971 | Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:0.457; Shield_60K_Al_side_window_side_wall_above_side_port:0.171; TP_L0_00302:0.165; Shield_4K_Al_side_window_side_wall_above_side_port:0.137; Still_Shield_Al_side_window_side_wall_above_side_port:0.114; Passive_Cu_Liner_detector_bay_above_side_port:0.0913 |
| `rep01_part01:84231` | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Copper:1.11; Aluminium:1.03; Ta/TES:0.339; Silicon:0.0445 | 2.18 | ColdPlate_MXC_50mK_SD_anchor:0.902; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:0.535; Cu_SubstrateSupport_OpenRing_L4_ZP_panel:0.205; Shield_60K_Al_side_window_side_wall_above_side_port:0.201; TP_L2_00129:0.196; Shield_4K_Al_side_window_side_wall_above_side_port:0.161 |
| `rep01_part01:104848` | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` | CsI:4.01; Aluminium:1.26; Copper:0.242; Cryoperm:0.132; W:0.0702; Nb:0.0551; Kapton:0.0301 | 5.8 | CsI_Side_Segment_05:4.01; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_below_side_port:0.401; Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port:0.3; Cu_SubstrateSupport_OpenRing_L3_YM_panel:0.162; Shield_60K_Al_side_window_side_wall_below_side_port:0.15; Cryoperm_Horizontal_Sleeve_1p2mm_YM_panel:0.132 |
| `rep01_part01:113651` | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Copper:2.43; Aluminium:1.89; Ta/TES:0.495; Silicon:0.101 | 4.42 | Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:1.25; ColdPlate_4K:0.634; ColdPlate_Still_0p7K:0.634; ColdPlate_MXC_50mK_SD_anchor:0.634; ColdPlate_CP_100mK_intercept:0.528; Shield_60K_Al_side_window_side_wall_above_side_port:0.472 |
| `rep01_part01:118057` | `Outer_Al_Mechanical_Shell_detector_bay_top_annulus` | Aluminium:1.47; CsI:1.01; Copper:0.524; Ta/TES:0.351 | 3.01 | CsI_TopAnnulus_Segment_04:1.01; Outer_Al_Mechanical_Shell_detector_bay_top_annulus:0.518; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:0.493; ColdPlate_MXC_50mK_SD_anchor:0.458; TP_L1_00338:0.2; Shield_60K_Al_side_window_side_wall_above_side_port:0.185 |
| `rep01_part01:121643` | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_01` | CsI:4.03; Aluminium:1.26; Ta/TES:0.722; Cryoperm:0.127; Silicon:0.0967; Copper:0.0805; W:0.0705 | 5.75 | CsI_Side_Segment_06:4.03; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_side_port_band_01:0.403; Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_01:0.301; TP_L3_00253:0.159; TP_L3_00232:0.159; TP_L3_00274:0.159 |
| `rep01_part01:144428` | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` | CsI:4.48; Aluminium:1.39; Ta/TES:0.197; Cryoperm:0.151; Copper:0.0969; W:0.0848; Nb:0.0628 | 6.26 | CsI_Bottom_Quadrant_02:3.74; CsI_Side_Segment_05:0.738; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_below_side_port:0.485; Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port:0.357; TP_L1_00001:0.186; Shield_60K_Al_side_window_side_wall_below_side_port:0.182 |
| `rep01_part01:169432` | `Outer_Al_Mechanical_Shell_detector_bay_top_annulus -> Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Aluminium:1.21; Copper:0.788; Ta/TES:0.132; Silicon:0.0492 | 2.04 | ColdPlate_MXC_50mK_SD_anchor:0.788; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:0.624; Shield_60K_Al_side_window_side_wall_above_side_port:0.235; Shield_4K_Al_side_window_side_wall_above_side_port:0.189; Still_Shield_Al_side_window_side_wall_above_side_port:0.159; TP_L4_00366:0.132 |
| `rep01_part01:181723` | `Outer_Al_Mechanical_Shell_detector_bay_top_annulus` | Aluminium:1.5; Copper:1.21; CsI:1.14; Ta/TES:0.439; Silicon:0.0798 | 3.93 | ColdPlate_MXC_50mK_SD_anchor:1.21; CsI_TopAnnulus_Segment_00:1.14; Outer_Al_Mechanical_Shell_detector_bay_top_annulus:0.602; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:0.466; TP_L0_00256:0.186; Shield_60K_Al_side_window_side_wall_above_side_port:0.175 |
| `rep01_part01:184929` | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_01` | CsI:4.02; Aluminium:1.28; Ta/TES:0.506; Cryoperm:0.163; Copper:0.0804; W:0.0703; Nb:0.0681 | 5.76 | CsI_Side_Segment_04_side_port_band_00:4.02; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_side_port_band_01:0.402; Outer_Al_Mechanical_Shell_detector_bay_side_wall_side_port_band_01:0.301; TP_L1_00077:0.204; Cryoperm_Horizontal_Sleeve_1p2mm_YM_panel:0.163; Shield_60K_Al_side_window_side_wall_side_port_band_01:0.151 |
| `rep01_part01:214319` | `Outer_Al_Mechanical_Shell_detector_bay_top_annulus` | Aluminium:1.46; Copper:1.08; CsI:0.513; Ta/TES:0.291; Silicon:0.0427 | 3.09 | ColdPlate_MXC_50mK_SD_anchor:1.08; Outer_Al_Mechanical_Shell_detector_bay_top_annulus:0.53; CsI_TopAnnulus_Segment_00:0.513; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:0.482; Shield_60K_Al_side_window_side_wall_above_side_port:0.181; TP_L3_00282:0.172 |
| `rep02_part01:36481` | `-` | CsI:4.22; Aluminium:1.23; Ta/TES:0.458; Copper:0.0843; W:0.0738; Silicon:0.0343; Kapton:0.0316 | 5.68 | CsI_Side_Segment_03_above_side_port:4.22; Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port:0.422; Outer_Al_Mechanical_Shell_detector_bay_side_wall_above_side_port:0.316; TP_L0_00362:0.161; Shield_60K_Al_side_window_side_wall_above_side_port:0.158; TP_L1_00312:0.132 |

## Files

- Event chord CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_event_chords.csv`
- Volume segment CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_volume_segments.csv`
- Fixed-line CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_line_chords.csv`
- Summary JSON: `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_summary.json`

## Boundaries

- Volumes are parsed from `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo` and `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo`.
- `BRIK` boxes and the constant-radius/plane boundaries of the local `PCON`
  shapes are traced as straight-line chord intervals in the no-rotation proxy
  geometry. The decisive fixed side-axis lines are constant-z radial lines.
- This is a chord-length audit, not a photon transport or attenuation
  calculation. The SIM interaction ledger remains the transport evidence; this
  ray trace explains the geometry along the proxy lines.
