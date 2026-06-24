# WP05 - native activation oracle

Gate: G5 Native activation.

Purpose:
- Compare the generated source-v2 inventory against the MEGAlib native
  `ActivationSources` isotope-store representation.
- Audit the installed Activator merge semantics before any raw `.dat` native
  parent-feeding calculation.
- Run bounded native syntax/probe tests only under the engineering directory.

Boundary:
- A single all-tag native Activator is invalid because the installed Activator
  merge divides by the total loaded `TT`.
- The executable oracle therefore runs one Activator per production tag and
  then compares the merged tag outputs to the direct source-v2 inventory.
- This gate still does not provide selected-rate promotion; transport and
  Step05 ingestion remain later gates.

Outputs:
- `05_native_activation/native_store_vs_custom_inventory.json`
- `05_native_activation/native_store_vs_custom_inventory.csv`
- `05_native_activation/native_activator_merge_audit.md`
- `05_native_activation/native_activator_merge_audit.json`
- `05_native_activation/native_activation_sources_probe.source`
- `05_native_activation/native_activation_sources_probe.log`
- `05_native_activation/synthetic_activator.source`
- `05_native_activation/synthetic_activator_counts.dat`
- `05_native_activation/synthetic_activator.log`
- `05_native_activation/summary.json`
- `05_native_activation/summary.md`

Acceptance:
- PASS only if a tag-aware native raw activator oracle or an equivalent native
  inventory comparison is complete.
- A serialization-only match is `WARN_NATIVE_ORACLE_LIMITED`, not final rate
  authority.
