# Geometry Optimization Draft: Full Plastic Skin + BPE + 5 mm Bottom W

Status: `DRAFT_ANALYTIC_PATCH_NOT_TRANSPORT_VALIDATED`

This directory contains a derived geometry draft built from the Mass_model_511 proxy geometry.
The source geometry is read-only; generated files live only under this workpackage directory.

User-reviewed revision implemented here:
- active plastic scintillator is full-wrap rather than segmented by the low-statistics e+ sample;
- borated polyethylene is a full inner envelope with only the signal-window region cut out;
- the bottom W baffle is 5 mm thick and placed inward of the borated polyethylene.

## Source

- Source geometry directory: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy`
- Historical R3 e+ skin metrics retained for provenance only: `engineering/background_anatomy_20260704/r3_metrics.json`

## Patch Contents

| Volume | Material | Mass kg | Role |
| --- | ---: | ---: | --- |
| `GeoOpt_S1_PlasticFullWrap_SideShell_5mm` | PlasticScintillator | 2.711 | Full-azimuth active plastic scintillator outer side skin; covers the side-window azimuth as a charged-particle sentinel instead of using the earlier low-statistics segmented S1 sector proxy; includes two local NF2 outer-support rod relief cutouts near the lower edge |
| `GeoOpt_S1_PlasticFullWrap_BottomCap_5mm` | PlasticScintillator | 1.259 | Active plastic scintillator bottom skin closing the outer charged-particle veto envelope; includes two local NF2 outer-support rod relief cutouts |
| `GeoOpt_S1_PlasticFullWrap_TopCap_5mm` | PlasticScintillator | 0.553 | Active plastic scintillator top annulus skin; preserves the existing central service/support opening |
| `GeoOpt_BPE5_FullWrap_SideShell_SignalWindowCut_10mm` | BoratedPolyethylene5wtB | 4.544 | 1 cm borated polyethylene inner side shell with a rectangular negative-x signal-window cutout; kept inside the plastic scintillator skin so the BPE does not become the first passive charged-particle stop |
| `GeoOpt_BPE5_FullWrap_BottomCap_10mm` | BoratedPolyethylene5wtB | 2.241 | 1 cm borated polyethylene bottom cap inside the plastic skin and outside the W bottom baffle |
| `GeoOpt_BPE5_FullWrap_TopCap_10mm` | BoratedPolyethylene5wtB | 0.937 | 1 cm borated polyethylene top annulus inside the plastic skin; preserves the existing central service/support opening |
| `GeoOpt_W_BottomBaffle_5mm_R60` | W | 1.091 | 5 mm tungsten bottom baffle for lower-hemisphere atmospheric 511 keV photons; placed inward of the borated-polyethylene bottom layer and just outside the original Mass_model_511 bottom shell |

## Geometry Choices

- Plastic skin: `r=27.4-27.9 cm`, side `z=-23.1..7.2 cm`, bottom cap, and annular top cap; no phi segmentation.
- Borated PE: `r=26.4-27.4 cm`, side `z=-22.1..6.2 cm`, bottom cap, and annular top cap.
- Top service/support opening: `r< 20.9 cm` is left open in the top caps to avoid existing cryostat/support hardware.
- BPE signal-window cutout: `negative-x`, centered at `z=-5.2 cm`, half-widths `y=2.4 cm`, `z=2.4 cm`; no extra window material is added.
- Plastic bottom NF2 rod relief cutouts: centers at `(x,y)=(-19.50, +/-19.80) cm`, half-widths `4.00 x 4.00 x 0.30 cm`.
- Plastic side NF2 rod relief cutouts: local centers at `(x,y,z)=(-19.50, +/-19.80, -14.90) cm`, half-widths `4.00 x 4.00 x 0.75 cm`.
- W baffle: `r=0..6.00 cm`, `z=-22.05..-21.55 cm`, thickness `0.50 cm`.
- Historical R3 reported S1 mass was `7.28004 kg`; the generated full-wrap mass is listed in the manifest and is not the R3 segmented proxy mass.

## Generated Files

- Geometry setup: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Geometry body: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- Detector map copy with plastic-skin detector entries: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- Local materials copy with PlasticScintillator and BoratedPolyethylene5wtB: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/Materials_DEMO2_DR_v3p5.geo`
- WRL visualization: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/figures/geo_opt_s1_bottomw_b4c.wrl`
- 2D detail PNG: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/figures/geo_opt_s1_bottomw_b4c_2d_detail.png`
- 2D detail SVG: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/figures/geo_opt_s1_bottomw_b4c_2d_detail.svg`
- Manifest: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geo_opt_s1_bottomw_b4c_manifest.json`

## Boundary

This is not a transport result, not a replacement geometry authority, and not a paper-facing number source.
Overlap and transport validation are intentionally separate follow-up gates.
