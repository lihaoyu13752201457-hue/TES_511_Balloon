# S3d atmospheric-511 and focused-signal replay harnesses

Status: `PASS_DRY_RUN_READY_NO_PRODUCTION_LAUNCHED`

Both harnesses load and hash-pin the retained project MEGAlib environment,
require the validated S3d geometry/overlap authority, generate dated source
cards without overwriting differing files, and refuse production unless an
exact confirmation token is supplied.  The source cards are the only files in
the three new run directories at handoff.

## Atmospheric 511 keV

The S3d source is a geometry-local transform of the retained S3c-C0 3M source.
The 20 angular bins, all fluxes, S1 environment/model, physics lists,
`3,000,000` events, and seed `26070917` are unchanged.  The later selection is
frozen to W2 `[510.58, 511.42) keV`, summed active energy `<50 keV`, the
retained active-volume predicate, and the frozen side-Compton/FoV policy.

Dry-run/preflight (safe and idempotent):

```bash
python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_atm511_replay.py
```

Guarded production command (not run at handoff):

```bash
python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_atm511_replay.py --execute --confirm Atm511SidecarS3dO9_3M
```

Expected resource scale from C0 is about `1152 CPU s` (roughly 20 minutes on
one comparable core), `807 MB` compressed SIM plus `311 MB` log.  Reserve at
least `2 GB` free disk.

## Matched focused signal

No retained S3c-C0 transport exists for this focused-signal guardrail.  The
harness therefore prepares a fresh paired comparison: S3c-C0 and S3d use the
same retained EventList (`37194` zero-based sequential 511-keV rows; SHA-256
`ee538d20d818baab94a5c3ebe01392a3ae9f278a231aa5b8938cdf23870f62b5`),
`37194` triggers, seed `260616`, physics, hit discretization, and later
selection.  Only geometry, run label, and output prefix differ.

Dry-run/preflight (safe and idempotent):

```bash
python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_signal_replay.py
```

Guarded production command; by default it runs C0 then S3d and validates both
SIM headers plus `SE=ID=37194` (not run at handoff):

```bash
python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_signal_replay.py --execute --confirm MATCHED_S3C_C0_AND_S3D_O9_SIGNAL37194
```

Expected resource scale is `28--31 CPU s`, `23--24 MB` compressed SIM, and
about `8 MB` log per branch; the sequential pair should take about one minute
on one comparable core and less than `100 MB` additional disk.

## Audit products

- `data/s3d_atm511_replay_manifest.json`
- `data/s3d_signal_replay_manifest.json`
- `runs/geometry_optimization_20260704/s3d_o9_atm511_sidecar_3m_20260712/`
- `runs/geometry_optimization_20260704/s3c_c0_f10m_a1_signal_replay_37194_matched_20260712/`
- `runs/geometry_optimization_20260704/s3d_o9_f10m_a1_signal_replay_37194_20260712/`

The manifests mark atmospheric occupancy and both performance summaries as
pending transport, not zero.  Downstream analysis must write the contracted
catalog occupancy, W2/broad window counts/rates, and paired signal acceptance
before either replay contributes to a promotion claim.
