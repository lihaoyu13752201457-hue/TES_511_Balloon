# WP03 - source semantics and excited-ion strategy

Gate: G3 Source semantics.

Purpose:
- Determine whether the installed Cosima can accept state-resolved delayed
  ions through ordinary source-card syntax.
- Determine the authoritative source format for WP04.
- Record the DetectorTimeConstant parser path before any delayed transport.

Inputs:
- `engineering/delayed_source_authority_v2_20260624/01_raw_inventory/raw_inventory_source_rows.csv`
- `engineering/delayed_source_authority_v2_20260624/02_rpip_alignment/dat_rpip_key_join.csv`
- `/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCParameterFile.cc`
- `/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCIsotopeStore.cc`
- `/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCSource.cc`
- `/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCSteppingAction.cc`

Outputs:
- `03_source_semantics/installed_megalib_activation_semantics.md`
- `03_source_semantics/decay_chain_semantics.md`
- `03_source_semantics/detector_time_constant_authority.md`
- `03_source_semantics/excited_ion_source_syntax_test.source`
- `03_source_semantics/excited_ion_source_syntax_test.log`
- `03_source_semantics/source_semantics_verdict.json`
- `03_source_semantics/summary.json`
- `03_source_semantics/summary.md`

PASS condition:
- Local source-code evidence shows one path that preserves excitation state.
- Unsupported ordinary source syntax is not used for source-v2 authority.
- The next source-building gate has a concrete format decision.

Blocking conditions:
- No installed Cosima path can preserve excitation state.
- DetectorTimeConstant semantics cannot be traced to the installed code.
