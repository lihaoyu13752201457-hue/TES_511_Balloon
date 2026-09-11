# Opticsim stepwise review records

Date: 2026-05-22

This directory mirrors the `COSMOSRAY_BALLOON_SIM/Records` review style: split the work into small review units, and give each unit its own figures, local source paths, key numbers, and explicit non-claims. The purpose is bug hunting and later review, not a polished final paper.

![review pipeline](00_review_map/review_pipeline.png)

## Directory map

| step | directory | review purpose |
|---|---|---|
| 00 | `00_review_map` | Overall evidence map and review protocol. |
| 01 | `01_laue_barhoum_baseline` | Barhoum-style Laue baseline using the local Darwin/Zachariasen table. |
| 02 | `02_laue_darwin_guan_process` | Compiled Guan/Reiazi-inspired process/model split and direct comparison to 01. |
| 03 | `03_channel_wallbywall` | Channel wall-by-wall ray tracing, no calibration-factor closure, CAM511 alignment boundary. |
| 04 | `04_detector_activation_bridge` | Detector handoff and activation-source scaffold evidence. |
| 05 | `05_review_checklist` | Risk matrix and bug-review checklist. |
| 06 | `06_figure_scripts` | Rebuild script for all figures and markdown. |

Each of steps 01-03 also contains:

- `implementation_manual.md`: beginner-readable principle, function map, reproduction commands, and review priorities.
- `code_commentary.md`: annotated code walkthrough in plain language.
- `code_function_map.csv`: machine-readable file/function map for review.
- WRL scene or WRL-derived quicklook image.

## Regeneration

Run:

```bash
python3 records/stepwise_review_2026-05-22/06_figure_scripts/build_stepwise_review_records.py
```

The script only uses local run summaries already in this repository. It does not add a new physics claim beyond those summaries.
