# Corrected-keV gamma prompt-TES authority postprocessing

Status: `IMPLEMENTED_AND_SYNTHETIC_TESTED__WAITING_FOR_SELECTED_CANONICAL_AUTHORITY`

This package is a non-overwriting streaming consumer for corrected-keV instant
gamma transport in `Mass_model_511` and `S3d-O8`. It never starts Cosima and
never discovers or reads an in-progress attempt. Canonical analysis requires
one explicit, mutually exclusive authority profile.

## Authority profiles

`stage5` is the full 5,000,000-event checkpoint per geometry. It consumes the
fixed batch0003 stage5 PASS ledger/validation pair plus the retained 101,000
prior events from batch0000 and batch0001.

`prefix76` is the committed-pair ordinal-76 fallback: 1,900,000 new events plus
101,000 prior events, or 2,001,000 events per geometry. It is always labelled
`2.001M prefix diagnostic (ordinal 76; non-full)`. It is not full batch0003,
eight-family, activation/delayed, sensitivity, or geometry-promotion authority.

The fixed selected paths are:

```text
# stage5
runs/particle_source_unit_repair_20260811/gamma_instant_batch0003_stage5m_v1_validation.json
runs/particle_source_unit_repair_20260811/gamma_instant_batch0003_stage5m_v1_ledger.json

# prefix76
runs/particle_source_unit_repair_20260811/gamma_instant_batch0003_prefix_checkpoints_20260811/gamma_instant_batch0003_prefix_shard0076_v1_validation.json
runs/particle_source_unit_repair_20260811/gamma_instant_batch0003_prefix_checkpoints_20260811/gamma_instant_batch0003_prefix_shard0076_v1_ledger.json
```

Canonical CLI mode has no ledger-path override. Batch0000 and batch0001 paths
and SHA-256 values are frozen in code. After one selected report/ledger pair is
published, one of these commands creates a single fixed write-once pin:

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma5m_postprocess_20260811/code/analyze_gamma5m_prompt_tes.py --pin-stage5-authority

python3 engineering/particle_source_unit_repair_20260811/gamma5m_postprocess_20260811/code/analyze_gamma5m_prompt_tes.py --pin-prefix76
```

The pin is
`data/canonical_gamma_authority.json`. It records the chosen profile, exact
report/ledger paths and SHA-256 values, prior/new/cumulative events, prefix end
ordinal, and full/non-full scope. A pin for one profile cannot authorize or be
replaced by the other. If the selected pair is absent or invalid, pinning exits
FAIL and writes nothing.

For prefix76, the analyzer requires exactly ordinals 1 through 76 in each
geometry, 76 unique new-job seeds, exactly 1,900,000 new events, and exactly
2,001,000 cumulative events. The prior 101,000 jobs and selected new jobs must
have unique identities and artifact paths; their seeds cannot overlap. The two
geometry schedules must match operationally but remain separate aggregation
domains.

## Transport, geometry, TT, and detector contracts

Every ledger-referenced SIM is streamed through gzip EOF while hashing the
exact compressed bytes. The analyzer requires sequential `ID 1..N`, `SE=N`,
one valid gamma `IA INIT` per event, the registered seed, exactly one Geometry
header, one `EN`, positive `TE`, and `TS=N`.

Each geometry key is bound to a fixed `.geo.setup` path/hash and detector-map
path/hash. The ledger IA scan, source-card `Geometry` directive, SIM header,
and fixed geometry key must all agree. Source cards must contain the corrected
20-bin spectra and no `cosima_spectra_dp_2602units` reference.

For every job, the analyzer parses exactly one positive `TT` from the isotope
DAT and exactly one positive `Observation time` from the log, then requires
DAT=log=ledger. Rates use `sum(selected counts)/sum(TT)` within one geometry,
instant mode, and gamma family only.

TES deposits are aggregated by real pixel UID. The deterministic response is
420 eV FWHM Gaussian noise per aggregated pixel followed by a 0.3 keV inclusive
pixel threshold. SHA-256 keyed Box-Muller noise makes results invariant to job
ordering. Source-side angle is `acos(-IA_dir_z)`.

Mass veto uses the exact 24 physical CsI sensitive volumes. S3d-O8 uses the
three physical BGO crystals and three physical plastic volumes only. BGO/CsI
thresholds are 50/70/80 keV; O8 plastic remains `<50 keV`. Kapton and passive
Al structures are excluded.

## Statistics and publication

Outputs include TES spectra, veto cutflow, `[480,550)` keV and
`[510.58,511.42)` keV windows, primary-energy/source-direction drivers,
pair/annihilation categories, Garwood Poisson intervals, Wilson intervals, and
the zero-count one-sided 95% rate upper bound.

Validation gates pair-category closure in all three windows, driver
denominator and selected-count closure, and full-histogram closure including
underflow and overflow. Open-ended energy bins serialize as JSON `null` plus
`bin_high_open_ended=true`; non-finite JSON tokens are forbidden.

Output names are profile-specific:

```text
gamma_stage5m_...
gamma_prefix76_2p001m_diagnostic_...
```

Prefix titles/statuses explicitly say `2.001M`, `diagnostic`, and `non-full`;
they are never presented as gamma5M results.

All files are built in a new sibling temporary directory. Only after files and
hashes close, all validation booleans pass, strict JSON round-trips, and input
ledgers rehash unchanged is the entire directory atomically renamed. Failure
removes only that private temporary directory and leaves no partial canonical
result.

## Commands

After pinning one authority, metadata-only checking is explicit:

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma5m_postprocess_20260811/code/analyze_gamma5m_prompt_tes.py --profile prefix76 --check-inputs-only
```

Run the selected analysis with the same explicit profile:

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma5m_postprocess_20260811/code/analyze_gamma5m_prompt_tes.py --profile prefix76
```

Use `--profile stage5` for the full checkpoint. Existing output directories are
never overwritten.

Tests, including synthetic prefix integration and retained batch0000 read-only
SIM parsing:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s engineering/particle_source_unit_repair_20260811/gamma5m_postprocess_20260811/tests \
  -p 'test_*.py' -v
```
