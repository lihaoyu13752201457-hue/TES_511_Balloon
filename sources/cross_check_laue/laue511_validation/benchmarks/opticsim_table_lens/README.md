# Opticsim Table-Lens Closure

Imported from `/home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process`.

This is a full five-ring opticsim closure check. It compares the
table-driven Barhoum-style baseline with the Guan/Reiazi-style online
Darwin-Hamilton process using the same Ge(111) lens geometry.

- ok: True
- Guan diffraction fraction: 0.24675
- table-driven diffraction fraction: 0.24638
- delta diffraction fraction: 0.00037
- max per-ring mean p_diff delta: 0.000631
- max per-ring sampled diffraction-fraction delta: 0.002849
- spot d90 delta: -0.001167 cm

It is useful full-lens evidence, but it is still internal to the opticsim
model family and does not replace a direct LLL/HEART-style external oracle.
