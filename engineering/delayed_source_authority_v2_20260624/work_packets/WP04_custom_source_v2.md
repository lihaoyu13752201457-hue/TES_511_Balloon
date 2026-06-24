# WP04 - custom delayed source v2

Gate: G4 Custom source v2.

Purpose:
- Build the state-aware delayed-source v2 authority from the G1 raw inventory
  and G2 RPIP point alignment.
- Preserve production tag, raw logical volume, ZA, excitation state, and
  production position in the transport input and sidecar ledger.
- Emit a native MEGAlib isotope-store activity file for the later G5 oracle.

Chosen implementation:
- Exact-position custom authority: weighted MEGAlib EventList.
- Native oracle input: MEGAlib isotope-store `VN/RP` activity file.
- Sampling mode: explicit all-RPIP-points, one EventList row per RPIP point,
  with per-row Bq weight in a sidecar ledger.

Acceptance:
- Total weighted source activity closes to the inventory at relative error
  `<= 1e-8`.
- Major keys with activity fraction `>= 1e-3` close at relative error
  `<= 1e-6`.
- Duplicate source names are zero.
- Positive non-ground activity unsupported by the exact-position EventList path
  is zero; otherwise this gate blocks into a hybrid/native stream.
- Round-trip parsing of the generated source files reconstructs the same
  per-key activity.

Outputs:
- `04_custom_source_v2/source_v2_eventlist.dat`
- `04_custom_source_v2/source_v2_event_weights.csv`
- `04_custom_source_v2/source_v2_eventlist.source`
- `04_custom_source_v2/source_v2_native_activity_store_total.dat`
- `04_custom_source_v2/source_v2_native_activity_store_by_tag/`
- `04_custom_source_v2/source_v2_key_closure.csv`
- `04_custom_source_v2/source_v2_manifest.json`
- `04_custom_source_v2/source_text_roundtrip.json`
- `04_custom_source_v2/source_name_audit.json`
- `04_custom_source_v2/sampling_audit.json`
- `04_custom_source_v2/summary.json`
- `04_custom_source_v2/summary.md`
