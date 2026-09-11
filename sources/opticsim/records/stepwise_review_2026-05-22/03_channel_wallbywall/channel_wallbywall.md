# 03 Channel wall-by-wall optics

This step records the current Channel route. Photons are propagated through the public W/Si bilayer channel geometry wall by wall; survival is determined by geometry, multilayer reflectivity, path absorption choice, and leakage/exit, not by fitting a calibration multiplier.

![wall outcomes](channel_wallbywall_outcomes.png)

![closure variants](channel_closure_variants.png)

Deep dive files:

- `implementation_manual.md`
- `code_commentary.md`
- `code_function_map.csv`
- `channel_wallbywall_scene.wrl`
- `channel_wrl_quicklook.png`

## Wall-by-wall run

Source: `runs/channel_wallbywall_rebuild/summary.json`

| item | value |
|---|---:|
| primaries | 20000 |
| survived | 5804 |
| absorbed | 10423 |
| entry blocked | 3425 |
| leaked | 348 |
| transmissivity | 0.2902 |
| effective area cm2 | 18.4617 |
| spot D90 cm | 1.0329 |
| mean bounces per survivor | 19.6239 |
| max bounces guard | 1111 |

## No-fudge closure against CAM511 headline

Source: `runs/channel_independent_closure/summary.json`

| item | value |
|---|---:|
| CAM511 target transmissivity | 0.8 |
| best no-fudge transmissivity | 0.7615 |
| best no-fudge delta | -0.0385 |
| best no-fudge effective area cm2 | 48.4445 |
| 1 nm roughness no-Si transmissivity | 0.7369 |
| 1 nm roughness no-Si delta | -0.0631 |
| no-fudge reaches CAM511 | False |

## Review target

Audit the physical meaning of three switches: roughness, whether to include Si path absorption, and public-geometry open fraction. The best no-fudge case is close to the CAM511 0.80 headline but does not exactly reach it, so the honest conclusion is "public information aligns closely, but the remaining accounting gap is not eliminated."

## Non-claim

This does not claim access to the original CAM511 IDL/IMD model, exact aperture engineering drawings, or final assembly tolerances.
