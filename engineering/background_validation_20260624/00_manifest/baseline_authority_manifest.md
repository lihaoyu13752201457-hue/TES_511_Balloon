# Baseline Authority Manifest

- status: `PASS`
- git head: `7cd86de5f2c7e641a149bd508848c8c8c209fb32`
- git status: `dirty`
- fix5 setup: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- source dir: `config/megalib_sources_fullsphere20_fix5_tilt45`
- prompt run: `runs/step02_instant_fix5_fullstat_v2`
- buildup run: `runs/step02_buildup_fix5_fullstat_v2`
- delayed source: `runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source`
- Step05 summary: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json`
- manuscript source: `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`

## Warnings
- source_migration_manifest label is fix5_1of10 although the same source directory is reused by fullstat runs; run normalization files carry fullstat labels.
- worktree is dirty; manifest records current file hashes as authority for this harness run.

## Gate G0

G0 is PASS if `missing_required_files` is empty. Candidate historical outputs under `old/` are marked archived support, not current authority.
