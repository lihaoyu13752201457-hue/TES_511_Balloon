# SG3B simulation execution handoff — 2026-08-17

This is the execution addendum to `NEXT_SESSION_REVIEW_OUTLINE.md`.  It records
the SG3B transport products produced or consolidated during the 2026-08-17
session.  Controller states, canonical receipts, generated plans, source
manifests, and seed registries remain the machine authority.

## 1. Read-only takeover contract

The next session must first read, in order:

1. repository `AGENTS.md`;
2. `NEXT_SESSION_REVIEW_OUTLINE.md`;
3. this file;
4. the relevant `config.json`, `generated/job_plan.json`,
   `generated/source_manifest.json`, `generated/seed_registry.json`, and
   `run/controller_state.json` under the paths below;
5. canonical receipt JSON files only when a count or identity needs checking.

Initial review must not scan or hash the large SIM payloads.  Do not start a
new Cosima run, delete data, merge unlike modes/families, run detector response,
or replace paper numbers until the user explicitly requests that next action.

## 2. Geometry identity

All accepted products in this addendum bind to:

`/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup`

| File | SHA-256 |
|---|---|
| `DEMO2_DR_v3p5_SG3B.geo.setup` | `49324ca4baebd8e6323b4a478b168dff8798e2bd7f0d0775e2f179769aad0469` |
| `DEMO2_DR_v3p5_SG3B.geo` | `5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9` |
| `DEMO2_DR_v3p5_SG3B.det` | `0a4e6cb6b17949d5593f46faae87d80b383f5c9c08cb5b3240b91131e8515e21` |

The setup declares `Name DEMO2_DR_v3p5_SG3B`, includes the matching `.geo`
and `.det`, and uses `SurroundingSphere 60 5 0 9 60`.  Do not silently replace
this geometry with S3c, S3d-O8, or another SG3 revision.

## 3. Storage summary

Authoritative storage root:

`/mnt/data/TES_Balloon_511_data/SG3/`

Snapshot disk usage was 86,778,629,225 bytes (about 80.82 GiB), including a
small superseded failed trial.  No product in this directory is authorized for
deletion by this handoff.

| Directory | State | PASS jobs | Accepted events/triggers | SIM bytes from receipts | Artifact bytes from receipts | Filesystem bytes |
|---|---:|---:|---:|---:|---:|---:|
| `sg3b_plan1_background_v1` | controller `FAILED`; 20 PASS jobs retained | 20 | 2,294,737 | 17,386,275,563 | 17,718,679,620 | 23,244,004,184 |
| `sg3b_plan1_background_extra2x_v1` | complete retained add-on | 21 | 4,592,370 | 36,601,088,757 | 37,272,240,258 | 48,928,718,351 |
| `sg3b_m05_delayed_1m_sharded_v2` | `COMPLETE` | 33 | 8,000,000 | 10,829,661,552 | 12,447,984,679 | 13,306,420,015 |
| `sg3b_parma511_sidecar_3m_v1` | `COMPLETE` | 13 | 3,000,000 | 809,148,379 | 1,102,889,363 | 1,103,299,593 |
| `sg3b_m05_delayed_1m_v1` | superseded failed controller trial | 0 | 0 accepted | 0 | 0 | 196,187,082 |

Accepted total: **87 PASS receipts and 17,887,107 transport units**.  This is a
bookkeeping sum only: atmospheric primary histories, delayed decay triggers,
and mono-line photons have different physical normalization and must not be
treated as one exposure or pooled event population.

## 4. Corrected-keV prompt and BUILDUP transport

The retained initial batch and independent extra-2x add-on contain 41 PASS
receipts and 6,887,107 accepted primaries in total:

| Mode | Initial batch | Extra-2x add-on | Combined |
|---|---:|---:|---:|
| INSTANT | 1,280,693 | 2,561,386 | 3,842,079 |
| BUILDUP | 1,014,044 | 2,030,984 | 3,045,028 |
| Total | 2,294,737 | 4,592,370 | 6,887,107 |

Paths:

- `/mnt/data/TES_Balloon_511_data/SG3/sg3b_plan1_background_v1/`
- `/mnt/data/TES_Balloon_511_data/SG3/sg3b_plan1_background_extra2x_v1/`

The early executor layout keeps the source-plan authorities in the retained
executor worktree rather than beside the transferred SIM payloads:

- initial config and plan root:
  `/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/`;
- extra-2x generated plan root:
  `/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/generated/sg3b_plan1_extra2x_v1/`;
- the transferred data directories keep their canonical receipts and root-level
  `controller_state.json` files.

