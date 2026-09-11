# Upload Package 20260623

Purpose: compact file set for external GPT review of the fix5 geometry,
prompt source construction, and delayed activation-source construction.

This package intentionally avoids large generated tables/SIM/event catalogs.
It is meant for method review and source/geometry provenance review, not for
rerunning the full simulation.

If the upload UI has a strict file-count limit, upload this README plus the
following first:

- geometry: `.geo.setup`, `.geo`, `.det`, `USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md`
- prompt: `run_equiv2602_pipeline_NEW_GEO.py`, `Background_eplus_fullsphere20.source`,
  `Background_n_fullsphere20.source`, `Background_gamma_fullsphere20.source`,
  `source_migration_manifest.json`
- delayed: `METHOD_FIX5_SIM_CLOSURE.md`, `makedecaysourcewithplot_rpip.py`,
  `build_fixed_delay_source.py`, `build_fix5_1of10_exactpos_delayed_source.py`,
  `activation_decay_day15.source`, `activation_decay_day15_groundstate_fixed.source`,
  `normalization_audit_groundstate_fix.json`,
  `fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json`
- analysis note: `analysis_notes/11_fix5_w2_prompt_delayed_energy_band_stats.md`

## Geometry

Directory: `geometry/`

Core MEGAlib geometry files:

- `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`

Human/audit context:

- `USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md`
- `side_window_material_path_audit_fix5.json`

The `.geo.setup` file includes the `.geo` and `.det` files and defines the
surrounding sphere. The summary and audit explain the multihole-W fix5 design
intent and side-window material-path checks.

## Prompt Source

Directory: `prompt_source/`

Included:

- `run_equiv2602_pipeline_NEW_GEO.py`
- `Background_alpha_fullsphere20.source`
- `Background_eminus_fullsphere20.source`
- `Background_eplus_fullsphere20.source`
- `Background_gamma_fullsphere20.source`
- `Background_muminus_fullsphere20.source`
- `Background_muplus_fullsphere20.source`
- `Background_n_fullsphere20.source`
- `Background_p_fullsphere20.source`
- `source_migration_manifest.json`

How to read this:

- The `Background_*.source` files are the fix5 prompt/buildup atmospheric
  full-sphere source cards.
- `run_equiv2602_pipeline_NEW_GEO.py` is the runner that turns those source
  cards into prompt (`instant`) and isotope-production (`buildup`) Cosima jobs.
- The runner normalizes prompt by generated TimeTags downstream; non-gamma
  prompt/buildup jobs use multiple replicas, which is why delayed-source
  normalization must later guard against replica over-counting.

## Delayed Source Model

Directory: `delay_model/`

Included:

- `METHOD_FIX5_SIM_CLOSURE.md`
- `makedecaysourcewithplot_rpip.py`
- `build_fixed_delay_source.py`
- `build_fix5_1of10_exactpos_delayed_source.py`
- `audit_fix5_groundstate_half_life_units.py`

How the delayed source is built:

1. `run_equiv2602_pipeline_NEW_GEO.py` runs the fix5 `buildup` transport.
2. `makedecaysourcewithplot_rpip.py` parses isotope production from SIM
   comment lines like `CC IP RP <volume> x y z ZA exc t` plus Cosima `.dat`
   isotope yield totals, creating the raw delayed source
   `activation_decay_day15.source`.
3. `build_fixed_delay_source.py` applies the ground-state half-life correction
   and the per-particle-family division guard. This is the fix for the historic
   non-gamma replicate over-normalization issue.
4. `audit_fix5_groundstate_half_life_units.py` audits the half-life and
   normalization rows.
5. `build_fix5_1of10_exactpos_delayed_source.py` builds the exact-position
   delayed source by drawing equal-flux `PointSource` blocks from the weighted
   RP/IP inventory and writes the manifest/transport summary.

## Delayed Source Artifacts

Directory: `delay_artifacts/`

Included small artifacts:

- `activation_decay_day15.source`
- `activation_inventory_day15.csv`
- `normalization_audit_day15.json`
- `activation_decay_day15_groundstate_fixed.source`
- `normalization_audit_groundstate_fix.json`
- `source_fix_summary.json`
- `fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json`
- `fix5_delayed_source_exactpos_summary.md`
- `fix5_groundstate_half_life_audit.md`
- `fix5_w_activation_selected_w2_audit.json`

Large generated files deliberately omitted:

- `runs/step02_delay_fix_fix5_fullstat_v2/exactpos_weighted_rpip_table_m50000_s260613.csv`
  is about 45 MB.
- `runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source`
  is about 7.3 MB.
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/work/event_catalog.pkl`
  is about 81 MB.

If a reviewer needs to inspect the final generated exact-position source
syntax, add the 7.3 MB source file above. If they need to audit every sampled
position, add the 45 MB weighted table.

## Analysis Notes

Directory: `analysis_notes/`

Included:

- `11_fix5_w2_prompt_delayed_energy_band_stats.md`

This note summarizes the current fix5 W2 prompt/delayed statistics, energy-band
delayed fractions, prompt `eplus` dominance, delayed Cu-62/Cu-64 selected-event
audit, and manuscript-safe wording. It is useful context for interpreting why
the current W2 final sample is prompt dominated while activation is still not
globally negligible.

## Current Full-Stat Label

The current fix5 full-stat delayed-source label is:

`fix5_fullstat_v2_exactpos_m50000_s260613`

The authoritative geometry setup used by these files is:

`outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
