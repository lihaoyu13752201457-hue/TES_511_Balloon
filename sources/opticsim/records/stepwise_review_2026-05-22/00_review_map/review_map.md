# 00 Review map

![pipeline](review_pipeline.png)

## What was copied from the COSMOSRAY Records style

- One physics or software step per directory.
- Each step has an `.md` file and at least one visual artifact.
- Each claim points back to a local source file, usually `summary.json` or `per_ring_summary.json`.
- Each step states what it does not prove, so later review can focus on the right weak point.

## Local source files used here

| evidence | path |
|---|---|
| Laue Barhoum-style baseline | `runs/geant4_laue_multiring_darwin/summary.json` |
| Laue baseline per ring | `runs/geant4_laue_multiring_darwin/per_ring_summary.json` |
| Guan-style compiled process | `runs/geant4_laue_darwin_guan_process/summary.json` |
| Guan vs Barhoum comparison | `runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json` |
| Channel wall-by-wall | `runs/channel_wallbywall_rebuild/summary.json` |
| Channel independent closure | `runs/channel_independent_closure/summary.json` |
| Detector wall-by-wall smoke | `runs/geant4_detector_wallbywall_1k/summary.json` |
| Detector I/O contract | `runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json` |
| Activation builder smoke | `runs/activation/synthetic_al28_day15/source_build_summary.json` |
| Activation focal smoke | `runs/activation/synthetic_al28_day15/focal_transport_no_neutrino/summary.json` |

## Current boundaries

- The Guan-style code is a compiled local process/model split. It is not a source-code migration of Guan or Reiazi and it is not registered inside the Geant4 EM category.
- The Channel code is a public-geometry wall-by-wall reconstruction. It is not the original 511-CAM IDL/IMD production model.
- The activation step in this repository is currently a workflow/smoke scaffold, not a production-statistics activation result.
