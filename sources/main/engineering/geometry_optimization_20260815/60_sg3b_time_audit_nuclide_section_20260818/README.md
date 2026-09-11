# SG3B receipt-time audit and activation-nuclide side section

This non-overwriting package audits the SG3B INSTANT and delayed normalization and adds an
annotated activation-origin side section.  It reuses package 59's compact selected-event lineage,
route reconstruction, geometry mesh adapter, and SG3B geometry overlays.

Run:

```bash
python3 code/build_audit_and_section.py
```

The script reads only plans/receipts, small source cards, compact derived lineage/routes, the
activation manifest, and geometry mesh products.  It does not open or hash SIM payloads, start
transport, rerun detector response, or modify the paper.

Machine-readable results and figures are under `outputs/`.
