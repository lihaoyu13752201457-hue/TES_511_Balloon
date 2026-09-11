# TES-511 primary-source unit repair

Status: `STATIC_REPAIR_PASS__BATCH0000_TO_BATCH0002_MERGE_ELIGIBLE__FULL_CHAIN_RERUN_PENDING`

This package repairs the factor-1000 kinetic-energy-axis error identified in
the retained eight-family continuum source cards.  It does not overwrite any
retained Mass_model_511, S3c, S3d-O8, prompt, activation, delayed, or response
artifact.

## Repair scope

The repaired profile is `unit_only_total_gamma`:

- all non-alpha raw energies are converted from MeV to total keV with a factor
  of 1000;
- alpha raw energies are MeV per nucleon and are converted to total alpha keV
  with a factor of `4 * 1000`;
- the differential PDF is transformed consistently and normalized to unit
  trapezoidal integral;
- every per-angle-bin `.Flux`, beam definition, particle type, far-field
  radius, and geometry reference is preserved from its retained parent card;
- all generated source cards point to package-owned, hash-pinned corrected
  spectra.

The input raw spectra describe the retained EXPACS/PARMA condition at latitude
34 deg, longitude 100 deg, altitude 38 km, cutoff rigidity 11.6 GV, and
`W=118.3`.  The gamma spectrum is the retained *total* broadband table and
contains its broad-bin annihilation-line bump.  A standalone atmospheric
511-keV mono source must not be composed with this profile.  A future
`continuum_plus_mono` model requires a separate package with one consistent
environment, explicit line subtraction, and per-bin flux closure.

## Outputs

- `input/raw_expacs/`: 160 package-owned, trackable raw-spectrum snapshots.
- `input/source_unit_audit_evidence_hashes.csv`: independent raw-input hash
  ledger carried forward from the source-unit audit.
- `spectra/correct_keV_total/`: 160 trackable Cosima `IP LIN`/`DP` spectra.
- `config/source_cards/mass_model_511/`: eight corrected Mass_model_511 cards.
- `config/source_cards/s3c_c0/`: eight corrected S3c-C0 cards.
- `config/source_cards/s3d_o8/`: eight corrected S3d-O8 cards.
- `data/source_contract_manifest.json`: raw, spectrum, source-card, geometry,
  flux, and SHA-256 provenance.
- `data/static_validation.json`: fail-closed validation result.

The canonical source contract SHA-256 is
`5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326`.
The static validator passes with 160 spectra, 24 source cards, 480 corrected
references, zero legacy `_2602units` references, and three closed transitive
geometry bundles.

## Build and validate

Run from the repository root:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/build_corrected_source_package.py
python3 engineering/particle_source_unit_repair_20260811/code/validate_corrected_source_package.py
python3 -m unittest discover \
  -s engineering/particle_source_unit_repair_20260811/tests \
  -p 'test_*.py'
```

The validator must establish all of the following before any Cosima transport:

- 160/160 spectra pass the raw-to-total-keV transformation;
- 480/480 production references use the package-owned corrected spectra and
  zero references use `cosima_spectra_dp_2602units`;
- PDF, flux, equal-mu solid-angle, R=60 cm, particle-type, geometry, and hash
  contracts close;
- the only allowed parent-to-child card changes are the spectrum-root comment
  and the 20 `Spectrum File` paths.

## Two-geometry mergeable smoke

The corrected original eight-family, 20-angle-bin source was transported
through both requested geometries:

- reference geometry: `Mass_model_511`;
- optimization-line candidate geometry: `S3d-O8` (full-wrap BGO active
  catcher, plastic positron-rejection layer, and borated-polyethylene neutron
  shield).

This is not a mono-line or reduced-bin surrogate: the source PDFs, fluxes,
angular bins, geometry, and transport physics are the production inputs.  Only
the event count and job partitioning are reduced for SMOKE statistics.

Instant-prompt and isotope-buildup sampling are separate campaigns.  Each
geometry/mode campaign contains eight jobs and 1,188 primaries:

- gamma 1,000; neutron 96; electron 41; positron 24; proton 23;
- alpha 2; negative muon 1; positive muon 1.

The four campaigns therefore contain 32 successful jobs and 4,752 validated
`IA INIT` records.  Every campaign resolves 160 corrected spectrum references
and zero legacy references.  All SIM geometry headers, explicit seeds,
particle types, directions, sampled energy support, isotope DAT files, and
positive matching DAT/log observation times pass the dynamic validator.
The 32 positive matching observation times span 0.00500222--0.0211693 s.
Buildup sampling retained 24 RP rows (summed production count 25) for
Mass_model_511 and 30 RP rows (summed production count 34) for S3d-O8;
zero-production jobs still contribute their observation time to a future
isotope-rate denominator.

The dynamic authority files are:

- `runs/particle_source_unit_repair_20260811/mergeable_smoke_v1_contract.json`;
- `runs/particle_source_unit_repair_20260811/mergeable_smoke_v1_validation.json`;
- `runs/particle_source_unit_repair_20260811/mergeable_smoke_v1_ledger.json`.

The validation status is `PASS`, and the ledger status is
`PASS__BATCH0000_MERGE_ELIGIBLE`.  These samples may be combined only with a
future batch that preserves the frozen source, geometry, physics, Cosima,
library, and Geant4-data contracts and registers disjoint seeds.  Use
`sum(selected)/sum(TT)` for prompt samples and, within one geometry, mode,
family, production volume, and isotope state, `sum(RP)/sum(TT)` for buildup.
Never pool raw counts or TT across geometries, modes, or particle families.

Operational note: the first wrapper-level post-run validation inherited an
already sourced MEGAlib environment and sourced it a second time, producing a
false mismatch in the environment string only.  Transport had already
completed successfully.  The unchanged, contract-frozen dynamic validator
(`cb435e9044082eb34c36e2e50855238de8a968bd24c8f977ac261fc8ca93c64a`)
was run from the base environment, passed all 32 jobs, and wrote the final
report and ledger.  The harness now leaves environment setup to the validator,
so later runs cannot repeat this false rejection.

To repeat the validation without changing outputs:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/validate_mergeable_two_geometry_smoke.py --check
```

