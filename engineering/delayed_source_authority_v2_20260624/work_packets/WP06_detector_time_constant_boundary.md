# WP06 - DetectorTimeConstant and decay-chain boundary

Gate: G6 DetectorTimeConstant.

Purpose:
- Establish the unique timing authority for source-v2 artifacts.
- Screen the current raw-state inventory for activity in short half-life
  intervals relevant to event-building.
- Preserve the WP05 limitation: full parent/daughter feeding is not complete
  until a tag-aware native Activator oracle is run.

Acceptance:
- All generated source cards that participate in v2/native probes use the same
  `DetectorTimeConstant`.
- Positive inventory in the 1 ns--5 us risk bins is zero, or a bounded timing
  scan is required.
- The gate emits exactly one timing authority or blocks.

Outputs:
- `06_time_constant/detector_time_constant_audit.json`
- `06_time_constant/static_lifetime_risk.csv`
- `06_time_constant/static_lifetime_risk_summary.json`
- `06_time_constant/timing_authority.json`
- `06_time_constant/timing_authority.md`
- `06_time_constant/summary.json`
- `06_time_constant/summary.md`
