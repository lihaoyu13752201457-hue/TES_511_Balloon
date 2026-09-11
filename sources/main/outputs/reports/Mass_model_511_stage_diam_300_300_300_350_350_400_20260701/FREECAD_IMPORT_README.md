# FreeCAD Import Package

This package converts the generated WRL visualization into OBJ/MTL for FreeCAD import.

## Files

- OBJ: `DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_freecad_mm.obj`
- Faster material-merged OBJ: `DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_freecad_material_merged_mm.obj`
- Colored semantic review OBJ: `DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_freecad_review_colored_mm.obj`
- MTL: `DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_freecad_mm.mtl`
- Colored semantic review MTL: `DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_freecad_review_colored_mm.mtl`
- Source WRL: `DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400.wrl`

## Units

The MEGAlib geometry is in centimeters. This OBJ is scaled by 10, so coordinates are in millimeters for FreeCAD.

## Contents

Full object-preserving OBJ:

- Objects: `3113`
- Vertices: `57944`
- Faces: `84996`
- Materials: `16`

Material-merged OBJ for responsive FreeCAD display:

- Objects: `16`
- Vertices: `57944`
- Faces: `84996`
- Materials: `16`

Colored semantic review OBJ:

- Objects: `26`
- Vertices: `57944`
- Faces: `84996`
- Materials: `26`

## Notes

- Object names are preserved as OBJ `o`/`g` records.
- The material-merged OBJ preserves all geometry but intentionally does not preserve per-part object names.
- The colored semantic review OBJ groups geometry by function and makes outer shielding/envelopes semi-transparent.
- This is a faceted mesh CAD package, not exact analytic STEP solids.
- FreeCAD was not available in this container, so native `.FCStd` export was not performed here.
