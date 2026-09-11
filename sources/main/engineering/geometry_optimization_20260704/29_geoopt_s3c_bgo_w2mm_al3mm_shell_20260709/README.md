# Geometry Optimization Draft: S3c BGO Barrel With 2 mm W + 3 mm Al Shell

Status: `DRAFT_S3C_BGO_W2MM_AL3MM_SHELL_GEOMETRY_ONLY`

S3 geometry combining the BGO full-wrap scintillator and the 2 mm W + 3 mm Al outer shell.

This is derived from the S3 CsI-barrel geometry recipe.  The branch is geometry
only: source cards, run directories, detector-response products, Mass_model_511
authority files, and existing S3 products are not modified.

## Boundary

- S2b BPE and plastic cryostat-following shells are unchanged.
- S3 side-window aperture, top service opening, NF2 reliefs, and pump-line
  relief treatment are retained.
- Native detector trigger thresholds are inherited from S3.

For the W+Al shell, the S3 shell inner faces are retained.  The replacement fills only `25.5..26.0 cm` on the side instead of the old `25.5..26.3 cm`; the remaining outside clearance is left empty.

## New Replacement Volumes

| Volume | Material | r cm | z cm | Mass kg pre-relief | Role |
|---|---|---:|---:|---:|---|
| `BGO_S3C_FullWrap_SideShell_WindowCut_40mm` | `BGO` | 21.20--25.20 | -19.40..40.90 | 250.689 | 4 cm BGO active side shell; S3 dimensions and side-window cut retained |
| `BGO_S3C_FullWrap_BottomCap_40mm` | `BGO` | 0.00--25.20 | -23.40..-19.40 | 56.898 | 4 cm BGO active bottom cap; S3 dimensions retained |
| `BGO_S3C_FullWrap_TopAnnulus_40mm` | `BGO` | 20.90--25.20 | 40.90..44.90 | 17.761 | 4 cm BGO active top annulus; top service opening retained |
| `ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm` | `Kapton` | 25.37--25.40 | -23.57..45.07 | 0.466 | thin Kapton side wrapper following the BGO shell; side-window cut retained |
| `ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm` | `Kapton` | 0.00--25.40 | -23.60..-23.57 | 0.086 | thin Kapton bottom wrapper between the BGO cap and outer shell |
| `ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm` | `Kapton` | 20.90--25.40 | 45.07..45.10 | 0.028 | thin Kapton top annulus wrapper preserving the BGO top service opening |
| `Outer_W_S3C_BGO_Mechanical_SideShell_WindowCut_2mm` | `W` | 25.50--25.70 | -23.70..45.20 | 42.779 | 2 mm W inner mechanical side shell replacing the inner part of the S3 8 mm Al shell around BGO |
| `Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm` | `Aluminium` | 25.70--26.00 | -23.70..45.20 | 9.065 | 3 mm Al outer mechanical side shell; outer 3 mm of the old S3 shell is left as empty clearance |
| `Outer_W_S3C_BGO_Mechanical_BottomCap_2mm` | `W` | 0.00--26.00 | -23.90..-23.70 | 8.198 | 2 mm W bottom cap adjacent to the BGO/Kapton package |
| `Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm` | `Aluminium` | 0.00--26.00 | -24.20..-23.90 | 1.720 | 3 mm Al bottom cap outside the W cap; remaining old S3 bottom thickness is empty clearance |
| `Outer_W_S3C_BGO_Mechanical_TopAnnulus_2mm` | `W` | 20.90--26.00 | 45.20..45.40 | 2.901 | 2 mm W top annulus adjacent to the BGO/Kapton package |
| `Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm` | `Aluminium` | 20.90--26.00 | 45.40..45.70 | 0.609 | 3 mm Al top annulus outside the W annulus; remaining old S3 top thickness is empty clearance |

## Generated Files

- Geometry setup: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Geometry body: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- Detector map: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- Manifest: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geoopt_s3c_geometry_manifest.json`
- Overlap source card: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/overlap_check_s3c.source`

## Validation

The builder generated the files and ran static text checks.  A separate
MEGAlib/cosima load/overlap helper run was executed with
`geometry/overlap_check_s3c.source` after sourcing
`engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/megalib_env.sh`;
it completed with exit code 0.  No prompt/delayed/atm511/focused transport,
Step05, or Step06--08 product was run for this geometry-only change.
