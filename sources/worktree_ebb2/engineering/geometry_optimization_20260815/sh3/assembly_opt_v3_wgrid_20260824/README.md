# SH3 assembly OptV3 — full-aperture W-grid variant

This is a new, non-overwriting geometry package derived from the frozen
`sh3/assembly_opt_v3` authority. The original SH3 package is an immutable input.

## Only geometry change

One passive tungsten multihole grid is added inside the existing four-bar W
frame. Every pre-existing byte of `SH3_Assembly_OptV3.geo` remains an exact
prefix of the new geometry. The setup, detector map and materials files are
byte-identical to the original package. In particular, the existing W frame,
optical windows, BGO, TES array, cold finger, cryostat and source sphere are not
changed.

The grid retains the model-A rule:

- pitch: 0.155 cm;
- W web width: 0.013 cm;
- W depth: 0.798 cm;
- vacuum envelope depth: 0.800 cm.

It is extended to the unchanged SH3 5.40 cm clear square, giving a 35 × 35
channel array. This avoids the 0.802 cm-per-side bypass that would result from
placing the smaller 3.796 cm model-A grid unchanged in the SH3 opening.

The new grid contains 1,224 W placements: 34 continuous horizontal webs, 1,122
internal vertical segments and 68 edge vertical segments. Its analytic W volume
is 3.623098752 cm³ (69.9258059 g at 19.3 g cm⁻³), and its normal-incidence open
fraction is 84.430%. It is centred at `(-44.7, 0, -2.8) cm` in the
`InstrumentFrame`, with no additional rotation.

## Reproducible sequence

Run one stage at a time from this package directory:

```bash
python3 -B code/build_sh3_assembly_opt_v3_wgrid.py
python3 -B code/run_sh3_assembly_opt_v3_wgrid_overlap.py
python3 -B code/export_sh3_assembly_opt_v3_wgrid_wrl.py
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/sh3_wgrid_mpl python3 -B code/render_sh3_assembly_opt_v3_wgrid_preview.py
```

The first stage pins and rechecks the original four authority hashes. The
second constructs the full geometry and executes `CheckForOverlaps 10000
0.0001` without particle transport. The third exports the native Geant4
VRML2FILE scene, also without particle transport. Audit receipts and logs are
written only inside this new package.

No transport response, activation, background or sensitivity result is claimed
by this geometry/visualization package.
