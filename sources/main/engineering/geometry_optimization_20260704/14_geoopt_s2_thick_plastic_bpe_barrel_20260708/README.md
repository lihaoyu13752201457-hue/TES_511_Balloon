# Geometry Optimization Draft: S2 Thick Plastic/BPE Barrel

Status: `DRAFT_S2_THICK_PLASTIC_BPE_BARREL_NOT_TRANSPORT_VALIDATED`

This directory contains a derived geometry draft built from the Mass_model_511 proxy geometry.
The source geometry is read-only; generated files live only under this workpackage directory.

User-reviewed revision implemented here:
- active plastic scintillator thickness is doubled from 5 mm to 10 mm;
- borated polyethylene thickness is doubled from 10 mm to 20 mm;
- both plastic and BPE are extended into top disks instead of the S1 annular top caps;
- top disks include local annular reliefs for the still/4K/60K/vacuum side walls, CP-Still cable/support arcs, and four XS400 support rods;
- the retained 5 mm bottom W baffle is not modified; the BPE bottom cap is extended downward to avoid it.

## Source

- Source geometry directory: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy`
- Historical R3 e+ skin metrics retained for provenance only: `engineering/background_anatomy_20260704/r3_metrics.json`

## Patch Contents

| Volume | Material | Mass kg | Role |
| --- | ---: | ---: | --- |
| `GeoOpt_S2_PlasticFullWrap_SideShell_10mm` | PlasticScintillator | 6.415 | 10 mm full-azimuth active plastic scintillator outer side skin; covers the side-window azimuth as a charged-particle sentinel instead of using the earlier low-statistics segmented S1 sector proxy; includes two local NF2 outer-support rod relief cutouts near the lower edge |
| `GeoOpt_S2_PlasticFullWrap_BottomCap_10mm` | PlasticScintillator | 2.610 | 10 mm active plastic scintillator bottom disk closing the outer charged-particle veto envelope; includes two local NF2 outer-support rod relief cutouts |
| `GeoOpt_S2_PlasticFullWrap_TopCap_10mm` | PlasticScintillator | 2.610 | 10 mm active plastic scintillator top disk over the former central service/support opening, with local service reliefs |
| `GeoOpt_S2_BPE5_FullWrap_SideShell_SignalWindowCut_20mm` | BoratedPolyethylene5wtB | 10.565 | 20 mm borated polyethylene inner side shell with a rectangular negative-x signal-window cutout; kept inside the plastic scintillator skin so the BPE does not become the first passive charged-particle stop |
| `GeoOpt_S2_BPE5_FullWrap_BottomCap_20mm` | BoratedPolyethylene5wtB | 4.160 | 20 mm borated polyethylene bottom disk inside the plastic skin; extended downward to avoid the retained W baffle and bottom shell |
| `GeoOpt_S2_BPE5_FullWrap_TopCap_20mm` | BoratedPolyethylene5wtB | 4.160 | 20 mm borated polyethylene top disk inside the plastic skin, covering the former central service/support opening with local service reliefs |
| `GeoOpt_W_BottomBaffle_5mm_R60` | W | 1.091 | 5 mm local tungsten bottom gamma baffle retained unchanged from the S1 geometry; placed inward of the borated-polyethylene bottom layer and just outside the original Mass_model_511 bottom shell. It is not treated as the primary ATM511 sidecar mitigation path. |

## Geometry Choices

- Plastic skin: thickness `1 cm`, side `r=28.4-29.4 cm`, `z=-25.1..9.2 cm`, closed bottom disk and top disk `r=0..28.4 cm` with local service reliefs; no phi segmentation.
- Borated PE: thickness `2 cm`, side `r=26.4-28.4 cm`, `z=-24.1..8.2 cm`, closed top disk `r=0..26.4 cm`.
- BPE bottom cap: disk `r=0..26.4 cm`, `z=-24.1..-22.1 cm`; it thickens downward relative to S1 to avoid the unchanged W baffle and bottom shell.
- Top service reliefs: annular reliefs `(('DRStillPot', 0.0, 3.05), ('StillShieldSideWall', 15.3, 16.0), ('Shield4KSideWall', 17.5, 18.1), ('Shield60KSideWall', 18.0, 18.7), ('VacuumJacketSideWall', 19.8, 20.9))`, CP-Still sector reliefs `(('DRHexCPStill', 0.0, 108.0, 5.0, 5.7), ('DRCapillaryCPStill', 38.4, 43.2, 6.0, 6.5), ('NbTiBundleCPStill', 99.4, 61.2, 6.4, 7.1), ('G10SupportRingCPStill', 210.0, 90.0, 7.8, 8.6))`, plus four XS400 rod relief boxes centered at `((6.19112313, 2.25338454), (-6.19112313, -2.25338454), (-1.14407331, -6.48836217), (5.04704982, -4.23497764))`.
- Top service/support opening: no longer left open as a full `r<20.9 cm` aperture; only local reliefs remain in this S2 draft.
- BPE signal-window cutout: `negative-x`, centered at `z=-5.2 cm`, half-widths `y=2.4 cm`, `z=2.4 cm`; no extra window material is added.
- Plastic bottom NF2 rod relief cutouts: centers at `(x,y)=(-19.50, +/-19.80) cm`, half-widths `6.00 x 6.00 x 0.70 cm`.
- Plastic side NF2 rod relief cutouts: local centers at `(x,y,z)=(-19.50, +/-19.80, -14.90) cm`, half-widths `6.00 x 6.00 x 3.00 cm`.
- W baffle: `r=0..6.00 cm`, `z=-22.05..-21.55 cm`, thickness `0.50 cm`.
- Historical R3 segmented skin metrics are provenance only when available; the generated S2 full-wrap mass is listed in the manifest.

## Generated Files

- Geometry setup: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Geometry body: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- Detector map copy with plastic-skin detector entries: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- Local materials copy with PlasticScintillator and BoratedPolyethylene5wtB: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/geometry/Materials_DEMO2_DR_v3p5.geo`
- WRL visualization: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/figures/geoopt_s2_thick_plastic_bpe_barrel.wrl`
- 2D detail PNG: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/figures/geoopt_s2_thick_plastic_bpe_barrel_2d_detail.png`
- 2D detail SVG: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/figures/geoopt_s2_thick_plastic_bpe_barrel_2d_detail.svg`
- Manifest: `engineering/geometry_optimization_20260704/14_geoopt_s2_thick_plastic_bpe_barrel_20260708/geoopt_s2_thick_plastic_bpe_barrel_manifest.json`

## Boundary

This is not a transport result, not a replacement geometry authority, and not a paper-facing number source.
Overlap, mechanical clearance, signal throughput, and S2 active-volume scorer validation are intentionally separate follow-up gates.
