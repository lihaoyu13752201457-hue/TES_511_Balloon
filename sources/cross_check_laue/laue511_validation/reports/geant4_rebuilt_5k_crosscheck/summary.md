# Geant4 vs Python Laue reference

Geant4 run: `/tmp/laue511_g4_latest_run`
Rows checked: 5000

## Probability kernel agreement

- p_diff: max abs delta 5.08754e-11
- p_abs: max abs delta 3.63427e-11
- p_trans: max abs delta 5.04911e-11

## Ring branch checks

- ring 0: N=1008, diff=0.259921 (z=0.26), abs=0.333333 (z=-0.76), trans=0.406746 (z=0.51)
- ring 1: N=1008, diff=0.239087 (z=-0.79), abs=0.357143 (z=0.29), trans=0.403770 (z=0.41)
- ring 2: N=1008, diff=0.253968 (z=0.56), abs=0.349206 (z=-0.51), trans=0.396825 (z=0.01)
- ring 3: N=1008, diff=0.235119 (z=-0.41), abs=0.350198 (z=-0.91), trans=0.414683 (z=1.26)
- ring 4: N=968, diff=0.236570 (z=0.13), abs=0.359504 (z=-0.75), trans=0.403926 (z=0.62)

## Focal Length

- ring CSV inferred focal length mean: 8301.499662 mm
- Geant4 summary focal length: 8300 mm
- relative delta: 0.00018065

## Schema

- phase_space.csv ok: True
- transmitted_space.csv ok: True
- vector diagnostics present in optics_history.csv: True
- diffracted rows with vector model: 1225/1225
- max angle_code_vs_recorded_reflect_rad: 1.49012e-08
- max relative_bragg_residual_perturbed: 0.0591069
