# M05 corrected-keV reanalysis entry

Status: `07_PAPER_REGISTRY_COMPLETE__PAPER_ASSET_REGENERATION_NEXT`

This directory is the single analysis entry for rebuilding the M05 results
from corrected-keV transport. It is a lightweight derived layer: raw SIM/DAT,
receipts, and batch ledgers stay in their original `runs/` directories.

## Current input selection

`analysis_inputs.json` selects the canonical batch0000--batch0007 and
continuation ledgers without re-counting credited prior events. The current
union contains:

| Mode | Jobs | Primary histories |
|---|---:|---:|
| instant | 530 | 7,684,156 |
| buildup | 446 | 6,092,936 |
| total | 976 | 13,777,092 |

Mass_model_511 contributes 6,888,549 histories and S3d-O8 contributes
6,888,543. The six-history difference is retained rather than altered.

The source profile is `unit_only_total_gamma`: its broadband gamma spectrum
already contains the annihilation bump, so this chain does not add a separate
mono-511 atmospheric source.

## Input check

From the repository root:

```bash
python3 -B \
  engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code/check_inputs.py
```

To refresh the compact audit used by downstream adapters:

```bash
python3 -B \
  engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code/check_inputs.py \
  --write
```

The check reads only JSON ledgers and selected receipts. It confirms the source
contract, terminal status, selection totals, geometry/mode/family boundaries,
positive TT, non-duplicated SIM selection, and exact active-veto volume lists.
It intentionally does not reopen SIM gzip files or recompute large-artifact
hashes.

## Prompt result (01 complete)

`outputs/01_prompt/` contains the compact position-preserving catalogs and
paper-facing prompt screening tables for all 530 instant jobs / 7,684,156
histories. The full scan used four worker processes and completed in 4,123.5 s.

With the retained 420 eV FWHM response, 0.3 keV pixel threshold, exact active
veto and retained Step05 selection, the measured results are:

| Geometry | 480--550 after veto+Step05 | W2 after veto+Step05 |
|---|---:|---:|
| Mass_model_511 | 20 events; 0.345273 cps | 7 events; 0.123419 cps |
| S3d-O8 | 8 events; 0.135372 cps | 2 events; 0.0338429 cps |

Rates are computed inside each geometry x family cell as `count/sum(TT)` and
then added across families. The event counts in the table are descriptive
sums across heterogeneous cells. This prompt-only table is retained as the
stage-01 screening view. The combined prompt+delayed result is published by
stage 04 below.

The compact catalogs are 5.1 MiB in total and retain TES hit energy/position,
exact shield energy, O8 plastic energy, and active-only occupancy counts. The
04 adapter consumes these explicit extensions instead of dropping them through
the historical compact helper.

## Activation result (02 complete)

`outputs/02_activation/` is a compact M05-facing view of the already complete
corrected BUILDUP and exact-position source preparation. It consumes 446
BUILDUP jobs / 6,092,936 histories without reopening the 33.6 GiB rich SIM
set. The retained normalization contains 97,247 RP records and 3,177.965553 s
of cell live time; zero-RP DAT live times remain in each denominator.

| Geometry | Known day-15 activity | Transported ground-state activity |
|---|---:|---:|
| Mass_model_511 | 482.117936 Bq | 482.117936 Bq |
| S3d-O8 | 1404.23088 Bq | 1404.13107 Bq |

Five NUBASE state rows remain unresolved and S3d-O8 has 0.0998093 Bq of
explicit non-ground-state holdout. These states are not silently collapsed.
Fifteen geometry-family cells have retained 50,000-point exact-position source
cards; Mass_model_511/muplus is the sole zero transport-source cell.

Inventory Bq is not by itself a detector-selected delayed background. Stage 03
now supplies the raw detector catalog; the shared response and final selection
belong to stage 04.

## Delayed result (03 raw catalog complete)

The retained p/n/alpha recovery contributes six corrected cells and the new
8-worker campaign contributes the remaining nine. The new campaign completed
2,250,000 triggers in 1,583.5 s wall time; together, stage 03 scans 15 positive
ground-state cells / 3,750,000 triggers. Mass_model_511/muplus remains an
explicit zero-source cell rather than a missing input.

The 8-process semantic scan completed in 232.7 s and found 18,675 TES-positive
events with 24,470 pixel hits. It keeps all 250,000 triggers in each positive
cell's normalization, including 275 records without `IA DECA`. Each event has
weight `transported day-15 activity / 250000`.

Parent nuclide and source volume are recovered from the sampled exact-position
table using the retained M04 Chebyshev nearest/second-nearest mapping rule;
`IA INIT` ZA remains separate transport evidence. The published source-mix
table compares the original 50,000 blocks, the stride-5 10,000 blocks, and the
realized 250,000 triggers. Across the 15 cells, the 50k-to-10k total-variation
range is 0--3.186% by volume and 0--6.190% by parent ZA. This sampling term is
kept separate from event-count uncertainty.

Stage 03 is deliberately response-neutral: it does not smear pixels or run
active veto/Step05. Stage 04 replays those operations once for prompt, delayed,
and focused signal under the same keyed response contract.

## Common response result (04 complete)

`outputs/04_common_response/` applies the same keyed 420 eV FWHM response,
0.3 keV measured-pixel threshold, exact active-volume policy, 50 keV nominal
veto, and retained Step05 selector to all three streams. The response pass used
8 processes over 34 compact catalogs. The focused-signal SIMs are reused at
the Be-window injection plane; no new signal transport was required.

