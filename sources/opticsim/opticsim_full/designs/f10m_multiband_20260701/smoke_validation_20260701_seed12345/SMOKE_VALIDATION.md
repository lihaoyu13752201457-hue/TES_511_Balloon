# Multiband f10m — smoke validation (2026-07-01)

Real transport of the six-ring config through the actual
`laue_multiring_bfull_demo` binary. This proves the design **loads and
diffracts end-to-end**; it is a smoke run, not a publication result.

## Command

```bash
./analysis/run_with_geant4_114.sh /tmp/opticsim_full_build_g4_11_4/laue_multiring_bfull_demo \
  --n 12000 --seed 12345 \
  --ring-config designs/f10m_multiband_20260701/ge111_balloon511_f10m_multiband_line_config.csv \
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \
  --focal-mm 10000 --source-jitter-mm 2.2 --out /tmp/mb_smoke
```

- `--source-jitter-mm 2.2` = tile size (R2 "honest tile-footprint" illumination).
- No `--require-rocking-curve-map`: the five non-511 rings use the internal
  energy-scaled Ge(111) Darwin-Hamilton backend (see `rocking_curve_source`).

## Result — all six rings diffract at their own energy

| ring | E (keV) | r (mm) | diffracted | p_diff (transported) |
|---|---|---|---|---|
| 0 | 451 | 84.160 | 769 | 0.2638 |
| 1 | 471 | 80.586 | 756 | 0.2586 |
| 2 | 491 | 77.304 | 682 | 0.2529 |
| 3 | **511** | 74.278 | 602 | **0.2469** |
| 4 | 531 | 71.480 | 581 | 0.2406 |
| 5 | 551 | 68.886 | 492 | 0.2341 |

**Checks that pass:**

- Diffraction efficiency falls monotonically with energy (0.264 → 0.234), the
  physically expected Ge(111) structure-factor trend. The design did not just
  copy the 511 number to every ring — each ring is solved at its own energy.
- The 511 ring reproduces the single-ring reference p_diff (~0.247).
- Aggregate `emergent_focal_diffraction_fraction = 0.252` vs
  `analytic_reference = 0.250982`, Δ = +0.001 → passes the strict <0.01 gate.

## What this does NOT yet establish

- Not full statistics (12k events, not 50k) and not multi-seed.
- Per-ring **transported A_eff and focal spot** are not extracted here; that
  needs `aeff_f10m_report.py` extended to group `focal_crossings.csv` by ring /
  energy and apply the within-Be gate. The design-summary A_eff values remain
  design-stage estimates until that runs.
- Five of six energies still use the internal Darwin fallback, not external
  XOP/CRYSTAL curves.
