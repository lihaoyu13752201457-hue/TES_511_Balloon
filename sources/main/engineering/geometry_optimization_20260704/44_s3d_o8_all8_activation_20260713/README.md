# S3d-O8 all-eight-family activation completion

This dated package completes the activation scope that was absent from the
retained S3d-O8 campaign.  The retained package-43 geometry, source cards,
all-eight prompt run, and neutron-only delayed result are immutable provenance;
all new buildup, source, transport, response, and paper-facing products use new
dated paths.

## Production contract

- Geometry: retained S3d-O8, 40/30/10 mm graded BGO, no outer W.
- Prompt: reuse the audited 68-job all-eight-family transport from 2026-07-12.
- ActivationBuildUp: clean 68-job all-eight-family run (12 gamma splits and
  eight replicas for each non-gamma family).
- Normalization: gamma divided by 12; every non-gamma family divided by 8;
  exactly one positive TT record per job.
- Inventory: day 15, local NUBASE-2020 ground-state correction, `min-points=1`.
- Delayed transport: family-resolved exact-RPIP sources, M=50,000 and 1,000,000
  delayed events for every family with positive activity.  Families with no
  observed production in this finite buildup campaign remain explicit
  `PASS_ZERO_PRODUCTION` entries; this is not a physical-zero claim.
- Downstream closure is complete: Step05, the 420 eV response ensemble, and
  the family-by-nuclide 81-bin trajectory fold are bound to this campaign by
  file hashes and independent PASS validators.

## Commands

```bash
python3 code/run_s3d_o8_all8_activation.py prepare --workers 8
python3 code/run_s3d_o8_all8_activation.py run-buildup --workers 8 \
  --allow-heavy-run --confirm RUN_S3D_O8_ALL8_BUILDUP_20260713
python3 code/run_s3d_o8_all8_activation.py prepare-delay --source-workers 4 \
  --allow-heavy-run --confirm BUILD_S3D_O8_ALL8_FAMILY_DELAY_SOURCES_20260713
python3 code/run_s3d_o8_all8_activation.py run-delay --family-workers 3 \
  --allow-heavy-run --confirm RUN_S3D_O8_ALL8_FAMILY_DELAYED_1M_20260713
```

The independent multi-family Step05 postprocessor must first reproduce the
retained neutron-only result.  `components` and the result-producing stages
remain fail-closed until the activation campaign reaches its terminal PASS
state.

```bash
python3 code/run_s3d_o8_all8_step05.py regression --rebuild-cache
python3 code/run_s3d_o8_all8_step05.py preflight
python3 code/run_s3d_o8_all8_step05.py components
python3 code/run_s3d_o8_all8_step05.py all --workers 4 \
  --allow-postprocess --confirm RUN_S3D_O8_ALL8_STEP05_POSTPROCESS_20260713
```

The regression currently passes a fresh raw-SIM neutron parse, exact retained
parser/splice and broad/W2 Step05 cut-flow reproduction, plus a synthetic
two-positive-family unequal-TE test with cross-family local-ID reuse and a
zero-observed family.  Parser caches are fingerprinted by the SIM hash/size,
ADR and harness hashes, and active-veto predicate.  The new catalogue retains
lineage as `(incident family, source file, local ID)` and normalizes every
transported family with its own `1/TE`; zero-observed families receive no
fictitious transport exposure.

Per-family Garwood intervals cover delayed-transport counting for transported
families only.  They do not cover buildup-yield uncertainty, exact-position
M-sampling uncertainty, or an upper limit for a family with zero observed
production in the buildup campaign.

## Final status

- Activation campaign:
  `PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT`.
- Day-15 fixed activity: `36.4525153075 Bq` across all eight audited incident
  families.
- Positive-activity delayed transports: `alpha, eplus, gamma, muminus, muplus,
  n, p`; each uses an exact-position `M=50,000` source and `1,000,000` delayed
  events.
- `eminus`: `PASS_ZERO_PRODUCTION` in this finite buildup realization, with no
  fabricated delayed transport or transport exposure.
- Delayed components: `PASS_S3D_O8_ALL8_STEP05_DELAYED_COMPONENTS`.
- Final Step05: `PASS_S3D_O8_ALL8_ACTIVATION_STEP05_DAY15`.
- Response closure:
  `PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE`.
- Family/nuclide mission closure:
  `PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_CLOSURE`.

The terminal campaign authority is
`data/s3d_o8_all8_activation_campaign.json`.
