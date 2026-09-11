# Corrected BUILDUP catalog adapter

`build_corrected_buildup_catalog.py` prepares the read-only production
inventory input for delayed phase02. It never launches transport and never
opens a SIM payload. It accepts only corrected-keV canonical BUILDUP
authorities: batch0000/1/4/5, batch0006 recovery0008 plus continuation0005,
and batch0007 only after its complete final PASS bundle is published.

From the repository root, the no-write readiness check is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/build_corrected_buildup_catalog.py \
  --check
```

The in-memory zero-RP/deduplication check is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/build_corrected_buildup_catalog.py \
  --self-test
```

After batch0007 publishes
`PASS__BATCH0007_SUPPLEMENTAL_TRANSPORT_COMPLETE`, publish once with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/build_corrected_buildup_catalog.py \
  --publish
```

Publication is an atomic, write-once `catalog_v1/` directory below
`runs/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/`.
The compatibility view `corrected_buildup_catalog.json` is a relative symlink
to `catalog_v1/catalog.json`. Existing, different canonical bytes or a changed
symlink target fail closed.

## Authority boundary

The catalog supports corrected-keV isotope-production normalization only.
`production_rate_s-1` means `sum(RP)/sum(TT)` inside one
geometry/family/BUILDUP cell; every zero-RP DAT contributes its TT. It is not
an activity until the activation/decay timeline is applied. DAT records are
volume/isotope-state aggregates. Exact production positions remain in the
declared rich-SIM `CC IP RP` records and are not materialized by this adapter.
The outputs are not delayed-decay transport, detector response, mission
sensitivity, final paper-rate closure, or geometry-promotion authority.

