# Seven-family TES and activation postprocessor (2026-08-12)

Status: **PREPARED / TESTED / WAITING FOR CANONICAL BATCH0004 FINAL PASS / NOT RUN**.

This package prepares the canonical postprocessing step for the corrected-keV,
proton-excluded seven-family screening campaign.  It does not launch Cosima,
does not inspect live `attempt_*` directories, and contains no paper-facing
physics result.  The analyzer must remain dormant until batch0004 publishes
all checkpoint authorities and its final PASS report and ledger.

## Authority boundary

The executable accepts only a complete, mutually consistent authority chain:

1. the fixed PASS batch0000, batch0001, and batch0002 ledgers, each with its
   compiled-in canonical SHA-256;
2. exactly one batch0003 gamma-instant authority selected by the batch0004
   global contract: either the canonical ordinal-76 prefix or the canonical
   stage5 profile, with exact report/ledger paths, hashes, statuses, and event
   exposure;
3. all 12 fixed batch0004 family/mode checkpoint PASS report+ledger pairs; and
4. the batch0004 final PASS report and merge-eligible ledger, including exact
   checkpoint bindings and prior-only negative-muon closure.

There is no run-directory glob or fallback ledger.  A missing authority yields
`WAIT` and writes neither a pin nor an analysis directory.  A mismatch yields
`FAIL`.  The write-once authority pin is re-derived and compared before any
canonical job collection.

The 28 normalization cells are kept separate:

`geometry x mode x family = 2 x 2 x 7`.

No counts, observation time, isotope production, or detector response are
pooled across geometry, mode, or family.  Prompt TES observables use `instant`
SIM files only.  Activation observables use `buildup` isotope DAT files only.
The batch0003 gamma exposure is instant exposure and is never deducted from or
credited to batch0004 gamma buildup.

## Physical and statistical contract

- Every source, SIM header, ledger geometry header, and fixed geometry contract
  must agree.  Source/DAT/log/SIM hashes, seed identity, event closure, and the
  unique positive observation time in DAT and log are checked against the
  ledgers by reading the actual files.
- TES hits are aggregated per event and physical pixel before selection.
- The measured response applies a deterministic keyed Gaussian draw per pixel
  at 420 eV FWHM, then a 0.3 keV post-noise pixel threshold.  The key includes
  geometry, mode, family, batch, seed, job, event, and pixel, so traversal order
  cannot change the result.
- Mass_model_511 veto uses exactly the 24 physical CsI volumes.  S3d-O8 uses
  exactly the three physical BGO volumes plus three physical plastic volumes.
  The BGO/CsI thresholds are 50, 70, and 80 keV; the O8 plastic threshold is
  fixed by the retained response contract.  Passive Kapton is explicitly
  excluded from every veto whitelist.
- Prompt tables include raw and measured TES spectra, pre-veto and veto50/70/80
  selections, TES-positive, 480--550 keV and W2 windows, pair/annihilation
  categories, primary-energy drivers, and source-side direction defined by
  `acos(-dir_z)`.
- Prompt rates are `sum(count) / sum(TT)` within one cell.  Activation rates are
  `sum(RP) / sum(TT)` within one geometry/family buildup cell.  Every buildup
  job, including jobs with zero RP records or zero RP for a particular
  volume/isotope/state key, contributes its TT to that denominator.
- Count/rate uncertainty uses two-sided 95% Poisson intervals; empty cells also
  carry the one-sided 95% upper limit `-ln(0.05)/sum(TT)`.  Binomial efficiencies
  and veto survival carry 95% Wilson intervals.  Open-ended driver bins are
  encoded with JSON `null` plus an explicit flag; non-finite JSON is rejected.

This is screening prompt/production evidence only.  It is not delayed-decay
transport, mission response, sensitivity, or geometry-promotion authority.

## Canonical workflow (run only after final PASS is independently accepted)

From the repository root:

```bash
python3 engineering/particle_source_unit_repair_20260811/seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py --pin-authorities
python3 engineering/particle_source_unit_repair_20260811/seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py --check-inputs-only
python3 engineering/particle_source_unit_repair_20260811/seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py --run
```

`--check-inputs-only` validates the authority and reads ledger/source/DAT/log
metadata without reading SIM payloads and without writing outputs.  `--run`
streams each canonical instant SIM and publishes `results_canonical/` only
after all files are closed, all authority/input/output hashes are rechecked,
and every validation boolean is true.  Work is written to a sibling temporary
directory and atomically renamed; any failure removes the temporary directory
and cannot leave a canonical partial result.  Existing output is never
overwritten.  `--no-figures` exists for tests or an explicitly requested
table-only run, not for the default canonical publication.

## Planned outputs

- `canonical_input_manifest.csv`
- `prompt_tes_event_diagnostics.csv.gz`
- `prompt_cutflow.csv`
- `prompt_tes_histograms.csv`
- `prompt_primary_drivers.csv`
- `prompt_pair_annihilation.csv`
- `activation_family_exposure.csv`
- `activation_rp_by_volume_isotope_state.csv`
- per-geometry/family raw-vs-measured TES spectrum PNG/SVG figures
- prompt veto-cutflow PNG/SVG figures
- per-geometry activation isotope-ranking PNG/SVG figures
- `seven_family_tes_activation_summary.json`
- `seven_family_tes_activation_validation.json`

Every published output except the validation envelope is recorded with path,
size, and SHA-256 in the summary/validation chain.  The validation envelope is
strict JSON and is the final publication gate.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  engineering.particle_source_unit_repair_20260811.seven_family_tes_activation_postprocess_20260812.tests.test_seven_family_tes_activation
```

The suite covers strict JSON, unique TT and RP parsing, whitelist/Kapton
classification, keyed-response determinism, synthetic SIM closure, zero-RP TT
normalization, absent-authority fail-closed behavior, failed transaction
cleanup/retry, a complete synthetic 28-cell transaction, and read-only parsing
of retained real batch0000/1/2 rows.

Implementation hashes and the frozen test command are recorded in
`IMPLEMENTATION_MANIFEST.json`.  No canonical authority pin or result directory
is part of this prepared package.
