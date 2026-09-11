# O8 Screening Harness

Status: `SIGNAL_GATE_PASS_PROMPT_ATM_PENDING_20260712`

This harness freezes the matched screening comparison between the retained
heavy control and the O8 fallback geometry.  It does not claim the complete
eight-family prompt, activation, delayed, or mission-fold closure.

## Preregistered gates

- Focused signal: central matched final-window acceptance loss `<= 2%`.
- Dominant background subset: final-window `e+ + neutron + atmospheric-511`
  rate `<= 0.0052 cps`.
- Primary line window: `510.58 <= E_TES < 511.42 keV`.
- Active-veto threshold: summed matched active energy `< 50 keV`.
- Side-entry policy: retained `side_keep_from_hits(..., reject_policy="keep")`.
- Missing production remains `PENDING`; no absent count or rate is replaced by
  zero.

## Equal-statistics prompt e+ and neutron

The prompt preparer copies the retained heavy-control gamma/e+/neutron source
cards and allows only geometry-path metadata to change.  Gamma is the 10M
normalization anchor; only e+ and neutron are transported.  The production
contract is eight replicas of `243,727` e+ and eight replicas of `963,066`
neutrons (`9,654,344` requested events total), with the exact retained 16-seed
sequence checked against the completed O9 run.

Dry-run/preflight:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_prompt_eqstats.py --workers 12
```

Guarded production:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_prompt_eqstats.py --launch --allow-heavy-run --confirm O8_EQSTATS_EPLUS_N_16JOBS_9654344 --workers 12
```

Output directory:
`runs/geometry_optimization_20260704/s3d_o8_eqstats_prompt_eplus_n_20260712/`.

The launched job-card authority has:

- `run_manifest.csv` SHA-256
  `c8e9193475afd5f9d53ba71484672efe58d2f9a19914bb023247b11132034564`;
- `normalization.json` SHA-256
  `50bdc59ccb8af3c04a61e5bf1a4dd3e5c9ca7082e973cc9a88d4d3dc4bb07a1d`;
- `16/16` source cards canonical-equal to the completed O9 cards after
  normalizing geometry and output metadata, with 16 unique exact seeds.

## Matched focused signal

The completed heavy-control 37,194-trigger branch is reused without rerunning.
The O8 branch uses the same retained EventList (SHA-256
`ee538d20d818baab94a5c3ebe01392a3ae9f278a231aa5b8938cdf23870f62b5`),
the same 37,194 triggers and physics settings, and seed `260616` both in the
source and as an explicit Cosima `-s 260616` argument.

Dry-run:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/prepare_o8_signal_replay.py
```

Guarded production:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/prepare_o8_signal_replay.py --execute --confirm O8_MATCHED_SIGNAL37194_SEED260616
```

Read-only completed-output audit:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/prepare_o8_signal_replay.py --audit-existing
```

Output directory:
`runs/geometry_optimization_20260704/s3d_o8_f10m_a1_signal_replay_37194_20260712/`.

The completed O8 source SHA-256 is
`d46bae01bc46ed0a8a8b7da50477e34ac09d2750dfe3384ad93f07a51dc412f5`.
The full readable SIM audit observes the correct O8 geometry, seed `260616`,
and `SE = ID = 37,194`.

## Atmospheric-511 sidecar

The 3M atmospheric run is prepared by `prepare_o8_atm511_replay.py` with seed
`26070917`.  The screening analyzer requires the completed log observation
time and independently scans the full readable SIM stream to observe
`SE = ID = 3,000,000`; manifest/requested counts are not substituted.  It uses
the same 50 keV veto and side/FoV policy and records the IA INIT entry-surface
proxy for every final-window survivor in both the heavy-control and O8 branches.

Dry-run and guarded production:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/prepare_o8_atm511_replay.py
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/prepare_o8_atm511_replay.py --execute --confirm Atm511SidecarS3dO8_3M
```

Output directory:
`runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/`.

## Incremental screening analysis

Self-test and read-only readiness check:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/build_o8_screening_analysis.py --self-test
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/build_o8_screening_analysis.py --status-only
```

Incremental/full analysis:

```bash
python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/build_o8_screening_analysis.py
```

The analyzer evaluates each gate as soon as its own inputs are complete.  A
valid failed physics gate is distinct from an audit failure.  Current matched
signal result:

- heavy-control final acceptance: `29,703 / 37,194`;
- O8 final acceptance: `29,598 / 37,194`;
- O8/control ratio: `0.9964650035`;
- central relative loss: `0.35349965%` (`PASS`, limit `2%`);
- paired table: both pass `24,412`, control-only `5,291`, O8-only `5,186`,
  neither `2,305` (closes exactly to `37,194`).

Prompt and atmospheric sections remain explicitly `PENDING` until their
completed authorities appear.  The dominant `e+/n/atm` gate is therefore also
`PENDING`, with no zero substitution.

## Static validation

The four new Python tools pass `python3 -m py_compile`.  Their self-tests check
the exact 16-job statistics/seed contract, the 37,194-row EventList authority,
the `2%` and `0.0052 cps` gates, zero-count Garwood behavior, and side/bottom/top
entry-surface classification.
