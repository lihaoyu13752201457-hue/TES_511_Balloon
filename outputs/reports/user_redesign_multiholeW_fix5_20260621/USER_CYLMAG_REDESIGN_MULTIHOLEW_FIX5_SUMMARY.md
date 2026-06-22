# User Cylindrical Redesign Multihole-W Fix5

Status: `TOPOLOGY_FIXES_APPLIED_NOT_MC_VALIDATED`

This candidate keeps the fix4 mass-model topology and applies only the requested review corrections in a new derived directory.
It is still not a prompt-511 minimal-addition candidate because the parent user redesign modifies baseline Cryoperm/50mK geometry.

## Implemented Fixes

- Replaced incorrect `Cu_50mK_Local_Can_Cylinder_2mm` x-axis open sleeve with a z-axis Still-like 2 mm Copper local cold shield.
- The 50 mK Cu can uses r=`7.45-7.65 cm`, bottom cap z=`-9.90..-9.70 cm`, and a full-azimuth top edge at z=`-0.30 cm`, touching the 50 mK cold plate lower face.
- The 50 mK cold plate radius is set to `7.80 cm` so it actually closes the larger no-notch Cu can.
- Moved `Win_50mK_Al_foil_side` to x=`-7.55 cm` so it sits on the new 50 mK Cu can side wall.
- The 50 mK Cu can has no +x service notch; its radius is placed outside the existing cold-finger clamp/stem envelope so those structures clear inside the can.
- Replaced the former solid MuMetal/Nb incident caps with `Win_MagShield_Al_foil_side`, a thin Al foil at x=`-4.35125 cm` with half-thickness `0.00125 cm`.
- Shortened the x-axis magnetic sleeve incident side to MuMetal x=`-4.35 cm` and Nb x=`-3.85 cm` so the magnetic shield remains inside the 50 mK Cu can.
- Shortened the x-axis Nb sleeve back edge to x=`4.10 cm` and the MuMetal sleeve back edge to x=`4.30 cm`; added back PCON end caps with central cold-finger clearance hole radius `1.85 cm` in both layers.
- Recut every side-wall window band listed below with a Boolean through-window: full side band minus a BRIK box with y/z half-size `1.898 cm` and x extent from outside shell to the cylinder centerline.
- Closed the simplified CsI bottom/side seam by moving side CsI lower edges to z=`-14.40 cm`, matching the bottom CsI top face.

## Side-Window Model

The side-wall openings are now true Boolean rectangular cuts in the `.geo`: each side-window band uses `Shape Subtraction full_PCON rect_window_BRIK orientation`.
The projected aperture is `3.796 cm x 3.796 cm` for the 50 mK Cu can, Still Al, 4K Al, 60K Al, vacuum jacket, CsI side wall, Kapton flex, and outer Al shell.
The x half-size is intentionally much larger than the shell thickness; that is what makes the curved side wall actually open all the way through while preserving the same y/z face aperture.
The MEGAlib geometry is globally tilted through `InstrumentFrame.Rotation 0 45 0` in the Intro file; the WRL and X-Z projections apply that parent rotation.
The Y-Z side-window face figure is explicitly a local InstrumentFrame face audit, because the real face is tilted in world coordinates.

## Artifacts