The initial controller planned 21 jobs but ended `FAILED` at 20/21 because
`sg3b_buildup_alpha_shard0001` (1,448 histories) exhausted its attempts without
a canonical PASS receipt.  The other 20 jobs are PASS and form the retained
initial accepted batch.  The extra-2x controller is `COMPLETE` at 21/21 and has
one 2,896-event alpha BUILDUP job.  Therefore the accepted initial-plus-extra
total excludes the missing 1,448 histories.  Preserve the exact receipt-level
family and mode identities.  Do not infer a perfectly uniform three-times
exposure for every cell, and do not pool INSTANT with BUILDUP.

All retained source cards use the corrected-keV package.  Legacy
`cosima_spectra_dp_2602units` references remain forbidden.  The accepted
primaries are transport counts, not TES survivors or physical rates.

## 5. M05 day-15 exact-position delayed transport

Canonical root:

`/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_sharded_v2/`

Controller state:

- profile: `SG3B_M05_DAY15_DELAYED_1M_SHARDED_20260817_V2`;
- status: `COMPLETE`;
- 33/33 jobs, zero pending, zero active, no controller error;
- 8,000,000 triggers total;
- each incident family (`p, n, alpha, gamma, eminus, eplus, muminus, muplus`)
  contributes exactly 1,000,000 triggers;
- proton uses a 50,000-trigger production canary plus three 250,000 shards and
  one 200,000 shard; every other family uses four 250,000 shards;
- 33 fresh transport seeds are unique and were checked against 602 previously
  occupied project seeds.

This is M05-style day-15 exact-production-position sampling.  Families remain
separate because their incident normalization, activation inventory, per-family
TT division, and lineage differ.  A plausible source card is not sufficient
authority: later rate work must preserve NUBASE ground-state correction,
per-family TT guards, source/inventory provenance, and the receipt-bound
geometry/seed evidence.

The earlier directory
`/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_v1/` is a superseded
unsharded controller trial.  It ended with
`canary stopped by resource guard: controller_stop_requested`, has no PASS
receipts, and contributes zero accepted events.  This was a controller/resource
execution failure, not evidence of a physics failure; do not mix its partial
files with v2.

## 6. PARMA atmospheric mono-511 transport

Canonical root:

`/mnt/data/TES_Balloon_511_data/SG3/sg3b_parma511_sidecar_3m_v1/`

Controller state:

- profile: `SG3B_PARMA511_MONO_3M_80BIN_20260817_V1`;
- status: `COMPLETE`;
- 13/13 PASS jobs, zero pending, zero active, no controller error;
- 3,000,000 mono-line photons total;
- 50,000-event production canary, eleven 250,000-event shards, and one
  200,000-event shard;
- 13 fresh seeds, checked against 695 occupied project and prior O8 PARMA511
  seeds;
- line energy: 510.99895 keV;
- physical angular model: 80 equal-mu bins, 40 down-going and 40 up-going;
- retained full-sphere line flux: 0.16651547160226118 ph cm^-2 s^-1.

This run is a **standalone line-only geometry-response sidecar**.  It does not
contain the broadband continuum.  The repaired `unit_only_total_gamma` source
already contains a broad-bin annihilation feature.  Therefore the mono-line
transport must not be added directly to broadband gamma results unless a
separate flux-closed de-duplication and recomposition contract is constructed
and validated.

Preparation/reuse code is retained at:

`engineering/geometry_optimization_20260815/57_sg3b_parma511_sidecar_20260817/`

## 7. Executor and resource policy

The runs reused the guarded executor and receipt-only dashboard at:

`/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/`

Final delayed and PARMA configs use eight workers, 1.5 GiB launch/runtime
`MemAvailable` floors, a 1 GiB runtime swap floor, and PSI threshold 100.  The
controllers were kept in tmux so GUI-terminal closure could not terminate the
transport.  These settings describe the completed run; they are not blanket
authorization for future campaigns.

## 8. What remains scientifically open

Raw transport completion does **not** establish paper-ready SG3B background
rates or a geometry promotion.  The next scientific stage still requires:

1. compact/event parsing with receipt and source provenance;
2. one common detector-response configuration for signal, INSTANT, delayed,
   and any permitted line-module analysis;
3. actual BGO/plastic veto mapping for SG3B volumes;
4. Step05/Compton/FoV closure and W2 selection;
5. per-family primary normalization and delayed inventory/TT normalization;
6. a flux-closed decision on broadband gamma versus the mono-511 module;
7. uncertainty and sparse-survivor reporting;
8. matched comparison to the retained Mass_model_511 and S3d-O8 authorities.

