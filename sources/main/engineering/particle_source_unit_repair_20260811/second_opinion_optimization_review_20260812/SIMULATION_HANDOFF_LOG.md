# Corrected-keV simulation handoff log

Snapshot time: 2026-08-12T11:31:22+08:00

Purpose: immutable handoff context for an independent, read-only optimization
review.  This file is descriptive; the JSON validation/ledger files listed
below remain the authority.

## Safety and state at handoff

- No Cosima transport, batch controller, or batch validator was active at the
  snapshot.
- The worktree was already dirty and contains substantial retained user work.
  The reviewer must not reset, overwrite, clean, or reinterpret those changes.
- Filesystem free space was 112,347,258,880 bytes (about 104.65 GiB).  The
  project requires at least 20 GiB to remain free.
- Physical RAM was 12,541,419,520 bytes; `MemAvailable` was 8,405,708,800
  bytes.  Swap was 1,975,685,120 / 2,147,479,552 bytes used.
- Review scope is read-only.  Do not start Cosima, change a source/geometry,
  delete raw data, or modify a retained paper.

## Geometry scope

The matched corrected-keV transport uses two geometries:

1. `Mass_model_511`, the mass-complete detector/cryostat reference geometry.
2. `S3d-O8`, derived from the Mass_model_511 line and containing a full-wrap
   BGO active catcher, a plastic charged-particle/positron-rejection layer, and
   borated-polyethylene neutron shielding.

The retained design-family documents also name `S3c-C0` and `S3c-LW1`.
Those are important optimization history, but they must not be silently
identified with the S3d-O8 geometry actually used in batches 0000--0005.  The
reviewer must resolve the canonical setup paths and transitive geometry bundle
hashes from the ledgers before drawing geometry conclusions.

Primary entry points:

- `engineering/Mass_model_511_nearfield_migration_20260701/SESSION_BOOTSTRAP.md`
- `engineering/Mass_model_511_nearfield_migration_20260701/README.md`
- `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/README.md`
- `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_mainline_analysis_summary.json`
- `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/`
- `engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`

## Factor-1000 source repair

The retained EXPACS/PARMA workbook/table energy coordinate is in MeV, whereas
Cosima `Spectrum File` energy is interpreted in keV.  The legacy cards therefore
sampled non-alpha primaries at 1/1000 of their intended kinetic energy.  Alpha
tables are MeV per nucleon and require `4 * 1000` to obtain total-alpha keV.

The corrected package changes the spectrum energy axis, not the physical flux:

- non-alpha: `E_corrected_keV = 1000 * E_raw_MeV`;
- alpha: `E_corrected_keV = 4 * 1000 * E_raw_MeV_per_nucleon`;
- `.Flux`, 20 equal-mu angular bins, particle type, far-field radius, and beam
  definitions are preserved;
- the differential sampling PDF is normalized after the coordinate transform;
- all production cards use package-owned corrected spectra, with zero legacy
  `_2602units` references.

Canonical source-contract SHA-256:
`5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326`.

Important physics boundary: the corrected total broadband gamma table already
contains its broad-bin annihilation feature.  Do not add the retained mono-511
source unless a separate continuum-plus-line flux-closure package is built.

## Accepted transport authorities

| Batch | Authority state | Ledger SHA-256 | Scope |
|---|---|---|---|
| 0000 | `PASS__BATCH0000_MERGE_ELIGIBLE` | `036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f` | 8-family smoke, two geometries and two modes |
| 0001 | `PASS__BATCH0001_MERGE_ELIGIBLE` | `bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4` | seven non-proton families, 466,692 new primaries |
| 0002 | `PASS__BATCH0002_MERGE_ELIGIBLE` | `742a4deb1bc3ab4585e479884d7e0ec376a0622f19391c8d87a2e66b92779a62` | instant negative-muon pair, 20,000 new primaries |
| 0003 prefix76 | `PARTIAL_PREFIX_MERGE_ELIGIBLE` | `3519c39d86e9bf38eddd01adae299c3428ef9810755d7e1d282420851df416fc` | instant gamma, cumulative 2,001,000/geometry |
| 0004 partial | `PASS__BATCH0004_PARTIAL_CHECKPOINT_THROUGH_GLOBAL_ORDINAL0097_MERGE_ELIGIBLE` | `b4de513e7902ae4755eb741e7a79d23c378b3e3dd8cee993c7ffbff1af19dba0` | five complete stages plus alpha-instant partial; not a seven-family final |
| 0005 add-on | `PASS__BATCH0005_REDUCED_BREADTH_ADDON_MERGE_ELIGIBLE` | `670bc6f14de7799306301343908f524738c564ac62161caab1206a0be5cc41a0` | 27,340-primary reduced-breadth add-on; not batch0004 final |

Authoritative paths are under
`runs/particle_source_unit_repair_20260811/`; find the exact report paired with
each ledger and verify both before using it.

## Current cumulative seven-family primary counts

Counts are identical for the two geometries.  Each entry is per geometry and
must remain separated by instant versus buildup.

| Family | Instant | Buildup |
|---|---:|---:|
| gamma | 2,001,000 | 1,000,000 |
| neutron | 96,310 | 96,310 |
| electron-minus | 9,187 | 9,187 |
| positron | 24,370 | 24,370 |
| alpha | 2,390 | 491 |
| muon-plus | 1,160 | 1,160 |
| muon-minus | 10,105 | 1,040 |

