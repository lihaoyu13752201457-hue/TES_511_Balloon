# Geometry Optimization Draft: S3a BGO Barrel

Status: `DRAFT_S3A_BGO_BARREL_GEOMETRY_ONLY`

S3 geometry with the full-wrap CsI scintillator changed to BGO; S3 8 mm Al shell retained.

This is derived from the S3 CsI-barrel geometry recipe.  The branch is geometry
only: source cards, run directories, detector-response products, Mass_model_511
authority files, and existing S3 products are not modified.

## Boundary

- S2b BPE and plastic cryostat-following shells are unchanged.
- S3 side-window aperture, top service opening, NF2 reliefs, and pump-line
  relief treatment are retained.
- Native detector trigger thresholds are inherited from S3.

## New Replacement Volumes

| Volume | Material | r cm | z cm | Mass kg pre-relief | Role |
|---|---|---:|---:|---:|---|
| `BGO_S3A_FullWrap_SideShell_WindowCut_40mm` | `BGO` | 21.20--25.20 | -19.40..40.90 | 250.689 | 4 cm BGO active side shell; S3 dimensions and side-window cut retained |
| `BGO_S3A_FullWrap_BottomCap_40mm` | `BGO` | 0.00--25.20 | -23.40..-19.40 | 56.898 | 4 cm BGO active bottom cap; S3 dimensions retained |
| `BGO_S3A_FullWrap_TopAnnulus_40mm` | `BGO` | 20.90--25.20 | 40.90..44.90 | 17.761 | 4 cm BGO active top annulus; top service opening retained |
| `ActiveShield_S3A_BGO_Kapton_SideWrap_WindowCut_0p3mm` | `Kapton` | 25.37--25.40 | -23.57..45.07 | 0.466 | thin Kapton side wrapper following the BGO shell; side-window cut retained |
| `ActiveShield_S3A_BGO_Kapton_BottomCap_0p3mm` | `Kapton` | 0.00--25.40 | -23.60..-23.57 | 0.086 | thin Kapton bottom wrapper between the BGO cap and outer shell |
| `ActiveShield_S3A_BGO_Kapton_TopAnnulus_0p3mm` | `Kapton` | 20.90--25.40 | 45.07..45.10 | 0.028 | thin Kapton top annulus wrapper preserving the BGO top service opening |
| `Outer_Al_S3A_BGO_Mechanical_SideShell_WindowCut_8mm` | `Aluminium` | 25.50--26.30 | -23.70..45.20 | 24.219 | 0.8 cm Al mechanical side shell following the BGO shell; S3 dimensions retained |
| `Outer_Al_S3A_BGO_Mechanical_BottomCap_8mm` | `Aluminium` | 0.00--26.30 | -24.50..-23.70 | 4.694 | 0.8 cm Al mechanical bottom cap for the BGO shell; S3 dimensions retained |
| `Outer_Al_S3A_BGO_Mechanical_TopAnnulus_8mm` | `Aluminium` | 20.90--26.30 | 45.20..46.00 | 1.730 | 0.8 cm Al mechanical top annulus for the BGO shell; S3 dimensions retained |

## Generated Files

- Geometry setup: `engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Geometry body: `engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- Detector map: `engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- Manifest: `engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/geoopt_s3a_geometry_manifest.json`
- Overlap source card: `engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/geometry/overlap_check_s3a.source`

## Validation

The builder generated the files and ran static text checks.  A separate
MEGAlib/cosima load/overlap helper run was executed with
`geometry/overlap_check_s3a.source` after sourcing
`engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/megalib_env.sh`;
it completed with exit code 0.  No prompt/delayed/atm511/focused transport,
Step05, or Step06--08 product was run for this geometry-only change.
