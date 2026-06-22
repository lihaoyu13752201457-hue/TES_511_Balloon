# Fix5 Workflow

Use `core_md/fix5_benchmarks.json` as the numeric authority for all gates and
thresholds.

## Current Geometry

`outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

## Main Rebuild / Audit Commands

```bash
python3 code/tools/build_fix5_fullstat_release.py
python3 code/tools/audit_fix5_groundstate_half_life_units.py --label fix5_fullstat_v2_exactpos_m50000_s260613
python3 code/tools/build_fix5_1of10_exactpos_delayed_source.py summarize-transport --label fix5_fullstat_v2_exactpos_m50000_s260613
python3 code/tools/build_fix5_step09_focus.py summarize-transport
python3 code/tools/build_fix5_w_activation_selected_audit.py
python3 code/tools/build_fix5_promotion_decision.py
python3 code/tools/build_fix5_final_closure_report.py
```

Transport runner retained for fix5 prompt/buildup source cards:

```bash
python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py --source-dir config/megalib_sources_fullsphere20_fix5_tilt45 ...
```

## Current Output Labels

- `fix5_1of10`
- `fix5_fullstat_v2`
- `fix5_fullstat_v2_exactpos_m50000_s260613`

## Legacy

The previous v3p5, BGO, prompt511, and old `new_geo_re` workflow notes were
archived under `old/docs/core_md_legacy/`.
