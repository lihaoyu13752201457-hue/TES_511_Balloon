# Prompt 511 Material Ledger

This is a diagnostic companion to `prompt511_entry_audit.md`.

## Scope And Caveat

The SIM files record IA interaction points and CC hit volumes. They do not store a full material-boundary step history. Therefore the "path cm" below is the straight-line distance from one post-annihilation IA point to the next, grouped by the downstream interaction material inferred from the nearest CC hit within `0.35` cm. This is useful for seeing where 511 branches interact or terminate, but it is not an exact chord-length integral through every passive boundary.

The selected-event sample is the same round-robin low-ID sample used by the interaction-track figure: up to `32` final W2 selected prompt-eplus events per geometry. The side/shield blocked sample uses up to `100` no-TES side-region events per geometry.

## Group Summary

| group | events | TES hits | stop materials | median path cm | median shield edep keV |
|---|---:|---:|---|---:|---:|
| old selected | 32 | 32 | {'Ta/TES': 32} | 33.2 | 10.3 |
| current selected | 32 | 32 | {'Ta/TES': 32} | 47.8 | 56.6 |
| old shielded sample | 100 | 0 | {'CsI': 67, 'Aluminium': 22, 'W': 4, 'other': 5, 'Copper': 2} | 9.27 | 523 |
| current shielded sample | 100 | 0 | {'CsI': 49, 'Aluminium': 37, 'W': 6, 'other': 8} | 8.25 | 517 |

## Representative Event Ledger

