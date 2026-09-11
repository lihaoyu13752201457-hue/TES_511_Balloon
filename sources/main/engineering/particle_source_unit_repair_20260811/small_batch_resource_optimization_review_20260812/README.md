# Corrected-keV small-batch resource review and M05 optimization plan

Status: `READ_ONLY_REVIEW__NO_NEW_TRANSPORT`

This report uses only ledger-owned, validated corrected-keV artifacts. It does
not restore delayed-chain, response, sensitivity, or geometry-promotion
authority.

## Audited sample

- 432 accepted seven-family jobs and 6,554,160 primaries, plus four mergeable
  batch0000 proton jobs and 92 primaries;
- the accepted eight-family prefix contains 436 jobs and 6,554,252 primaries;
- its measured rich-output footprint is about 24.477 GB and its accumulated
  Cosima run-phase is about 8.369 h;
- the later 256-primary proton resource diagnostic is separate and non-mergeable;
- run-phase is Cosima BeamOn steady-clock time, not OS user+system CPU time.

## Observed cost ranking

| Family | ms / primary | compressed kB / primary | Interpretation |
|---|---:|---:|---|
| alpha | 434.025 | 360.385 | Highest accepted per-primary burden; strong heavy-tail and small-N caveat |
| proton diagnostic | 156.249 | 113.995 | Non-mergeable N=256 diagnostic; one event generated 61.6 MB raw text |
| positron | 46.847 | 41.240 | O8 is about 3.3x Mass in run-phase; preserve PAIR/ANNI ancestry |
| neutron | 16.751 | 13.390 | O8 is about 4.7x Mass; prompt and activation are both important |
| negative muon | 10.140 | 9.215 | Low total budget but capture/buildup needs a precision check |
| positive muon | 9.397 | 8.710 | Low priority; zero observations require upper limits |
| electron | 8.793 | 8.176 | Current coverage is only about 22% of the screening reference |
| gamma | 2.665 | 2.109 | Cheapest per primary but largest event count and sparse W2 survivors |

The optimized O8 geometry changes the resource regime: measured O8/Mass
run-phase multipliers are about 4.70 for alpha, 4.69 for neutron, 3.32 for
positron, and 2.72 for gamma.

## Rich-output hotspot

Streaming inspection of the 40 batch0001 SIM files found about 71.8% of raw
bytes in `CC HIT`, 27.4% in `IA`, and 0.58% in `HTsim`. Gzip already provides
about 6.5--6.8x raw-text compression. Therefore the first optimization target
is the creation and serialization of per-step CC/IA records, not HT records or
gzip tuning.

## Recommended design

1. Preserve the baseline transport physics and implement an M05-complete typed
   event sidecar. Every primary keeps its denominator, source stratum, weight,
   job/seed provenance, TES and active-shield block summaries, passive-material
   aggregate, and TT. Every real RP keeps exact isotope/state/volume/position
   and ancestry.
2. Retain full native truth for every raw TES-positive event, every RP-producing
   event, boundary candidates, pair/annihilation candidates, and a preregistered
   stratified control sample. Do not simply delete all TES-zero or vetoed events.
3. Treat r1 as a sequential checkpoint. Add r2/r4/r8 only for
   family-by-geometry-by-mode cells whose W2, TES, RP/TT, or material-attribution
   uncertainty has not met a preregistered gate.
4. Use a family-aware scheduler. One heavy O8 job occupies the heavy slot;
   additional light jobs are allowed only after an RSS gate. Current measured
   maximum process-group RSS is 4.98 GB, with only 362/432 jobs covered.
5. Use full-support weighted energy strata for the proton heavy tail and, after
   an analog control is frozen, for rare gamma W2 and alpha tails. Never truncate
   the high-energy source support.
6. Only after output closure, run paired region-cut tests in far, thick passive
   material: 50 micrometres, 0.1, 0.5, and 1 mm. Keep 5 micrometres in TES,
   active veto, thin windows/foils, near-field high-Z regions, and other
   resolution-critical volumes. Physics-list changes are a later systematic arm.

## Planning envelope

