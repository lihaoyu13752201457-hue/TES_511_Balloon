# Batch0007 M05 analysis adapters

These readers are append-only analysis companions for the corrected-keV
batch0007 campaign. They do not launch transport, change sources, geometry,
physics, CUTs or native detector thresholds, and never read a live
`.attempt*.partial` directory.

Run all commands from `/home/ubuntu/TES_511_Balloon` with bytecode disabled so
the read-only checks do not create `__pycache__` files.

## Prompt and BUILDUP top-up reader

While the batch0007 top-up is running, perform the no-SIM/no-DAT check:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/analysis/code/analyze_batch0007_prompt_activation.py \
  --check
```

Only after `final_validation.json`, `final_ledger.json` and
`final_umbrella.json` all publish
`PASS__BATCH0007_SUPPLEMENTAL_TRANSPORT_COMPLETE`, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/analysis/code/analyze_batch0007_prompt_activation.py \
  --run
```

The write-once output is
`runs/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_v1/analysis_prompt_activation/`.
It contains prompt e− TES pixel sums, the M05 response and 0.3-keV measured
pixel cut, W2 and exact-block 50/70/80-keV veto flags, a clearly labelled
single-pixel topology proxy, and BUILDUP e−/μ− TT/RP/zero-RP and
position/isotope-state coverage.

## Phase02 delayed detector-response adapter

The static synthetic self-test and terminal readiness check do not open any
SIM:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/analysis/code/analyze_phase02_delayed_response.py \
  --self-test

PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/analysis/code/analyze_phase02_delayed_response.py \
  --check
```

The adapter is intentionally gated on the atomically published canonical
12-job subset summary
`delayed_phase02/state_aware_exactpos_v1/transport_summary.partial_59ff7d29ca6e.json`.
Here `partial_59ff7d29ca6e` is the phase02 controller's semantic label for a
completed, deliberately bounded subset of the prepared plan; it is not a live
`.partial` staging file. The reader additionally requires every embedded
receipt to be PASS, every SIM to reside below final `attempt01`, and every
selected `.attempt01.partial` directory to be absent.

After that check reports
`PASS__DELAYED_RESPONSE_READER_TERMINAL_GATE_READY`, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/analysis/code/analyze_phase02_delayed_response.py \
  --run
```

The write-once output is
`runs/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_v1/analysis_delayed_response/`.
It applies per-pixel 0.420-keV FWHM response with seed 26071301, removes
measured pixels below 0.3 keV, constructs W2 and exact active-veto flags, and
runs the retained Step05 side-entry Compton/FoV baseline with
`reject_policy=keep`. Rates use each source manifest's included ground-state
day-15 activity divided by one million triggers.

## Exact active-block rule

- `Mass_model_511`: the exact 24 CsI volume names declared in the readers.
- `S3d_O8`: exactly three BGO and three plastic detector volumes.

The historical broad `BGO`/`ACTIVE_SHIELD` substring predicate must not be used
for O8 because it can include mechanical names.

## Authority boundary

These adapters support corrected-keV analysis compatibility and partial
screening only. They do not combine historical factor-1000 rates. The phase02
delayed result covers only paired p, n, alpha, gamma, e− and μ− ground-state
transport. It excludes e+/μ+ jobs, every explicit excited-state holdout,
unknown activity states, complete prompt+delayed response, mission
sensitivity, final paper-rate closure, final structure ranking and geometry
promotion.