| group | source:id | leak class | primary / key volume | path endpoint material cm | CC edep keV | stop |
|---|---|---|---|---|---|---|
| current_selected | `rep01_part01:51708` | non window no window disk intersection | `Passive_W_Liner_detector_bay_above_side_port -> Passive_Cu_Liner_detector_bay_above_side_port` | Ta/TES:47.7 | Ta/TES:511; Copper:24.5; W:0.818 | TES hit / Ta/TES / `TP_L0_00281` |
| current_selected | `rep01_part01:84231` | non window no window disk intersection | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Ta/TES:18.4 | Ta/TES:511; Aluminium:83.8 | TES hit / Ta/TES / `TP_L2_00149` |
| current_selected | `rep01_part01:104848` | non window no window disk intersection | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` | Ta/TES:39.4 | Ta/TES:511; Aluminium:31.7 | TES hit / Ta/TES / `TP_L3_00156` |
| current_selected | `rep01_part01:113651` | non window no window disk intersection | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Ta/TES:112 | Ta/TES:511; Aluminium:12.3 | TES hit / Ta/TES / `TP_L4_00328` |
| current_selected | `rep02_part01:36481` | non window no window disk intersection | `TP_L1_00292` | Ta/TES:52.6 | Ta/TES:511 | TES hit / Ta/TES / `TP_L1_00292` |
| current_selected | `rep02_part01:38093` | non window no window disk intersection | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Ta/TES:74.5 | Ta/TES:511; Aluminium:35.7 | TES hit / Ta/TES / `TP_L1_00266` |
| current_selected | `rep02_part01:43996` | non window no window disk intersection | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` | Ta/TES:64.4 | Ta/TES:511; Aluminium:91.8 | TES hit / Ta/TES / `TP_L0_00340` |
| current_selected | `rep02_part01:48330` | non window no window disk intersection | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_above_side_port` | Ta/TES:50.9 | Ta/TES:511; Aluminium:81 | TES hit / Ta/TES / `TP_L1_00025` |
| current_selected | `rep03_part01:12294` | non window no window disk intersection | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Ta/TES:137 | Ta/TES:511; Aluminium:1.37 | TES hit / Ta/TES / `TP_L2_00206` |
| current_selected | `rep03_part01:57164` | non window no window disk intersection | `TP_L4_00160` | Ta/TES:289 | Ta/TES:511 | TES hit / Ta/TES / `TP_L4_00160` |
| current_selected | `rep03_part01:114158` | non window no window disk intersection | `Outer_Al_Mechanical_Shell_detector_bay_top_annulus` | Ta/TES:15.9 | Ta/TES:511; Aluminium:288 | TES hit / Ta/TES / `TP_L1_00022` |
| current_selected | `rep04_part01:68149` | non window no window disk intersection | `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` | Ta/TES:59.2 | Ta/TES:511; Aluminium:55.6 | TES hit / Ta/TES / `TP_L3_00190` |
| current_shielded | `rep01_part01:38` | - | `CsI_TopAnnulus_Segment_02` | CsI:41.9; Aluminium:4.16 | CsI:511; Aluminium:147 | absorbed before TES / CsI / `CsI_TopAnnulus_Segment_02` |
| current_shielded | `rep01_part01:45` | - | `CsI_TopAnnulus_Segment_00` | CsI:41.3 | CsI:511; Aluminium:21.3 | absorbed before TES / CsI / `CsI_TopAnnulus_Segment_00` |
| current_shielded | `rep01_part01:54` | - | `CsI_Side_Segment_05` | CsI:24.1 | CsI:511; Aluminium:31.5 | absorbed before TES / CsI / `CsI_Side_Segment_05` |
| current_shielded | `rep01_part01:70` | - | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_above_side_port` | Aluminium:0.555 | Aluminium:256 | scattered/no TES / Aluminium / `Outer_Al_Mechanical_Shell_detector_bay_side_wall_above_side_port` |
| current_shielded | `rep01_part01:72` | - | `CsI_Side_Segment_00` | CsI:6.11; Aluminium:0.213 | Aluminium:323; CsI:293 | absorbed before TES / CsI / `CsI_Side_Segment_00` |
| current_shielded | `rep01_part01:106` | - | `CsI_Side_Segment_01` | CsI:17.6 | CsI:511; Aluminium:32.7 | absorbed before TES / CsI / `CsI_Side_Segment_01` |
| current_shielded | `rep01_part01:115` | - | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` | - | Aluminium:69 | no TES / Aluminium / `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` |
| current_shielded | `rep01_part01:116` | - | `ActiveShield_Al_Backplane_detector_bay_side_port_band_01` | Aluminium:3.4 | Aluminium:759 | absorbed before TES / Aluminium / `ActiveShield_Al_Backplane_detector_bay_side_port_band_01` |
| current_shielded | `rep01_part01:123` | - | `CsI_Side_Segment_00` | CsI:25 | CsI:511; Aluminium:432 | absorbed before TES / CsI / `CsI_Side_Segment_00` |
| current_shielded | `rep01_part01:149` | - | `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` | Aluminium:0.452 | Aluminium:275 | scattered/no TES / Aluminium / `Outer_Al_Mechanical_Shell_detector_bay_side_wall_below_side_port` |
| current_shielded | `rep01_part01:158` | - | `CsI_Side_Segment_02` | CsI:7.79 | CsI:511; Aluminium:5.78 | absorbed before TES / CsI / `CsI_Side_Segment_02` |
| current_shielded | `rep01_part01:159` | - | `CsI_Bottom_Quadrant_03` | CsI:36.9 | CsI:511; Aluminium:11.8 | absorbed before TES / CsI / `CsI_Bottom_Quadrant_03` |
| old_shielded | `rep01_part01:12` | - | `CsI_Active_Shield_Side00` | CsI:10.7 | CsI:511; Aluminium:9.07 | absorbed before TES / CsI / `CsI_Active_Shield_Side00` |
| old_shielded | `rep01_part01:23` | - | `CsI_Active_Shield_Side00` | CsI:4.53 | CsI:511; Aluminium:2.16 | absorbed before TES / CsI / `CsI_Active_Shield_Side00` |
| old_shielded | `rep01_part01:36` | - | `Outer_Al_Mech_Shell` | - | Aluminium:34.9 | no TES / Aluminium / `Outer_Al_Mech_Shell` |
| old_shielded | `rep01_part01:39` | - | `Outer_Al_Mech_Shell` | Aluminium:1.64 | Aluminium:222 | scattered/no TES / Aluminium / `Outer_Al_Mech_Shell` |
| old_shielded | `rep01_part01:48` | - | `CsI_Active_Shield_Side07` | CsI:2.91 | CsI:151; Aluminium:43.1 | scattered/no TES / CsI / `CsI_Active_Shield_Side07` |
| old_shielded | `rep01_part01:52` | - | `ActiveShield_Al_Backplane_Liner` | Kapton:6.67; Aluminium:4.86 | Aluminium:191; Kapton:131 | absorbed before TES / Aluminium / `ActiveShield_Al_Backplane_Liner` |
| old_shielded | `rep01_part01:59` | - | `CsI_Active_Shield_Side03` | CsI:9.6 | CsI:511; Aluminium:14.7 | absorbed before TES / CsI / `CsI_Active_Shield_Side03` |
| old_shielded | `rep01_part01:69` | - | `CsI_Active_Shield_Side04` | CsI:9.33 | CsI:511; Aluminium:13.4 | absorbed before TES / CsI / `CsI_Active_Shield_Side04` |
| old_shielded | `rep01_part01:94` | - | `CsI_Active_Shield_Side00` | CsI:5.9 | CsI:511; Aluminium:194 | absorbed before TES / CsI / `CsI_Active_Shield_Side00` |
| old_shielded | `rep01_part01:99` | - | `Outer_Al_Mech_Shell` | Aluminium:0.214 | Aluminium:367 | scattered/no TES / Aluminium / `Outer_Al_Mech_Shell` |
| old_shielded | `rep01_part01:148` | - | `CsI_Active_Shield_Side04` | CsI:4.26 | CsI:511; Aluminium:53.4 | absorbed before TES / CsI / `CsI_Active_Shield_Side04` |
| old_shielded | `rep01_part01:167` | - | `CsI_Active_Shield_Side04` | CsI:10.8 | CsI:511; Aluminium:45.6 | absorbed before TES / CsI / `CsI_Active_Shield_Side04` |
| old_selected | `rep01_part01:27173` | - | `Outer_Al_Mech_Shell` | Ta/TES:31.7 | Ta/TES:511; Aluminium:149 | TES hit / Ta/TES / `TP_L5_00059` |
| old_selected | `rep01_part01:32527` | - | `Outer_Al_Mech_Shell` | Ta/TES:33.2 | Ta/TES:511; Aluminium:10.3 | TES hit / Ta/TES / `TP_L3_00005` |
| old_selected | `rep01_part01:37120` | - | `TP_L2_00062` | Ta/TES:31.3 | Ta/TES:511 | TES hit / Ta/TES / `TP_L2_00062` |
| old_selected | `rep01_part01:73592` | - | `Outer_Al_Mech_Shell` | Ta/TES:49.2 | Ta/TES:511; Aluminium:8.2 | TES hit / Ta/TES / `TP_L5_00099` |
| old_selected | `rep02_part01:27173` | - | `Outer_Al_Mech_Shell` | Ta/TES:31.7 | Ta/TES:511; Aluminium:149 | TES hit / Ta/TES / `TP_L5_00059` |
| old_selected | `rep02_part01:32527` | - | `Outer_Al_Mech_Shell` | Ta/TES:33.2 | Ta/TES:511; Aluminium:10.3 | TES hit / Ta/TES / `TP_L3_00005` |
| old_selected | `rep02_part01:37120` | - | `TP_L2_00062` | Ta/TES:31.3 | Ta/TES:511 | TES hit / Ta/TES / `TP_L2_00062` |
| old_selected | `rep02_part01:73592` | - | `Outer_Al_Mech_Shell` | Ta/TES:49.2 | Ta/TES:511; Aluminium:8.2 | TES hit / Ta/TES / `TP_L5_00099` |
| old_selected | `rep03_part01:27173` | - | `Outer_Al_Mech_Shell` | Ta/TES:31.7 | Ta/TES:511; Aluminium:149 | TES hit / Ta/TES / `TP_L5_00059` |
| old_selected | `rep03_part01:32527` | - | `Outer_Al_Mech_Shell` | Ta/TES:33.2 | Ta/TES:511; Aluminium:10.3 | TES hit / Ta/TES / `TP_L3_00005` |
| old_selected | `rep03_part01:37120` | - | `TP_L2_00062` | Ta/TES:31.3 | Ta/TES:511 | TES hit / Ta/TES / `TP_L2_00062` |
| old_selected | `rep03_part01:73592` | - | `Outer_Al_Mech_Shell` | Ta/TES:49.2 | Ta/TES:511; Aluminium:8.2 | TES hit / Ta/TES / `TP_L5_00099` |

## Files

- Event ledger CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger_events.csv`
- Segment ledger CSV: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger_segments.csv`
- Summary JSON: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger_summary.json`
- Stack figure PNG: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_path_stacks.png`
- Stack figure SVG: `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_path_stacks.svg`

## Interpretation

Current selected prompt-eplus W2 events should not be read as photons punching through a thick, continuous passive column. Most are born in or near side-port/side-wall materials and then have a short local post-annihilation branch whose first hard endpoint is the TES stack. The side-region no-TES samples show the complementary behavior: the branch terminates in side shield materials, with substantial CC energy deposition and no TP_L hit.

Old `new_geo_re` does not reproduce the same side-port leak topology; the side-region sample is stopped in the solid old side material column, while the old selected W2 events remain tied to the old axial/top-stack geometry.
