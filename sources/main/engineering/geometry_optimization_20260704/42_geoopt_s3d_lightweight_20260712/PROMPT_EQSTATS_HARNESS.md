# S3d equal-stat e+/neutron prompt harness

Status: `PREFLIGHT_PASS_NO_TRANSPORT_LAUNCHED`

This is the matched dominant-background screening run against the retained S3c
e+/neutron production.  It is **not** the eight-family prompt authority needed
for the final Step05--08 paper closure.

## Frozen production definition

- Geometry: the validated 42_ S3d setup (uniform 30 mm BGO, no outer W2, Al3).
- Source authority: retained S3c full-sphere 20-bin cards from 32_.
- Source-card delta: only the `Geometry` directive and its
  `geometry_setup` comment are repointed to the S3d setup.
- Gamma normalization anchor: 10,000,000 events, flux
  `4.7996615777852 cm^-2 s^-1`; gamma itself is not transported by this subset.
- e+: 243,727 events per replica x 8 replicas.
- neutron: 963,066 events per replica x 8 replicas.
- Total: 16 independent jobs and 9,654,344 requested events.
- Source surface: R60 cm; prompt exposure anchor 184.220098 s.
- The source templates retain isotope settings.  The shared runner's
  `instant` mode intentionally removes `DecayMode ActivationBuildUp` from the
  materialized prompt job cards, exactly as in the retained S3c prompt run.
  Neutron delayed production is a separate audited chain.

## Safe preflight

```bash
python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_prompt_eqstats.py
```

This writes the three pinned source cards, the normalization/run manifests,
all 16 materialized job cards, and the preflight audit.  It does not invoke
Cosima.

## Exact production command

```bash
python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_prompt_eqstats.py --launch --allow-heavy-run --workers 12
```

The runner refuses production without both explicit launch flags.  It also
refuses to run if the validated geometry/overlap state, source hashes, shared
runner hash, job-card geometry, statistics, seeds, or output containment checks
are stale.

The Python entry point loads and validates the retained project environment
authority at
`engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/megalib_env.sh`
before starting the shared runner.  Its exported MEGAlib libraries and all
required Geant4 data directories are passed to the runner and inherited by
every Cosima worker; the caller does not need to source the script manually.

All production output is confined to:

`runs/geometry_optimization_20260704/s3d_lightweight_eqstats_prompt_eplus_n_20260712/`

## Resource planning

The event-matched retained S3c run measured 8,730.053 CPU-s, 4.345 GB of
compressed SIM data, and 5.601 GB including verbose logs.  S3d event
multiplicity can differ, so reserve at least 8 GB free disk for this subset.
The retained 16-worker run approached the host's roughly 11--12 GB RAM
envelope, so the production command uses 12 workers on the current host.
Reserve at least 20 GB before adding the atmospheric-511 screening and
downstream products.

## Evidence

- Source manifest:
  `config/prompt_eqstats_eplus_n/source_cards/source_migration_manifest.json`
- Package preflight:
  `data/s3d_prompt_eqstats_preflight.json`
- Run-local preflight:
  `runs/geometry_optimization_20260704/s3d_lightweight_eqstats_prompt_eplus_n_20260712/preflight_validation.json`