The previously quoted 198 GB and 66.8 h are a proton-excluded seven-family
sub-budget. A strict eight-family r1 uses the same batch convention as the other
families: 234,000 proton primaries per geometry and mode. After crediting the
23 mergeable batch0000 events in each cell, 935,908 proton primaries remain.
The N=256 resource-smoke rates project 106.69 GB and 40.62 run-phase h for this
proton work. The strict eight-family r1 point estimate is therefore about
305.00 GB and 107.46 h after current credits. These proton numbers are linear
planning points with no reliable tail confidence bound.

The historical r8 projections of roughly 1.07--1.17 TB and 375--387 h exclude
protons and must not be called an eight-family total.

With current free space, the 20 GiB reserve, and a 2x capacity gate, point output
must be no more than about 43.3 GB. Thus strict eight-family r1 needs a measured
additional reduction of about 7.0x. CC-only aggregation is structurally around 3.3--3.5x and is
not enough; reaching a 5--6x target requires compacting IA as well and retaining
full truth only for candidates and controls. Compact CPU/RSS benefits remain
unmeasured and must not be inferred from the disk ratio.

## What 16 h and 80 GB buy

Assume first that 16 h means accumulated Cosima run-phase and that 80 GB is a
new-output quota. Advancing the strict eight-family r1 cells by the same
fraction gives a scale factor of 0.1489 and about 6.112 million new primaries:
5.062 million gamma, 0.516 million neutron, 0.131 million positron, 13.4 thousand
alpha, 0.241 million electron, 6.2 thousand positive muon, 2.9 thousand negative
muon, and 0.139 million proton. The point output is about 45.41 GB rich SIM.
Added to the current accepted prefix, that reaches about 12.67 million
primaries, or 26.6% of the strict eight-family r1 event target.

For 16 h of actual wall time, reusing the seven-family controller calibrations
gives only a provisional 5.10--6.04 million range and 37.9--44.9 GB. Proton has
not yet been measured with production-sized shards, so this is not a throughput
promise. If 80 GB is physical free space and the project 2x capacity gate is
retained, point output is limited to 40 GB; the strict balanced run stops near
14.09 run-phase hours and 5.384 million new primaries. A measured 5x compact
output would reduce the 16 h point output to about 9.08 GB, but it does not
multiply transport statistics because compact CPU speedup is unmeasured.

There is a useful nearer-term milestone: closing only the 1M-gamma-equivalent
proton screen needs 93,508 new proton histories, about 4.06 run-phase h and
10.66 GB at the current point estimate. Completing that screen first and using
the remaining 11.94 h for the seven-family checkpoint yields about 7.26 million
new histories and 46.09 GB. This is a screening closure, not strict proton r1.

If every available run-phase hour is instead spent on matched prompt gamma,
the event-count upper bound is about 10.67 million new primaries per geometry,
21.33 million total, and 44.76 GB rich SIM. This maximizes primary count but not
scientific closure. Scaling the observed 3/1 W2 counts gives only about 19/6
selected events after adding the present exposure; the approximate Poisson
relative uncertainty of the geometry rate ratio remains about 46%.

The earlier 9.60-million estimate remains valid only as a deliberately
proton-excluded seven-family sub-budget, not as an eight-family capacity claim.
Therefore the corrected budget is enough for a paper-ready corrected-keV methods or
compact-equivalence section and, after directed allocation, a limited
single-component result. It is not enough for a complete M05 claim covering
all-family prompt background, activation inventory, delayed transport, common
response, mission sensitivity, or geometry promotion. Paper sufficiency must
be judged by selected-event effective counts, not primary count: about 25,
100, and 400 effective events correspond to approximately 20%, 10%, and 5%
Poisson relative uncertainty for one component. A zero count requires an exact
upper limit rather than a claim of physical absence.

## Physics boundary

The only published corrected prompt cutflow is gamma prefix76. For each geometry
it contains 2.001M primaries; after the 50 keV active veto, W2 counts are 3 for
Mass_model_511 and 1 for O8. Gamma statistics therefore cannot simply be reduced.
Corrected non-gamma prompt cutflows, activation inventory accumulation, delayed
transport, common response, mission fold, and geometry promotion remain open.
Raw RP is an isotope-production record, not activity or delayed 511-keV
background.

The validated interactive report payload is `artifact.json`; its bounded source
tables are the CSV files in this directory.
