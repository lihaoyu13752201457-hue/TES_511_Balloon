# Geometry Optimization Draft: S3 CsI Barrel

Status: `DRAFT_S3_CSI_BARREL_NOT_TRANSPORT_VALIDATED`

S3 is derived from S2b.  The S2b BPE and plastic cryostat-following shells are
left unchanged.  The local CsI side segments, top annulus, bottom quadrants,
and local CsI Kapton/Al wrapper volumes are removed from this S3 copy and
replaced by a CsI full-wrap package: side shell, bottom cap, and top annulus,
with matching Kapton/Al wrapper pieces.

## Design Interpretation

- Base: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/`.
- New CsI side-shell remains at the existing CsI radial thickness:
  `r=21.2..25.2 cm` (`4.0 cm`).
- The S3 replacement package is kept inside the unchanged S2b BPE side-shell
  span: `z=-24.5..46.0 cm`.
- The bottom CsI cap is solid.  The top CsI closure is an annulus with
  inner radius `20.9 cm` to preserve top-service
  clearance inside the unchanged S2b BPE/plastic envelope.
- S2b-style NF2 support-rod reliefs are subtracted from all new S3 volumes.
  A local pump-line relief is also subtracted from the CsI side shell for
  `DR_Still_PumpLine_SS_to_300K_top`.
- Side-window aperture is retained at local `z=-5.2 cm`,
  with half-widths `y,z=1.898 cm`.
- No BPE/plastic/source-card/fix5/Mass_model authority file is changed.

## New Volumes

| Volume | Material | r cm | z cm | Mass kg | Role |
|---|---|---:|---:|---:|---|
| `CsI_S3_FullWrap_SideShell_WindowCut_40mm` | `CsI` | 21.20--25.20 | -19.40..40.90 | 158.570 | 4 cm CsI active side shell replacing the local side segments; side-window cut retained |
| `CsI_S3_FullWrap_BottomCap_40mm` | `CsI` | 0.00--25.20 | -23.40..-19.40 | 35.990 | 4 cm CsI active bottom cap closing the S3 inner veto shell inside the unchanged BPE envelope |
| `CsI_S3_FullWrap_TopAnnulus_40mm` | `CsI` | 20.90--25.20 | 40.90..44.90 | 11.235 | 4 cm CsI active top annulus closing the S3 veto shell while preserving the top service opening |
| `ActiveShield_S3_CsI_Kapton_SideWrap_WindowCut_0p3mm` | `Kapton` | 25.37--25.40 | -23.57..45.07 | 0.466 | thin Kapton side wrapper following the new CsI shell; side-window cut retained |
| `ActiveShield_S3_CsI_Kapton_BottomCap_0p3mm` | `Kapton` | 0.00--25.40 | -23.60..-23.57 | 0.086 | thin Kapton bottom wrapper between the S3 CsI bottom cap and outer Al shell |
| `ActiveShield_S3_CsI_Kapton_TopAnnulus_0p3mm` | `Kapton` | 20.90--25.40 | 45.07..45.10 | 0.028 | thin Kapton top annulus wrapper preserving the top service opening |
| `Outer_Al_S3_CsI_Mechanical_SideShell_WindowCut_8mm` | `Aluminium` | 25.50--26.30 | -23.70..45.20 | 24.219 | 0.8 cm Al mechanical side shell following the new CsI shell; side-window cut retained |
| `Outer_Al_S3_CsI_Mechanical_BottomCap_8mm` | `Aluminium` | 0.00--26.30 | -24.50..-23.70 | 4.694 | 0.8 cm Al mechanical bottom cap for the S3 CsI shell |
| `Outer_Al_S3_CsI_Mechanical_TopAnnulus_8mm` | `Aluminium` | 20.90--26.30 | 45.20..46.00 | 1.730 | 0.8 cm Al mechanical top annulus preserving the top service opening |

Approximate old local CsI mass reference: `79.274 kg`.
New CsI full-wrap mass: `205.795 kg`.
Masses above are analytic pre-relief values.

## Generated Files

- Geometry setup: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Geometry body: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- Detector map: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- Manifest: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geoopt_s3_csi_barrel_manifest.json`
- 2D detail (layer schematic, builder): `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures/geoopt_s3_csi_barrel_2d_detail.png` / `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures/geoopt_s3_csi_barrel_2d_detail.svg`
- Full-component 2D projections (XZ/XY/YZ of all meshed solids): `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures/geoopt_s3_csi_barrel_full_2d.png` / `.svg`
- Instrument-frame r–z full layer stack: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures/geoopt_s3_csi_barrel_rz_layers.png` / `.svg`
- Full 3D WRL (all meshed components + shell overlays): `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures/geoopt_s3_csi_barrel_full.wrl`
- Visual notes: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures/geoopt_s3_csi_barrel_visual_notes.md`
- Regen visuals: `python3 engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/build_s3_full_visuals.py`
- Overlap source card: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/overlap_check_s3.source`
- Removed geometry volume counts: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/s3_remove_counts.json`
- Removed detector block counts: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/s3_det_remove_counts.json`

## Validation

- `python3 -m py_compile` passed for the S3 builder.
- Static grep audit found no remaining old local CsI or old local CsI-wrapper
  `Volume` blocks in the generated S3 geometry.
- `cosima geometry/overlap_check_s3.source` completed with exit code 0 after
  NF2 support-rod and pump-line reliefs were added.  The final run did not
  report `GeomVol1002` overlap warnings.
- Smoke record: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/cosima_overlap_smoke_20260709.md`.

## Boundary

This is a geometry draft with overlap/load smoke passed.  It is not a transport
result, not a promotion, and not a background-rate claim.  The next required
gates are focused signal throughput, atmospheric-511 sidecar replay, prompt
e+/n equal-stat replay, and delayed activation review.
