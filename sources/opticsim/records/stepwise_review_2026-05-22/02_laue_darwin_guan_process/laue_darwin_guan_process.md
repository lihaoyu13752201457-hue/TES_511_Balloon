# 02 Guan-style Darwin process split

This step records the local compiled C++ implementation inspired by the Guan/Reiazi architecture: separate a process object from the Darwin/Zachariasen model object, then register that process in the gamma process manager for this application.

![process schematic](guan_process_schematic.png)

![metrics](guan_vs_barhoum_metrics.png)

![per ring](guan_vs_barhoum_per_ring.png)

Deep dive files:

- `implementation_manual.md`
- `code_commentary.md`
- `code_function_map.csv`
- `laue_multiring_scene.wrl`
- `guan_wrl_quicklook.png`

## Key run summary

Source: `runs/geant4_laue_darwin_guan_process/summary.json`

| item | value |
|---|---:|
| primaries | 100000 |
| rings | 5 |
| diffraction fraction | 0.2467 |
| absorption fraction | 0.3577 |
| transmission fraction | 0.3956 |
| spot D90 cm | 0.2194 |
| registered in Geant4 EM category | False |
| model/process split | True |

## Direct comparison to step 01

Source: `runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json`

| item | value |
|---|---:|
| delta diffraction fraction | 3.7000e-04 |
| delta absorption fraction | -0.0013 |
| delta transmission fraction | 9.2000e-04 |
| delta spot D90 cm | -0.0012 |
| max abs delta mean p_diff by ring | 6.3100e-04 |

## Interpretation

The important closure is not that we copied Guan/Reiazi source code. We did not have that source. The closure is that the local process/model split uses the same geometry as step 01, computes Darwin-Hamilton mosaic probabilities online during compiled Geant4 tracking, and still reproduces the table-driven baseline to Monte Carlo scale.

## Non-claim

This is not a Geant4 toolkit patch and not an EM-category upstream integration. If that becomes necessary, this step gives the physics-equivalent app-level baseline to compare against.
