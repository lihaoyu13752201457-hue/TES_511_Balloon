# MEGAlib / Cosima implementation guide for `DEMO2_DR_v3p5_minpatch_centerfinger`

## Geometry authority
Use `DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json` as the source of truth.  The CSV is a convenience mass table only.

This model is intentionally a **proxy mass model**, not final CAD.  The changes relative to `DEMO2_DR_v3p5_minpatch_three_fixes` are the downstream support-disk clearance, four symmetric off-axis Cu cold fingers/stems, the shared CsI side-port declaration, and a 2 cm side-entry W sleeve/collimator.

## Coordinate convention

- Units are cm.
- The 511 keV optical beam travels along `-x -> +x`.
- Beam axis is `y = 0`, `z = -5.2 cm`.
- The DR remains upright: 300 K service side is on top; MXC is at the bottom.

## Components that require explicit CSG holes

The following are **not optional annotations**.  In the MEGAlib `.geo`, implement them either by splitting the shell into PCON/BRIK panels around the hole or by using the project's supported Boolean/subtraction equivalent.

### Side optical port chain

For each side-window shell or liner, cut a side aperture centered at `y = 0`, `z = -5.2 cm`, with the radius listed in the component parameters:

- `Nb_SideEntry_Sample_Can_with_side_aperture`
- `Cryoperm_Horizontal_Sleeve_1p2mm`
- `Al_50mK_Local_Can_side_entry`
- `Still_Shield_Al_side_window`
- `Shield_4K_Al_side_window`
- `Shield_60K_Al_side_window`
- `Vacuum_Jacket_Al_266mmClass_side_port`
- `Passive_Cu_Liner_detector_bay`
- `Passive_W_Liner_detector_bay`
- `CsI_Side_Segment_03`
- `CsI_Side_Segment_04`
- `ActiveShield_Al_Backplane_detector_bay`
- `ActiveShield_Flex_Kapton_detector_bay`
- `Outer_Al_Mechanical_Shell_detector_bay`

Window/filter discs are separate volumes aligned to this port:

- `Win_50mK_Al_foil_side`
- `Win_Still_Al_foil_side`
- `Win_4K_Al_foil_side`
- `Win_60K_Al_foil_side`
- `Win_Be_Vacuum_150um_side`
- `Win_Outer_Al_Filter_side`

### Off-axis thermal-finger feedthroughs

The four-finger patch adds four symmetric off-axis thermal paths:

- four `Cu_ColdFinger_OffAxis_*_from_Disk_to_Stem` x-axis fingers;
- four `Cu_ColdFinger_Stem_*_to_MXC` vertical stems;
- four `Cu_MXC_Clamp_Pad_*_for_OffAxisStem` clamp pads.

Implement the following declared feedthroughs:

1. In `Nb_SideEntry_Sample_Can_with_side_aperture`, cut all holes listed in `plus_x_thermal_finger_feedthroughs`.
2. In `Cryoperm_Horizontal_Sleeve_1p2mm`, cut the same four +x cap feedthroughs.
3. In `Al_50mK_Local_Can_side_entry`, cut the four +x feedthroughs plus all `top_stem_slots` so each vertical stem reaches the MXC plate bottom.

Do **not** leave thermal fingers/stems overlapping closed end caps; the feedthroughs and stem slots are part of the geometry definition.

## Suggested MEGAlib shape mapping

- `z_cylinder`: PCON cylinder or TUBE aligned with z.
- `z_annulus`: PCON annular cylinder.
- `z_annulus_phi` / `z_annulus_phi_segment`: PCON with phi start/delta or split BRIK/sector approximations if needed.
- `x_disc`: PCON/TUBE rotated by 90° so its axis is x; if rotation is inconvenient, use a thin BRIK proxy only for a systematic check.
- `x_annulus`: rotated annular PCON/TUBE.  The support rings are physically important because the center must remain open.
- `x_cylinder_offaxis`: rotated cylinder; used for the Cu support rods and off-axis thermal fingers.
- `z_cylinder_offaxis`: cylinder aligned with z at an offset x/y; used for off-axis stems and clamp pads.
- `x_can`: implement as a hollow shell with end-cap panels and declared openings, not as a solid filled box.

## Mother / daughter hierarchy recommendation

A robust first MEGAlib implementation is:

1. World
2. Detector-bay vacuum jacket / cryostat volume
3. Thermal shields as daughters or siblings with non-overlapping shells
4. Magnetic sample can / Cryoperm / Nb shells
5. TES / substrates and Cu support frame inside the hollow sample-can region
6. Active CsI and outer package outside the cryostat, not inside it

## Validation steps before production transport

1. Generate `.geo` and `.det` from the JSON.
2. Run MEGAlib/Cosima overlap check.
3. Confirm that the beam path along `y=0, z=-5.2` intersects only the intended windows/filters and the TES stack, not closed shell material.
4. Confirm that the four off-axis fingers/stems touch or overlap only through declared feedthrough / union regions.
5. Recompute mass by material and compare to `DEMO2_DR_v3p5_minpatch_centerfinger_mass_budget.csv`.

## Physics/systematic follow-up

The main nominal choice left for simulation is not this feedthrough detail but material systematics:

- MXC copper plate vs Au-plated Al substitute for Cu-64 risk.
- Cryoperm 1.2 mm vs thicker magnetic-shield systematic.
- CsI side thickness 4/6/8 cm.
- Remote PT / compressor / open-cycle DR platform alternatives.
