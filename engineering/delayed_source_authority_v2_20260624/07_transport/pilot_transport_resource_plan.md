# Pilot Transport Resource Plan

status: `BLOCKED_RESOURCE_APPROVAL`

No pilot transport was launched.

Blocking reasons:
- Pilot transport would create new Cosima simulation outputs.
- The v2 exact-position EventList contains 254704 weighted rows.
- G5 native oracle status is `EXPLAINED_MODEL_DIFFERENCE`; selected-rate promotion still requires transport and Step05 ingestion.

Candidate inputs:
- legacy L0 source: `runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source`
- v2 source: `engineering/delayed_source_authority_v2_20260624/04_custom_source_v2/source_v2_eventlist.source`
- native source: `engineering/delayed_source_authority_v2_20260624/05_native_activation/native_activation_sources_probe.source`
- prepared pilot input manifest: `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_input_manifest.json`

Recommended bounded pilot after approval:
- 1000 triggers legacy L0
- deterministic 1000-row v2 weighted subset or equivalent stratified slice
- 1000 triggers native volume-level source
- existing Step05 selection only; no geometry, veto, W2, prompt, or signal changes