2026-08-18 update: after explicit user authorization, Section 9 closes items
1, 3, 4, 5, and the finite-count part of item 7 for the SG3B background chain.
The fresh SG3B signal half of item 2, the mono/broadband recomposition decision
in item 6, and matched promotion comparison in item 8 remain open.  Package 62
background cps and its conditional-proxy sensitivity may therefore be reported
with the Section 9 boundaries; a final SG3B sensitivity gain or promotion claim
may not.

## 9. 2026-08-18 mature common-Poisson post-processing update

The user subsequently authorized SG3B detector post-processing with the
retained M05/Step05 common-time method.  The non-overwriting result package is:

`engineering/geometry_optimization_20260815/62_sg3b_mature_poisson_timeline_20260818/`

This update records the SG3B background-response quantities explicitly closed
below.  It does not authorize paper edits or turn the conditional signal proxy
into an SG3B signal authority.

### 9.1 Selected inputs and compact-catalog closure

The event catalog streamed the 55 accepted background jobs selected by the
canonical receipts:

- 22 INSTANT jobs / 3,842,079 prompt primaries;
- 33 canonical delayed-v2 jobs / 8,000,000 triggers;
- 39,796,967,065 compressed SIM bytes in one semantic pass;
- no Cosima transport, no large-SIM hash, no BUILDUP-as-prompt mixing, no
  superseded delayed-v1 event, and no PARMA mono-511 event.

The resulting catalog contains 8,505,399 detector-positive event templates,
66,870 raw TES pixel deposits, and 1,807 `(stream, family, parent-ZA)` rate
categories.  Its direct detector response closes to package 58 over every
stream/family/stage/window row with maximum absolute rate difference
`4.440892098500626e-16 cps`.

Machine authorities:

- `outputs/01_event_catalog/summary.json`;
- `outputs/01_event_catalog/category_registry.json`;
- `outputs/01_event_catalog/direct_cutflow_closure.csv`;
- `outputs/02_mature_timeline/summary.json`;
- `outputs/02_mature_timeline/anchor_timeline_rates.csv`;
- `outputs/02_mature_timeline/mission_mature_flux_threshold.csv`.

The repeated human-readable job names in the two prompt batches are not unique
identifiers.  Catalog closure uses the composite receipt identity
`(stream, family, batch_id, job_id)`.

### 9.2 Normalization actually used

For prompt family `f`, every selected event has weight

`w_prompt,f = 1 / sum_j(TT_f,j)`,

where the sum includes all accepted INSTANT receipts in the initial and
extra-2x batches.  Thus the added transport statistics enlarge `sum(TT)`; they
do not multiply the physical rate.  The accepted values are:

| family | accepted INSTANT events | sum(TT) (s) |
|---|---:|---:|
| p | 25,449 | 20.0476 |
| n | 232,992 | 44.6213 |
| alpha | 5,958 | 45.7723 |
| gamma | 3,207,738 | 59.10547 |
| eminus | 295,341 | 131.2517 |
| eplus | 60,186 | 45.8131 |
| muminus | 10,443 | 188.6587 |
| muplus | 3,972 | 61.5173 |

For delayed family `f`, its shards sum to exactly 1,000,000 triggers and the
day-15 event weight is `A_f(15)/1,000,000`.  The day-15 transported ground-state
activities are 724.2735643, 330.0210223, 287.5411356, 6.59231051,
0.667877327, 2.953695927, 0.247887655, and `1.260430775e-9 Bq` for
`p, n, alpha, gamma, eminus, eplus, muminus, muplus`, respectively.  Mission
time dependence retains parent ZA and applies the exact inventory convolution
`A_f,ZA(t)/A_f,ZA(15)`.

Parent ZA is recovered from the retained exact-production-position table.
`IA INIT` ZA remains a separate diagnostic and is not required to equal that
parent label.  The compact scan reproduces package 58's per-job mismatch counts
and maximum position-match distances; it does not substitute IA ZA for the
exact-position lineage.

### 9.3 Mature common-time method — retained project definition

The governing implementations are:

- `old/code/tools/make_complete_day15_report_ADR.py`;
- `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py`;
- the SG3B migration in package 62 `code/run_mature_timeline.py`.

For independent stream/category rates `R_i`, the retained construction is

1. draw `N_i ~ Poisson(R_i T)`, draw its arrival times uniformly on `[0,T]`,
   then merge and sort all streams;
2. equivalently, draw chronological inter-arrival gaps
   `Delta t ~ Exponential(sum_i R_i)` and assign each mark with probability
   `R_i/sum_i R_i`.

Package 62 uses the second, memory-bounded construction; it is the same marked
Poisson process as the first.  Events are grouped transitively whenever each
adjacent gap is no larger than `tau = 1 microsecond`.  This is not a per-event
one-sided live-factor cut.

