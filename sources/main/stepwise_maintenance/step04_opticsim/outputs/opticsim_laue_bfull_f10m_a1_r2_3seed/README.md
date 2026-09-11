# f10m Ge(111) 511-line Step04 Embedding Profile

This directory is the `new_geo_re` embedded copy of the f=10 m A1/R2 honest-footprint optics profile generated in `/home/ubuntu/opticsim/opticsim_full`.

- compatibility authority: `stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json`
- full Phase-0 authority copy: `stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_20260611.json`
- combined focal crossings: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_f10m_a1_r2_3seed/focal_crossings.csv`
- per-seed focal crossings copied into this repo:
  `per_seed/focal_crossings_seed12345.csv`,
  `per_seed/focal_crossings_seed24680.csv`,
  `per_seed/focal_crossings_seed98765.csv`
- within-Be rows: `37194` / `37256`
- A_eff(511): `20.0848 cm2`
- focal r50/r90: `0.715648` / `1.02853 cm`

Build the embeddable Step09 source with:

```bash
STEP09_OPTICS_PROFILE=f10m_a1 python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
```
