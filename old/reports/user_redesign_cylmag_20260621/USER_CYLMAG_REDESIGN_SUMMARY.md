# User Cylindrical Magnetic/Cryostat Redesign

Status: `GEOMETRY_BUILT_OVERLAP_PASS_NOT_MC_VALIDATED`

This candidate implements the user's geometry-redesign request in a new directory only.
It intentionally modifies/removes baseline structures, so it is not a prompt-511 minimal-addition candidate.

## Artifacts

- Geometry directory: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_20260621_megalib_proxy`
- Geometry setup: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Detector map: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- WRL from actual `.geo` proxy: `outputs/reports/user_redesign_cylmag_20260621/user_cylmag_redesign.wrl`
- Schematic-only WRL, not geometry authority: `outputs/reports/user_redesign_cylmag_20260621/user_cylmag_redesign_schematic_only.wrl`
- 2D schematic PNG: `outputs/reports/user_redesign_cylmag_20260621/user_cylmag_redesign_xz_schematic.png`
- 2D schematic SVG: `outputs/reports/user_redesign_cylmag_20260621/user_cylmag_redesign_xz_schematic.svg`
- Mass delta CSV: `outputs/reports/user_redesign_cylmag_20260621/user_cylmag_redesign_mass_delta.csv`
- Candidate overlap source: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_20260621_megalib_proxy/overlap_check.source`

## Implemented Changes

- Outer Al detector-bay mechanical shell thickened from 0.30 cm to 0.80 cm, preserving the inner radius and expanding outward.
- `ActiveShield_Al_Backplane_detector_bay_*` volumes removed.
- `Passive_Cu_Liner_detector_bay_*` and `Passive_W_Liner_detector_bay_*` side liner volumes removed.
- Vacuum/60K/4K/Still side walls thickened to 0.50/0.30/0.30/0.30 cm.
- BRIK-panel Nb/Cryoperm/50mK-can proxies replaced by open x-axis cylindrical sleeves:
  - Nb inner magnetic sleeve: r=4.00-4.20 cm, x=-5.8..5.5 cm.
  - MuMetal outer high-mu sleeve: r=4.25-4.45 cm, x=-6.1..5.5 cm.
  - Cu 50mK local can: r=4.50-4.70 cm, x=-6.6..5.5 cm.
- The new x-axis sleeves are open at both ends in this MEGAlib proxy; the +x end stops before the vertical Cu cold-finger stems for feedthrough clearance.
- `.det` blocks referencing deleted volumes were removed, and detector proxy blocks were added for the new Nb/MuMetal/Cu sleeves.
- The authoritative 3D WRL is a faceted export from the actual `.geo`; it preserves BRIK/PCON shapes, side-port segmentation, rotations, mothers, and non-vacuum physical copy placement. It is a visualization of the simulation proxy, not a mechanical CAD model. The old hand-drawn WRL was retained only as `*_schematic_only.wrl`.

## Known Contract Boundary

This redesign violates the prompt-511 refix minimal-change contract because it removes and replaces baseline volumes, including Cryoperm geometry.
That is expected for this user-requested redesign; the original baseline directory is untouched.

## Validation

- Cosima `CheckForOverlaps 10000 0.0001`: `PASS`.
  Log: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_20260621_megalib_proxy/cosima_overlap_user_redesign_20260621.log`.
- The first full-length sleeve attempt overlapped `Cu_ColdFinger_Stem_*`; after review, the +x sleeve ends were shortened to `x=+5.5 cm` to leave cold-finger/feedthrough clearance.
- Prompt-511 hard gate: `FAIL`, expected for this redesign because it modifies/removes baseline Cryoperm/Nb/50mK and cryostat shell structures. This candidate is not a minimal passive W/Ta/Pb shield refix.
- No prompt, delayed, neutron, signal, or activation MC closure has been run.

## Mass Estimate

Estimated mass delta over listed modified components: `+8.290 kg`.
This is a component-level estimate, not a full regenerated bounds authority.

| component | material | baseline kg | candidate kg est. | delta kg |
|---|---:|---:|---:|---:|
| Outer_Al_Mechanical_Shell_detector_bay | Aluminium | 3.715 | 9.907 | +6.192 |
| ActiveShield_Al_Backplane_detector_bay | Aluminium | 0.5097 | 0 | -0.5097 |
| Passive_Cu_Liner_detector_bay | Copper | 0.9821 | 0 | -0.9821 |
| Passive_W_Liner_detector_bay | W | 1.868 | 0 | -1.868 |
| Vacuum_Jacket_Al_266mmClass_side_port | Aluminium | 5.293 | 6.616 | +1.323 |
| Shield_60K_Al_side_window | Aluminium | 1.368 | 2.737 | +1.368 |
| Shield_4K_Al_side_window | Aluminium | 0.7328 | 1.832 | +1.099 |
| Still_Shield_Al_side_window | Aluminium | 0.3688 | 1.106 | +0.7376 |
| Nb_SideEntry_Sample_Can_with_side_aperture | Nb | 0.1691 | 0.4989 | +0.3299 |
| Cryoperm/MuMetal magnetic shield | MuMetal | 0.469 | 0.5517 | +0.08264 |
| Al_50mK_Local_Can_side_entry / Cu_50mK_Local_Can_Cylinder_2mm | Copper | 0.1097 | 0.6267 | +0.517 |

## Review Checklist

- Original baseline directory was not edited.
- TES and Cu_ColdFinger volumes were not removed or rewritten.
- This build deliberately replaces Cryoperm panel proxies with a MuMetal cylindrical proxy, per user request.
- Detector map references to removed volumes were removed; proxy detector blocks were added for the three new sleeves.
- No prompt, delayed, neutron, or signal MC closure has been run.

Removed volume count: `21`. Added volume count: `3`.