Within each time group, raw TES deposits are combined by pixel, plastic energy
is summed, and BGO energy is summed.  The retained TES response is 0.42 keV
FWHM per pixel with a 0.3 keV post-noise pixel threshold.  A group then passes,
in order, only if:

1. plastic positron-veto energy is strictly below 50 keV;
2. BGO active-scintillator energy is strictly below 50 keV;
3. both active vetoes pass;
4. the retained Step05 side-entry Compton/FoV trajectory rule passes.

Vetoes are therefore applied after the streams have been placed on one common
time axis and after group energies have been summed.  Package 58's analytic
`exp[-R(t) tau]` result is retained only as the approximation being tested, not
as the implementation of this replay.

### 9.4 Replay statistics and result

Five mission anchors at days 0, 5, 10, 15, and 20 were replayed for 20,000 s
each with seed 2026081801.  They contain 2,115,936,204 sampled event instances,
2,071,605,984 time groups, 43,400,733 multi-event groups, and 622,951
multi-event groups with raw TES energy.  Ten million conditional signal probes
were used across the five anchors.

| day | detector-positive rate (cps) | final W2 counts / 20,000 s | final W2 rate (cps) | conditional signal accidental survival |
|---:|---:|---:|---:|---:|
| 0 | 20,110.72184 | 293 | 0.01465 | 0.969368 |
| 5 | 21,296.31257 | 1,017 | 0.05085 | 0.967324 |
| 10 | 21,603.10917 | 1,048 | 0.05240 | 0.967052 |
| 15 | 21,459.21204 | 1,042 | 0.05210 | 0.967069 |
| 20 | 21,324.23497 | 1,023 | 0.05115 | 0.967283 |

At day 15, the mature W2 rates through the stages are 6.20405 cps pre-veto,
1.5114 cps after the plastic veto, 0.05855 cps after the BGO veto, 0.0568 cps
after both active vetoes, and 0.0521 cps after the Compton trajectory veto.
Thus the active system strongly suppresses prompt/charged activity.  In the
direct no-coincidence final W2 expectation, delayed contributes 69.98%; the
proton-incident delayed component alone contributes 47.03% of the total.

Using the existing conditional SE3 full-envelope signal proxy
`Aeff_W2,final = 11.69478 cm2`, the 20-day mission result is:

| quantity | mature replay |
|---|---:|
| cumulative background counts | 88,217.12053 |
| cumulative signal counts per unit flux | 12,643,941.41118 cm2 s |
| 3-sigma Gaussian Fmin | `7.04717764e-5 ph cm^-2 s^-1` |
| 3-sigma Poisson-Asimov Fmin | `7.05903107e-5 ph cm^-2 s^-1` |
| 5-sigma Gaussian Fmin | `1.17452961e-4 ph cm^-2 s^-1` |

Package 58's analytic 20-day 3-sigma Gaussian value was
`7.06350747e-5 ph cm^-2 s^-1`; the mature replay changes it by only -0.231%.
Therefore the failure of the central estimate to reach `5e-5` is not caused by
using the package-58 analytic live factor instead of the retained common-time
algorithm.

At fixed signal kernel, reaching `5e-5` would require reducing the integrated
background from 88,217 to about 44,408 counts, a 49.66% reduction.  At fixed
background it would require 1.4094 times the current signal kernel, equivalent
within this proxy to `Aeff_W2,final ~= 16.483 cm2` rather than 11.69478 cm2.

### 9.5 Uncertainty and claim boundary

The timeline resampling does not create new Geant4 information.  The final W2
transport selection contains 395 templates: one prompt gamma survivor and 394
delayed survivors.  After physical weights and mission correlation are applied,
the background has only 9.971 weighted effective survivors.  The corresponding
finite-transport counting diagnostic is 31.67% relative on integrated
background, or about 15.83% on `Fmin` from the background term alone.  This is
separate from the approximately 3% per-anchor timeline counting error.

Consequently the correct conclusion is:

- the mature Poisson/time-veto method works and validates the package-58
  central sensitivity scale;
- the central conditional estimate does not reach `5e-5`;
- the present data do not support a precise failure margin because prompt has
  one weighted survivor and the total weighted effective survivor count is
  small;
- the dominant central residual is delayed activation, especially the
  proton-incident family, rather than an obvious failure of the external
  positron/plastic or BGO veto logic;
- no final SG3B sensitivity or geometry-promotion claim is allowed because the
  denominator still uses an SE3 conditional signal proxy.  A fresh SG3B
  full-envelope 37,194-ray signal transport and common response are required to
  determine whether the true W2 effective area is closer to 11.7, 16.5, or the
  upstream 20 cm2 optical area.

The standalone PARMA mono-511 sidecar remains excluded from the repaired
broadband sum.  No paper number was changed by this update.
