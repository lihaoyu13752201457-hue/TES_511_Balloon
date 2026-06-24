# WP03 Source Semantics Summary

status: `PASS`

Key findings:
- Current all-ground exact-position source-v2 authority can use MEGAlib EventList plus a weight ledger.
- Nonzero-excitation exact-position EventList remains a boundary condition, not a proven authority path.
- `ActivationSources` remains the native volume-based cross-check path.
- `ParticleType` alone loses excitation state.
- `.Particles Ion` is not supported by this installed parser.
- DetectorTimeConstant is parsed in seconds; use `1e-9` for the current contract.

syntax_probe_status: `REJECTED_UNSUPPORTED_PARTICLES_ION`
syntax_probe_log: `engineering/delayed_source_authority_v2_20260624/03_source_semantics/excited_ion_source_syntax_test.log`
