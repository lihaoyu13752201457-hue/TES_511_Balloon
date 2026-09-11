# Source Construction Core Bundle

Date: 2026-06-24

Purpose: compact, GPT-readable bundle for understanding the current fix5 prompt
and delayed source construction. The bundle intentionally stays at 10 files.

## How To Read

Read files in numeric order. Files 02--06 cover prompt atmospheric source
construction and normalization. Files 07--10 cover delayed activation source
construction, ground-state correction, production-position sampling, and the
current exact-position delayed source artifact.

## Files

1. `01_README_SOURCE_CONSTRUCTION_CORE.md`
   - This guide.

2. `02_prompt_runner_run_equiv2602_pipeline_NEW_GEO.py`
   - Original path: `code/tools/run_equiv2602_pipeline_NEW_GEO.py`.
   - Explains prompt/buildup run normalization, event splitting, replicated
     non-gamma sampling, far-field area use, and run manifests.

3. `03_prompt_source_migration_manifest.json`
   - Original path:
     `config/megalib_sources_fullsphere20_fix5_tilt45/source_migration_manifest.json`.
   - Lists all eight prompt atmospheric source cards, geometry setup path,
     far-field radius, total fluxes, source-surface policy, and pointing policy.

4. `04_prompt_representative_eplus_source_card.source`
   - Original path:
     `config/megalib_sources_fullsphere20_fix5_tilt45/Background_eplus_fullsphere20.source`.
   - Representative MEGAlib prompt source card. The eplus family is included
     because it dominates the selected W2 prompt survivors.

5. `05_prompt_expacs_flux_bin_audit.csv`
   - Original path:
     `engineering/background_validation_20260624/01_prompt_source_audit/source_flux_bin_audit.csv`.
   - Records the 20 equal-mu angular bins for each of the eight EXPACS/PARMA
     particle families, including theta/phi ranges, fluxes, delta-mu, and
     delta-omega checks.

6. `06_prompt_normalization_audit.json`
   - Original path:
     `engineering/background_validation_20260624/01_prompt_source_audit/prompt_normalization_audit.json`.
   - Prompt source audit verdict. This is the key evidence for source-card flux
     closure, 60 cm far-field radius consistency, pi R^2 area handling, local
     MEGAlib FarFieldAreaSource semantics, and selected-rate reconstruction.

7. `07_delay_groundstate_fix_builder.py`
   - Original path: `code/tools/build_fixed_delay_source.py`.
   - Recomputes delayed activities with NUBASE ground-state half-lives and
     audits per-family TT division before writing the fixed delayed source.

8. `08_delay_exactpos_source_builder.py`
   - Original path: `code/tools/build_fix5_1of10_exactpos_delayed_source.py`.
   - Builds exact-position delayed source cards from recorded RP/IP production
     positions and supports the full-stat label
     `fix5_fullstat_v2_exactpos_m50000_s260613`.

9. `09_delay_exactpos_source_manifest.json`
   - Original path:
     `runs/step02_delay_fix_fix5_fullstat_v2/fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json`.
   - Current delayed exact-position source manifest. Records source path,
     geometry, generated prompt/buildup provenance, fixed activity, RP/IP rows,
     point-source count, seed, and flux conservation.

10. `10_delay_exactpos_source_summary.md`
    - Original path:
      `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.md`.
    - Human-readable summary of the current exact-position delayed source and
      transport boundary.

## Large Files Not Included

The exact-position weighted RP/IP table was not copied into this core bundle:

`runs/step02_delay_fix_fix5_fullstat_v2/exactpos_weighted_rpip_table_m50000_s260613.csv`

It is about 44 MB and is too large for a compact GPT context. Its important
counts, activity sums, sampling parameters, seed, and conservation checks are
recorded in files 09 and 10.

The actual exact-position delayed MEGAlib source card was also not copied:

`runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source`

It is about 7.1 MB and 250,017 lines, mostly repeated point-source blocks.
File 08 explains how it is generated, and file 09 records its output path,
50,000 point-source blocks, per-source flux, total activity, and source-text
flux-closure check.

## Current Interpretation Boundary

This bundle is enough to audit source construction and normalization logic. It
does not by itself prove final detector-rate claims; those also require Step05
detector response, event selection, and downstream rate/audit products.

