# Corrected-keV proton P0 six-band weighted pilot

Status: **WAIT; preparation only; zero transport launched.** The review-owned
science contract is not frozen. Consequently the conditional spectra, six
band source cards, and source manifest do not exist and have no authority.
The controller's `--print-plan` path is output-free in this state. This README
and the read-only tests do not authorize source publication or transport.

## Authority boundary and current gates

This package proposes a full-support, six-stratum corrected-keV proton P0
pilot for `mass_model_511` and `s3d_o8`, with separate `instant` and `buildup`
normalization domains. It is a small weighted pilot, **not full statistics**,
not an unweighted full-spectrum sample, and not sensitivity, delayed-response,
or geometry-promotion authority.

The required gates are deliberately fail-closed:

1. `data/proton_p0_sixband_science_contract.json`: **WAIT**. It must freeze
   exactly seven ordered keV edges, six bands, the corrected-parent total Flux,
   and the science interpretation.
2. `spectra/conditional_keV_total/`, `config/source_cards/`, and
   `data/proton_p0_sixband_source_manifest.json`: **WAIT**. The builder may
   publish these only after gate 1. Parent corrected spectra and cards remain
   immutable.
3. Canonical batch0004 final validation report and ledger: **WAIT**. A real P0
   run requires the exact final PASS pair, including its global-contract,
   transport-core, geometry-bundle, and corrected source-contract bindings.
4. P0 dynamic validator and final ledger: **WAIT**. No P0 transport result is
   merge eligible without per-job receipts, per-cell authority, and a final
   clean PASS.

The execution window is inherited from batch0003 and is never reset or
extended: `2026-08-11T14:31:43.664883+00:00` through
`2026-08-12T02:31:43.664883+00:00`. Publication of a later batch0004 PASS does
not create a new P0 wall-time allowance. If the inherited deadline/resource
gates are closed, the controller must remain WAIT/fail-closed.

No raw SIM, DAT, logs, source cards, spectra, contracts, ledgers, or prior
authority may be deleted automatically. The hard disk reserve is **20 GiB**
(`20 * 1024^3` bytes), in addition to remaining-output and active-attempt
margins. Per-attempt and per-file caps are safety bounds, not permission to
delete retained raw artifacts.

## Frozen statistical shape once the science contract passes

The proposed schedule is:

- 2 geometries x 2 modes x 6 bands = 24 cells;
- 256 primaries per cell;
- 4 shards per cell, 64 primaries per shard;
- **96 transport jobs and 6,144 total primaries**;
- one deterministic, globally unique seed per job; retries reuse only that
  job's seed and never create a new statistical contribution.

The bands are equal-*N* strata, not six copies of the parent proton field.
Every derived band card must preserve the parent geometry, source identity,
particle type, Beam direction, and all other active lines byte-for-byte. The
only permitted parent-to-band changes are the 20 `Spectrum File` paths and the
20 Decimal partial `Flux` values proven by the frozen derivation manifest. No
Geant4 production CUT or physics-list change belongs to this pilot.

The corrected parent all-angle Flux is the exact Decimal
`0.1123007216313341 cm^-2 s^-1`; `0.112300721631334` is only a rounded display.
For each angular bin, the first five band Flux values are obtained from the
piecewise-linear band integrals and the sixth is the Decimal residual. Thus the
six partial values close exactly to that angular bin's parent Flux, and all 120
angular-bin/band values close exactly to the corrected-parent total.

## TT and rate contract

Equal event counts do not imply equal exposure. Each band has a different
partial Flux and therefore a different realized Cosima observation time. The
actual TT recorded for every accepted shard/band is authoritative; nominal
`N/(Flux*pi*R^2)` is only a diagnostic.

Prompt rates must be formed per band and then summed:

`rate_prompt = sum_b(selected_count_b / TT_b)`.

Activation production must likewise be accumulated as
`sum_b(RP_b / TT_b)` only within the same geometry, physical volume, isotope,
and nuclear state. Zero-RP bands still require their own valid positive TT and
must remain explicit zero contributions. The forbidden estimator is
`sum_b(count_or_RP_b) / sum_b(TT_b)`, and raw equal-*N* counts must never be
pooled without band Flux weighting. Instant products cannot supply buildup
activation normalization, and no TT may cross a geometry, mode, band, or
attempt boundary.

## Read-only commands at the current WAIT gate

At the present pre-manifest WAIT gate, the main plan command emits a strict-JSON
WAIT record, writes no run artifact, and does not invoke Cosima. After a source
manifest is frozen, plan construction may invoke `cosima --help` solely to
fingerprint the executable; it still never launches transport:

```bash
python3 engineering/particle_source_unit_repair_20260811/proton_p0_sixband_pilot_20260812/code/run_proton_p0_sixband_pilot.py --print-plan
```

The builder plan also emits WAIT while the science contract is absent. Its
exit status is 3 and it writes no spectra, cards, or manifest:

```bash
python3 engineering/particle_source_unit_repair_20260811/proton_p0_sixband_pilot_20260812/code/build_proton_p0_sixband_sources.py --print-plan
```

Run the preparation tests without transport:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s engineering/particle_source_unit_repair_20260811/proton_p0_sixband_pilot_20260812/tests \
  -p 'test_*.py' -v
```

The tests cover all three WAIT paths and absence of authority outputs, exact
schedule/seed closure (including historical operational-pair reservations),
Decimal Flux arithmetic, strict JSON rejection, unchanged CUT-bearing lines,
the resource-limit launcher mapping, synthetic proton/band/geometry SIM scans,
true-veto/TES aggregation, exact source-card allowed differences, write-once
report+ledger pairing, and per-band rate recomposition. They do not execute
Cosima. Once the science contract is frozen, the dynamic validator additionally
replays the complete corrected-parent derivation byte-for-byte before signing
any transport authority.
