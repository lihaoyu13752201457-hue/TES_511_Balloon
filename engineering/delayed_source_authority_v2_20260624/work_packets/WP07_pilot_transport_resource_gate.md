# WP07 - pilot transport resource gate

Gate: G7 Pilot transport.

Purpose:
- Identify the exact legacy, v2 custom, and native-volume source inputs needed
  for delayed-source v2 pilot transport.
- Prevent accidental compute-heavy transport after source construction.
- Block rate promotion until explicit resource approval and native-oracle
  limitations are handled.

Default status:
- `BLOCKED_RESOURCE_APPROVAL`

Reason:
- Pilot transport compares multiple delayed-source models and would create new
  Cosima simulation outputs.
- The v2 exact-position EventList contains more than 250k weighted rows.
- G5 is `WARN_NATIVE_ORACLE_LIMITED`, so transport can be diagnostic but cannot
  promote a final delayed-rate authority without an accepted native/decay-chain
  boundary.

Outputs:
- `07_transport/pilot_transport_resource_plan.json`
- `07_transport/pilot_transport_resource_plan.md`
- `07_transport/summary.json`
- `07_transport/summary.md`
