# 01 Laue Barhoum-style baseline

This step records the current local Laue baseline. The implementation is a Geant4 application-level process driven by a local Ge(111) Darwin/Zachariasen mosaic table. In the code output this is called `multiring_zachariasen_darwin_mosaic_laue_process_v3`.

![outcomes](laue_barhoum_outcomes.png)

![per ring](laue_per_ring_darwin.png)

Deep dive files:

- `implementation_manual.md`
- `code_commentary.md`
- `code_function_map.csv`
- `laue_multiring_scene.wrl`
- `laue_wrl_quicklook.png`

## Key run summary

Source: `runs/geant4_laue_multiring_darwin/summary.json`

| item | value |
|---|---:|
| primaries | 100000 |
| rings | 5 |
| diffraction fraction | 0.2464 |
| absorption fraction | 0.3589 |
| transmission fraction | 0.3947 |
| spot D90 cm | 0.2206 |
| energy min keV | 480 |
| energy max keV | 550 |
| focal length mm | 8300 |

## Review target

Check whether the ring geometry, energy band, table lookup, branch probabilities, and focal deflection are internally consistent before comparing with the Guan-style split in step 02.

## Non-claim

This step does not prove the original Barhoum codebase or a publication-grade Ge measured-crystal validation. It records the local Barhoum-style baseline we can actually rerun and compare.
