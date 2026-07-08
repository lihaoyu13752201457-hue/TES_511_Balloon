# Geometry Optimization Draft: S2b 45-degree cryostat shell

Status: `DRAFT_S2B_CRYO_SHELL_45DEG_NOT_TRANSPORT_VALIDATED`

This branch replaces the over-large S2 sealed outer-can interpretation with a small shell
that follows the cryostat axis.  The added volumes are children of `InstrumentFrame`,
whose intro geometry has `InstrumentFrame.Rotation 0 45 0`; therefore the shell is
45 degrees in world coordinates without using the NF2 support-cage envelope.

Only plastic scintillator and borated polyethylene are added in this branch.  No W baffle
or other passive gamma collimator is added here.

## Dimensions

- BPE side shell: `r=27.0-29.0 cm`, `z=-24.5..46.0 cm`, thickness 20 mm.
- BPE caps: bottom `z=-26.5..-24.5`, top `z=46.0..48.0`, solid to `r=29.0 cm`.
- Plastic side skin: `r=29.0-30.0 cm`, `z=-26.5..48.0 cm`, thickness 10 mm.
- Plastic caps: bottom `z=-27.5..-26.5`, top `z=48.0..49.0`, solid to `r=30.0 cm`.
- NF2 support annuli/rods are excluded from the envelope; local reliefs are subtracted where they pass through the shell.
- Production source sphere: `SurroundingSphere 60 5.0 0.0 9.0 60`.

## Added mass

- Plastic scintillator: `20.048 kg` before relief subtraction.
- Borated polyethylene: `33.606 kg` before relief subtraction.
- Total added mass: `53.653 kg` before relief subtraction.

## Visual outputs

- Geometry WRL: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/geoopt_s2b_cryo_shell_45deg.wrl`
- Geometry 2D PNG: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/geoopt_s2b_cryo_shell_45deg_2d_detail.png`
- Source WRL on full geometry, original S1 R60: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/source_1000_prompt_rays_original_s1_R60.wrl`
- Source WRL on full geometry, S2b R60: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/source_1000_prompt_rays_s2b_cryo_shell_R60.wrl`
- Source WRL on full geometry, original S1 R65: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/source_1000_prompt_rays_original_s1_R65_full_geometry_coverage.wrl`
- Source WRL on full geometry, S2b R65: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/source_1000_prompt_rays_s2b_cryo_shell_R65_full_geometry_coverage.wrl`
- Source PNG comparison: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/source_1000_prompt_rays_original_vs_s2b.png`
- Source radius coverage notes: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures/source_radius_coverage_notes.txt`

## Added volumes

| Volume | Material | Mass kg | Role |
|---|---:|---:|---|
| `GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm` | `BoratedPolyethylene5wtB` | 23.566 | 20 mm BPE side shell following InstrumentFrame; sized to the cryostat/outer-Al body, with NF2 support reliefs |
| `GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm` | `BoratedPolyethylene5wtB` | 5.020 | 20 mm BPE bottom cap below the cryostat body, with NF2 support reliefs |
| `GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm` | `BoratedPolyethylene5wtB` | 5.020 | 20 mm BPE top cap above the 300K top-service sleeves, with NF2 support reliefs |
| `GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm` | `PlasticScintillator` | 14.223 | 10 mm active plastic side skin outside the BPE cryostat shell, with NF2 support reliefs |
| `GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm` | `PlasticScintillator` | 2.912 | 10 mm active plastic bottom cap outside the BPE bottom cap, with NF2 support reliefs |
| `GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm` | `PlasticScintillator` | 2.912 | 10 mm active plastic top cap closing the cryostat-following shell, with NF2 support reliefs |