## Seven-family production-contributing batch0001

The first corrected-keV seven-family batch excludes protons and transports
the other seven families through Mass_model_511 and S3d-O8 in separate
instant and buildup campaigns.  It completed 40/40 jobs and validated
466,692/466,692 `IA INIT` records.  All 800 dynamic spectrum references are
corrected and none uses `_2602units`; no proton job exists.  The validation
status is `PASS` and the ledger status is
`PASS__BATCH0001_MERGE_ELIGIBLE`.

Read the batch contract and results at:

- `SEVEN_FAMILY_BATCH0001.md`;
- `runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_validation.json`;
- `runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_ledger.json`.

The four completed directories occupy about 2.332 GB.  After crediting
batch0000 and batch0001, the historical full-stat target still requires
92,882,280 primaries.  Calibrated retain-all output is about 1.091 TB at the
point estimate and needs about 2.202 TB free under the minimum 2x safety gate
plus 20 GB reserve; at least 2.5 TB free is recommended.  The current local
disk cannot retain the complete raw chain.  Later shards must use disjoint
registered seeds and be dynamically validated before any external archival or
local raw-file release.

## Paired muminus instant batch0002

A first full-target top-up shard adds 10,000 instant negative muons to each
geometry with paired seed `860915732`. Both jobs and all 20,000 `IA INIT`
records pass corrected-energy, particle, direction, seed, and geometry gates.
The validation is `PASS`; the ledger is
`PASS__BATCH0002_MERGE_ELIGIBLE`. The two campaign directories occupy about
192.3 MB total. See `MUMINUS_INSTANT_PAIR_BATCH0002.md` and the validation
and ledger named `muminus_instant_pair_batch0002_v1_*` under the repair run
root.

## Instant-gamma 10M controller batch0003

The non-overwriting batch0003 harness defines corrected-keV instant-gamma
checkpoints of exactly 5M and 10M primaries per geometry after crediting the
validated 101k prior events. The default run stops with independent merge
authority at 5M; 10M is an explicit ceiling that can be continued only inside
the same frozen 12-hour window. It uses 25k equal-N/same-seed operational shards
(one 24k checkpoint-closing shard), robust process/disk/RAM/deadline gates, and
full per-shard and per-stage validation. This operational pairing is not a
common-random-number or paired-estimator claim. Transport has not been launched
by the harness-preparation step. See `GAMMA_INSTANT_BATCH0003.md`.

## Seven-family 1M-equivalent screening batch0004

The non-overwriting batch0004 harness defines a reduced-statistics corrected-
keV checkpoint after batch0003 publishes either the preferred canonical
ordinal-76 instant-gamma prefix or its independent 5M authority. Gamma is added only in buildup; the six other non-proton families
use separate instant and buildup campaigns. Exact batch0000/0001 credit is
deducted, and batch0002 already closes negative-muon instant above the target.
The plan contains 127 operationally paired ordinals, 254 jobs, and 2,395,698
new primaries. Its point estimate is 17.44 GB and 6.90 CPU h.

Batch0004 does not receive a new wall window: it inherits batch0003's original
start and deadline, refuses transport until the selected predecessor
report/ledger pair passes exact validation, retains a 20 GiB free-space reserve, and
publishes independent family/mode checkpoints before a final umbrella ledger.
It is explicitly a screening product, not the historical full-stat target.
Harness preparation ran only tests and `--print-plan`; no batch0004 transport
was launched. See `SEVEN_FAMILY_1M_SCREENING_BATCH0004.md`.

## Authority boundary

Passing this package proves the repaired *source input*.  It does not repair
previous SIM files or derived prompt, isotope inventory, activation, delayed,
Step05-response, mission, sensitivity, or geometry-ranking results.  Those
quantities require a new matched transport chain.  Retained legacy products
remain structural or historical evidence only.  The new smoke is valid source
transport and mergeable sampling, but it is deliberately too small to restore
full-chain physics or geometry-promotion authority by itself.
