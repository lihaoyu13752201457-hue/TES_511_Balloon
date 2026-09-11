# 04 Detector and activation bridge

This step separates two different bridges: science photons from optics into a detector smoke model, and radioactive inventory positions into a delayed decay source. The current files are useful workflow checks, not final detector or activation rates.

![handoff](detector_activation_handoff.png)

![smoke](detector_activation_smoke.png)

## Detector handoff

Source: `runs/geant4_detector_wallbywall_1k/summary.json`

| item | value |
|---|---:|
| input photons | 5804 |
| simulated | 1000 |
| events written | 1000 |
| hits | 7102 |
| TES detected | 895 |
| BGO veto | 132 |
| TES detection fraction | 0.895 |
| BGO veto fraction | 0.132 |

I/O contract source: `runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json`

| item | value |
|---|---:|
| contract ok | True |
| tables checked | 6 |

## Activation scaffold

Source: `runs/activation/synthetic_al28_day15/source_build_summary.json` and `runs/activation/synthetic_al28_day15/focal_transport_no_neutrino/summary.json`

| item | value |
|---|---:|
| activation status | PASS |
| inventory rows | 1 |
| radioactive rows | 1 |
| day 15 activity Bq | 100 |
| decay source rows | 200 |
| focal simulated | 200 |
| focal crossings | 41 |
| skipped neutrino crossings | 46 |

## Review target

Keep detector I/O schema bugs separate from physics-performance claims. The current detector and activation steps show that the interfaces can run, while production confidence still requires a higher fidelity detector geometry and a higher statistics true-mass activation run.
