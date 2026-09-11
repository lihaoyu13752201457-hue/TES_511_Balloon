# Geant4 vs Python Laue reference

Geant4 run: `/home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process`
Rows checked: 100000

## Probability kernel agreement

- p_diff: max abs delta 5.14268e-11
- p_abs: max abs delta 3.63427e-11
- p_trans: max abs delta 5.1356e-11

## Ring branch checks

- ring 0: N=20016, diff=0.258143 (z=0.60), abs=0.342526 (z=-0.66), trans=0.399331 (z=0.11)
- ring 1: N=20016, diff=0.250899 (z=0.34), abs=0.351918 (z=-0.24), trans=0.397182 (z=-0.06)
- ring 2: N=20016, diff=0.248351 (z=0.63), abs=0.359762 (z=0.82), trans=0.391886 (z=-1.36)
- ring 3: N=20008, diff=0.242803 (z=0.71), abs=0.364004 (z=-0.00), trans=0.393193 (z=-0.62)
- ring 4: N=19944, diff=0.233504 (z=-0.43), abs=0.370086 (z=-0.30), trans=0.396410 (z=0.67)

## Focal Length

- ring CSV inferred focal length mean: 8301.499662 mm
- Geant4 summary focal length: 8300 mm
- relative delta: 0.00018065

## Schema

- phase_space.csv ok: True
- transmitted_space.csv ok: True
- vector diagnostics present in optics_history.csv: False
