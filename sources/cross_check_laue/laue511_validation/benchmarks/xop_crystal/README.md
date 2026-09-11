# XOP/CRYSTAL Rocking Curve

CRYSTAL `diff_pat` Ge(111) 511 keV mosaic Laue diffraction curve.

- ok: True
- rows: 101
- source tools: ['CRYSTAL-diff_pat']
- source versions: ['CRYSTAL diff_pat v1.8; CRYSTAL commit 9a255d904bc331ebc5deea02a95bedf1bb4e4324; xoppylib 1.0.53; DABAX 1.0.12']
- peak reflectivity: 0.25748122500000004
- absorption: 0.3338322696770665

`diff_pat` provides the diffracted rocking curve. The `absorption`
column is computed from the CRYSTAL beta-derived absorption coefficient
reported in `diff_pat.par`; `transmittivity` is the remaining flux
complement after unpolarized diffraction and absorption.