| Geometry | Prompt W2 (cps) | Delayed day-15 W2 (cps) | Total W2 (cps) | Signal W2 Aeff (cm2) |
|---|---:|---:|---:|---:|
| Mass_model_511 | 0.123419 | 0.107854 | 0.231273 | 15.11676 |
| S3d-O8 | 0.0338429 | 0.0544798 | 0.0883227 | 15.04170 |

Background MC errors combine event weights in quadrature. Signal acceptance,
multiplicity, and occupancy use fixed-trial binomial errors. The 70/80 keV
alternatives are kept in `veto_threshold_scan.csv`; the common tables use the
nominal 50 keV policy. Signal Aeff is conditional on the retained post-Be
EventList and is not a full-envelope BPE/plastic transmission measurement.

## Matched day-15 comparison (05 complete)

`outputs/05_matched_comparison/` publishes the Mass reference budget and the
matched Mass/S3d family, parent-nuclide, material, and volume tables. Zero
prompt-family and material survivors remain explicit rows with upper-limit or
zero-survivor flags.

For W2 after the common response, the central O8/Mass background ratio is
0.38190 (61.81% lower), while the selected signal-Aeff ratio is 0.99503
(0.50% lower). The detector-plane diagnostic `Aeff/sqrt(B)` ratio is 1.610.
These are day-15 central diagnostics, not mission sensitivity or geometry
promotion. Prompt support remains only 7 versus 2 W2 MC events; delayed
source-position subsampling, the 0.0998093 Bq O8 excited-state holdout, optics
systematics, and time evolution remain separate.

## Mission result (06 complete)

`outputs/06_mission/` uses the corrected stage-02 production rates and stage-04
response. The 81 trajectory-node family ratios were rebuilt with eight workers
and a proper trapezoidal energy integral in each equal-mu PARMA bin. Each
parent inventory starts at zero on mission day 0 and is advanced to day 20;
this scenario excludes pre-flight/ground activation, and there is no forced
day-15 reanchoring. The activity update uses the exact decay convolution for
linearly varying production between adjacent trajectory nodes. Signal uses the fixed-45-degree slant
transmission. The corrected broadband gamma already contains the annihilation
bump, so no separate atmospheric mono-511 background is added.

| Geometry | Z20 central | Z20 conditional proxy | T3 central | F3(20 d) central | F3 proxy |
|---|---:|---:|---:|---:|---:|
| Mass_model_511 | 2.7094 | 1.3343 | not reached (24.52 d sqrt-time extrap.) | 1.1073e-4 | 2.2484e-4 |
| S3d-O8 | 4.3329 | 1.4634 | 9.368 d | 6.9238e-5 | 2.0501e-4 |

The forward trajectory-node day-15 backgrounds are 0.225151 cps (Mass) and
0.0862124 cps (S3d-O8), rather than the constant-environment stage-04
references 0.231273 and 0.0883227 cps. This difference is now a prediction,
not an artificial closure condition.

Fluxes are top-of-atmosphere photons cm^-2 s^-1. The conditional proxy combines
componentwise prompt Garwood upper limits, a delayed parent-mixture-scaled
upper proxy, and the focused-signal Clopper--Pearson lower endpoint; it is not
a joint 95% interval. Neither geometry reaches 5 sigma within 20 days, and
neither conditional proxy reaches 3 sigma.

This is an analytic family-scalar mission scenario, not corrected multipoint
transport authority. The PARMA driver returns W=114.6 for the retained date,
whereas the corrected source contract records W=118.3; only driver-internal
ratios to its 34N, 100E, 38 km reference are used. The scalar holds the
within-family energy spectrum, angular distribution, detector response, and
activation yield fixed across trajectory bins. Prompt W2 statistics (7 versus 2), source-position
sampling, the excited-state holdout, optics/visibility, and the synthetic
trajectory remain explicit limitations. Final geometry promotion is deferred.

## Reuse contract

Existing analysis machinery is reused with paths supplied by
`analysis_inputs.json`; this package contains only thin adapters and the small
delayed parent-lineage join adapted from the retained M04 mapping method:

- corrected BUILDUP catalog:
  `m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/build_corrected_buildup_catalog.py`;
- state-aware exact-position delayed preparation:
  `m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/prepare_state_aware_delayed_phase02.py`;
- keyed TES energy response:
  `seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py`;
- retained Compton/FoV selection:
  `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py`;
- existing family/nuclide mission fold and Step08 sensitivity builders.

Historical runners that still bind `cosima_spectra_dp_2602units` must not be
executed directly.

## M05 stage order

Outputs are created only when a stage is run:

1. `00_input_audit`: the current JSON selection and exposure summary;
2. `01_prompt`: common Mass/S3d prompt response and veto cutflow;
3. `02_activation`: BUILDUP production and day-15 inventory;
4. `03_delayed`: formal delayed transport and response inputs;
5. `04_common_response`: signal, prompt, and delayed common selection;
6. `05_matched_comparison`: Mass reference and matched S3d comparison;
7. `06_mission`: analytic family-scalar time fold, significance, and flux-threshold scenario;
8. `07_paper_registry`: M05 table/figure/claim number registry.

The corrected detector-plane results and analytic mission scenario are
complete. Stage 07 exposes 52 paper-number keys and maps 18 M05 figures,
tables, and claims to their current sources and readiness states. Final
geometry promotion remains blocked by the stated statistical/systematic
boundaries. Historical batch0007 screening tables are not substituted for the
stage-03/04 common-response products.

## Next action

Regenerate the paper-facing tables and figures listed READY in
`outputs/07_paper_registry/manuscript_object_registry.csv`, then revise the
English and Chinese M05 Methods/Results as a pair. No detector transport,
common response, or mission fold should be rerun for that step.