- Geometry directory: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy`
- Geometry setup: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Detector map: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- WRL visualization: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5.wrl`
- 2D X-Z projection zoom PNG: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5_xz_projection_zoom.png`
- 2D X-Z projection zoom SVG: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5_xz_projection_zoom.svg`
- 2D X-Z projection full PNG: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5_xz_projection_full.png`
- 2D X-Z projection full SVG: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5_xz_projection_full.svg`
- 2D Y-Z side-window face PNG: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5_yz_side_window_face.png`
- 2D Y-Z side-window face SVG: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5_yz_side_window_face.svg`
- Mass delta CSV: `outputs/reports/user_redesign_multiholeW_fix5_20260621/user_cylmag_redesign_multiholeW_fix5_mass_delta.csv`
- Candidate overlap source: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/overlap_check.source`
- `.det` reference check JSON: `outputs/reports/user_redesign_multiholeW_fix5_20260621/geometry_det_reference_check.json`
- Side-window material-path audit JSON: `outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json`
- cosima overlap log: `outputs/reports/user_redesign_multiholeW_fix5_20260621/cosima_overlap_fix5_20260621.log`
- prompt-511 constraint log: `outputs/reports/user_redesign_multiholeW_fix5_20260621/check_prompt511_constraints_fix5.log`

## Side-Port Opening Audit

| layer | r_inner cm | r_outer cm | rectcut y half cm | rectcut z half cm | rectcut x center cm | rectcut x half cm | shell thickness cm |
|---|---:|---:|---:|---:|---:|---:|---:|
| 50mK Cu Still-like can | 7.45 | 7.65 | 1.8980 | 1.8980 | -3.8250 | 3.8251 | 0.2000 |
| Still Al shield | 8.50 | 8.80 | 1.8980 | 1.8980 | -4.4000 | 4.4001 | 0.3000 |
| 4K Al shield | 9.90 | 10.20 | 1.8980 | 1.8980 | -5.1000 | 5.1001 | 0.3000 |
| 60K Al shield | 11.40 | 11.70 | 1.8980 | 1.8980 | -5.8500 | 5.8501 | 0.3000 |
| Vacuum jacket Al | 12.90 | 13.40 | 1.8980 | 1.8980 | -6.7000 | 6.7001 | 0.5000 |
| CsI side wall | 14.00 | 18.00 | 1.8980 | 1.8980 | -9.0000 | 9.0001 | 4.0000 |
| Kapton flex | 18.17 | 18.20 | 1.8980 | 1.8980 | -9.1000 | 9.1001 | 0.0300 |
| Outer Al shell | 18.30 | 19.10 | 1.8980 | 1.8980 | -9.5500 | 9.5501 | 0.8000 |

## Mass Delta For Fix5 Components

Estimated fix5 mass delta over listed components: `+0.6422 kg`.

| component | material | baseline kg est. | candidate kg est. | delta kg |
|---|---:|---:|---:|---:|
| Cu_50mK_Local_Can_Cylinder_2mm | Copper | 0.6267 | 0 | -0.6267 |
| Cu_50mK_StillLike_Can | Copper | 0 | 1.1027 | +1.1027 |
| Nb magnetic end caps | Nb | 0 | 0.076557 | +0.076557 |
| MuMetal magnetic end caps | MuMetal | 0 | 0.089539 | +0.089539 |
| Win_MagShield_Al_foil_side | Aluminium | 0 | 9.7265e-05 | +9.7265e-05 |

## Validation Notes

- No prompt, delayed, neutron, or signal MC closure has been run.
- `.det` reference check: PASS (`missing_count=0`); every existing passive sensitive detector concept is preserved for tracking.
- Side-window material-path audit: PASS; every cut box covers the full -x shell chord for the square aperture, the MuMetal/Nb incident caps are absent, and `Win_MagShield_Al_foil_side` is present.
- CsI seam audit: PASS; the side CsI lower edges and bottom CsI top face both sit at z=`-14.40 cm`.
- `cosima CheckForOverlaps 10000 0.0001`: PASS; `cosima_overlap_fix5_20260621.log` reaches `Summary for run Minimum` and has no `GeomVol`/`Overlap`/fatal error keywords.
- The prompt-511 constraint checker is expected to fail because this user redesign deliberately modifies/removes baseline Cryoperm/50mK/cold-plate structures.
- Constraint-checker note: it also flags the new Boolean CsI rectcut bands as `r=0` cold-region additions because the checker does not infer radii from named Boolean shapes; the actual `.geo` PCON definitions are `rin=14 cm`, `rout=18 cm`.