The four geometry/mode campaigns contain 6,554,160 accepted primary histories
in total.  These are input/`IA INIT` counts, not TES survivors.

## Measured runtime and storage behavior

Across the completed new production portions of batches 0003--0005:

- 362 geometry jobs;
- 6,062,808 new primary histories;
- Cosima-reported run phase 26,670.041 s (7.408 h); this is a `steady_clock`
  BeamOn elapsed time, not OS user CPU time;
- summed subprocess wall time 31,743.204 s (8.818 worker-h);
- SIM + isotope DAT + log = 22,718,567,400 bytes;
- controller-active spans summed to about 7.495 h;
- no attempt02/retry was needed.

Workload composition matters: gamma was 92.333% of new histories but only
53.747% of retained bytes.  Neutrons were 5.712% of histories and 20.859% of
bytes; positrons 1.445% and 16.715%; alpha 0.079% and 7.670%.  The small current
disk footprint must not be extrapolated using a gamma-dominated average.

Observed resident-memory tails were also family/geometry dependent.  Examples:

- S3d-O8 positron buildup: about 4.75 GiB peak RSS;
- S3d-O8 gamma instant: about 4.66 GiB;
- S3d-O8 neutron instant: about 4.15 GiB;
- S3d-O8 neutron buildup: about 3.83 GiB.

`StoreSimulationInfo all` produces rich IA/CC/HT/PM records.  Prefix sampling
showed CC records, almost entirely `CC HIT`, contributed roughly 60--90% of
uncompressed event-record bytes.  Per-job run time per primary and compressed
SIM bytes per primary were extremely correlated (`r` about 0.997), although a
no-output control has not yet separated transport cost from serialization and
compression causally.

## Corrected gamma TES result already available

The accepted 2.001M/geometry instant-gamma postprocess has:

- summary SHA-256
  `08e431718b48e0e23b96052393804cc95bcfa86cb75bb413aa2b92f0644ccad2`;
- validation SHA-256
  `8012f103c73553512c088027ee0d18dbaae627d3f92bbc42104249e035b97a7f`.

At a 50-keV active-shield threshold:

| Geometry | TES-positive | 480--550 keV | 510.58--511.42 keV |
|---|---:|---:|---:|
| Mass_model_511 | 223 | 14 | 3 |
| S3d-O8 | 51 | 5 | 1 |

These are response-thresholded, prompt-gamma, active-veto counts without an
accepted full Step05/FoV all-family closure.  They are sparse and do not support
mission sensitivity or geometry promotion.

## M05 versus M06 information boundary

For deciding what an optimized transport/output format must preserve, read the
full M05 method and data dependencies, not only the deliberately restricted M06
interim text:

- `core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/balloon511_ea_draft_en_m05_atm511_source_revision_20260811.tex`
- `core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/balloon511_ea_draft_zh_m05_atm511_source_revision_20260811.tex`

M05 requires, at minimum, enough information for:

- eventwise TES pixel energy aggregation and detector response;
- real active-shield and plastic-veto energy sums;
- prompt/delayed/focused-stream coincidence handling;
- TES hit multiplicity, interaction positions/order, Compton topology, and FoV
  consistency;
- incident family, primary energy/direction, pair/annihilation drivers, and
  selected-event provenance;
- activation nuclide, excitation state, material/volume, production position,
  and the TT contribution of zero-production runs;
- NUBASE-corrected inventory construction, production-position delayed source,
  common response, and mission-time fold.

M05 numerical results were produced before the factor-1000 repair and are not
current physics authority.  Its methods define the preservation requirements;
its old rates, rankings, delayed totals, and sensitivity must not be promoted.
M06 accurately marks the currently blocked claims but is intentionally too
minimal to specify every future data dependency.

## Optimization question for the independent reviewer

Design a scientifically lossless or explicitly bounded replacement for the
current retain-all workflow that materially reduces both wall time and disk.
Prompt and buildup may require different output profiles.  Candidate ideas may
include in-simulation scoring, selective event serialization, compact
event/activation sidecars, stratified or importance-sampled sources, weighted
variance reduction, and a retained full-truth control fraction.  However:

- do not raise Geant4 production cuts or remove primary-energy bands merely on
  intuition; pair production, annihilation feed-in, veto response, and
  activation can arise far from 511 keV;
- do not discard interaction order/position if M05 topology needs it;
- do not replace exact activation production positions with volume-only counts
  without proving downstream equivalence;
- propose a same-input A/B pilot and event-/observable-level equivalence gates
  before any optimized mode is allowed into production.

## 2026-08-12 follow-up authorization: isolated optimization smoke

After the independent GPT-5.6-Sol ultra audit completed, the user explicitly
authorized that same reviewer to implement and run an isolated smoke benchmark.
The purpose is to test whether a materially faster and smaller representation
can preserve the full M05 analysis contract.  This does **not** authorize any
production merge, production-cut change, source-energy truncation, retained
geometry edit, paper-number replacement, or deletion of existing data.

The executor owns proposal, implementation, tests, and smoke execution.  The
primary Codex session independently owns the final physics-equivalence and
performance GO/NO-GO decision.  O8 neutron, positron, and alpha stress cells are
mandatory; a gamma-only or light-particle-only benchmark cannot establish the
optimization.
