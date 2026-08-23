# WP2: modular PARMA atmospheric-annihilation-511 repair

## Technical result

This package repairs only the atmospheric annihilation line.  It does not
rerun or replace the retained photon continuum, prompt, delayed, focused-signal,
or other-particle modules.

The archived official PARMA routines give, for the explicit day-15 authority
tuple,

- line energy: `0.51099895 MeV` (`510.99895 keV` in a Cosima source card);
- full-sphere integrated line flux:
  `0.16651547160226118 ph cm^-2 s^-1`;
- PARMA `mu < 0` fraction: `0.8232197530929204`;
- PARMA `mu > 0` fraction: `0.1767802469070797`;
- positive-to-negative hemisphere ratio: `0.21474247458579357`.

PARMA defines `mu=-1` as upward and `mu=+1` as downward.  For the retained
Cosima convention, `theta=acos(mu)`, so `theta=0 deg` is the downward source
direction.  The 20-, 40-, and 80-bin source fractions each sum to unity to
better than `5e-16`; the line-flux closure is better than
`9e-17 ph cm^-2 s^-1`.

The source-level gate is `PASS_PARMA_511_SOURCE_LEVEL_ONLY`.  A dedicated O8
campaign then transported only this monoenergetic atmospheric-line module:
60 independent batches of 3,000,000 triggers, all with `Spectrum Mono
510.99895`.  The merged exposure is 180,000,000 triggers and
`95575.47507199999 s`.  Under the frozen 420-eV response and selection it gives
663 final W511 events, `0.006936926021037709 cps`, a counting RSE of
`3.883678%`, and a 40/80-bin combined relative difference of `0.121477%`.
The dynamic detector-rate gate therefore passes.

This is a pass for the corrected atmospheric-511 line module, not for the
entire retained photon model or for manuscript headline numbers.  The retained
broadband photon module contains the old broad-bin line term, and a raw-SIM
audit found that its `_2602units` energy abscissae were divided by 1000 a second
time: the line term was transported at 0.44965--0.71264 keV.  It is removed
exactly once by offline reweighting; its Broad480--550/W511 selected-rate
correction is exactly zero, while its active-only/TES-zero accidental occupancy
is subtracted with the retained `prompt_scale_gamma`.  This does not certify
the remaining legacy photon continuum energy axis.

The final offline modular recomposition removes the old
`0.0015552613519498118 cps` sidecar once, retains all
prompt/delayed/signal/other-particle modules, and
adds the corrected line rate.  Its day-15 background is
`0.012346528209026033 cps`.  The conditional 20-day fold gives
`S=1650.787710238136`, `B=20734.191748070585`, and `Z=11.464303417952294`.
These are explicitly not publication authority while the scientific blockers
listed below remain.

## Execution scope

The user's modular-simulation clarification supersedes the full-chain run
recommendations in the session handoff:

| Item | This work package |
| --- | --- |
| PARMA 511-keV source calculation | Recomputed from archived official routines |
| 20/40/80 equal-mu source tables | Generated and closed at source level |
| Corrected line-only O8 response | Dedicated 60 x 3M mono-line campaign; detector-rate gate PASS |
| Retained broadband gamma | Offline misplaced line-term removal only; zero Broad/W511 delta; no continuum transport |
| Prompt/delayed/signal/other particles | Reused unchanged; no transport |
| Finite-M validation | Existing tables/SIM/catalog/response only; zero transport |
| Full-chain or all-particle rerun | Not performed and not authorized |

The `.inc.source` files under `line/` deliberately contain no `Geometry`,
`Run`, `Events`, or `FileName` directive.  They cannot launch transport on
their own.

For strict module comparability, any line-response analysis uses the retained
O8 Step05 predicate unchanged.  A separate audit found that its
`ACTIVE_SHIELD` substring rule also matches passive
`ActiveShield_S3C_BGO_Kapton_*` scorer volumes.  Thus the historical 50-keV
mask is not a pure BGO+plastic scintillator veto.  This package records that
selection defect as a blocker; it does not silently repair the predicate or
reprocess any other module.

## Final authority, cleanup, and residual boundaries

The authoritative campaign state is the complete 0--59 aggregate receipt and
its dynamic `response.primary_gate`, not the producer's static top-level
`PREPARED` or `DIAGNOSTIC_ONLY` strings.  The response summary's dynamic gate
is independently reconstructed from the primary event CSV and must agree with
the receipt.  The prepared supplement campaign was never executed and
contributes no event, exposure, or rate to the 180M result.

Four external cleanup receipts cover exactly batches 0--59 without overlap.
All 60 nominal raw SIM files are absent; the removed raw total is
48,600,153,913 bytes and is not locally recoverable.  The 60 source cards,
seeds, compressed logs, compact event products, provenance, response products,
and original raw sizes and SHA-256 records remain.  Campaign records saying
`raw_deleted=false` describe their pre-cleanup state; the four external
receipts are the post-campaign cleanup authority.

WP1 used only the retained source tables, SIM catalogs, and response products.
It remains
`CONDITIONAL_OFFLINE_FINITE_M_VARIANCE_ESTIMATE__NOT_HANDOFF_TRANSPORT_PASS`,
not `PASS_M_SAMPLING`: the independent-family finite-M CV point estimate is
2.6244% with an approximate 5.8389% upper bound, but there is only one frozen M
realization and the retained delayed-transport counting precision is
insufficient for the handoff's original multi-M transport gate.

The 20-day line fold evaluates the PARMA flux along retained depths but holds
the day-15 detector angular response fixed; it is therefore a conditional
mission model.  Separately, the retained focused-signal EventList begins at the
Be-window selection surface, so it does not validate transmission through the
complete upstream plastic/BPE outer envelope.  Neither limitation authorizes a
broader rerun in this work package.

The atomic finalization package is under
`response/wp2_final_180m_20260811/`:

- `PARMA_ATM511_CONCLUSION.md` (`a47abd7f...52ad73`);
- `wp2_final_summary.json` (`e62e937d...0191a0`);
- `wp2_output_manifest.json` (`f3887cb8...99cf7a`), which anchors 812 validated
  input evidence files.

The cross-WP0/WP1/WP2 handoff index is
`../FINAL_HANDOFF_MANIFEST_20260811.json`; it binds the subordinate manifests,
cleanup receipts, protected hashes, final outputs, user scope override, and all
remaining scientific blockers.

## Day-15 authority and resolved metadata conflict

The frozen explicit input is stored in
`config/day15_environment_authority.json`:

```text
date=2025-08-31
latitude=34 deg, longitude=100 deg, altitude=38.75 km
W=114.6 MV, Rc=11.6 GV, X=3.4614689720143224 g cm^-2
g=0.15
```

The archived routines independently reproduce `W=114.6` and `Rc=11.6`.
`getdcpp(38.75,34)` instead gives `3.501195617 g cm^-2`, whereas the retained
day-15 mission trajectory gives `3.4614689720143224 g cm^-2`.  This package
selects the retained trajectory depth explicitly so the correction changes
only the modular atmospheric-511 component.  It does not import either the old
38-km `W=118.3` EXPACS row or the separate 38-km `X=3.8650985` scenario.

The line flux function does not take `g`.  At the line energy, the photon
angular checksum is also numerically identical for `g=0`, `0.15`, and `10`;
the saved comparison is `data/g_parameter_sensitivity.csv`.

## Reproduction

From this directory:

```bash
python3 code/build_parma511_source_package.py
```

The program compiles `code/parma511_driver.cpp` against the unmodified archived
`subroutines.cpp`, runs only `getHPcpp`, `getrcpp`, `getdcpp`,
`get511fluxCpp`, and `getSpecAngFinalCpp`, and regenerates all source-level
tables.  It never calls `getSpecCpp`, an event generator, Cosima, or a retained
runner.

The expected one-line receipt is:

```json
{"generated_files": 14, "line_flux_ph_cm2_s": 0.16651547160226118, "mu_negative_fraction": 0.8232197530929204, "mu_positive_fraction": 0.1767802469070797, "status": "PASS_REPRODUCIBLE_SOURCE_ONLY_BUILD_NO_SIMULATION"}
```

## Evidence map

| Evidence | Purpose |
| --- | --- |
| `vendor/README_PROVENANCE.md` | Official download URL, banner caveat, and hashes |
| `config/day15_environment_authority.json` | One explicit metadata authority and the depth discrepancy |
| `data/parma_line_closure.json` | Machine-readable source-level conclusion and gate status |
| `data/angular_convergence.csv` | 20/40/80 integration closure |
| `data/g_parameter_sensitivity.csv` | `g=0,0.15,10` invariance check |
| `line/parma511_day15_*bins.csv` | Exact source fractions and fluxes |
| `line/PARMA_atm511_day15_fullsphere_*bins.inc.source` | Non-executable source fragments |
| `data/build_manifest.json` | Compiler, source hashes, binary hash, and output hashes |
| `response/existing_o8_line_module_reweight_audit.md` | Read-only old line-only reuse/statistics audit |
| `data/o8_prompt_gamma_line_dedup_audit.json` | Machine-readable retained broadband-gamma lineage, unit-axis, and offline line-term audit |
| `response/O8_PROMPT_GAMMA_LINE_DEDUP_AUDIT.md` | Human-readable proof that the misplaced term has zero Broad/W511 effect |
| `transport/campaigns/o8_parma511_line_nominal_180m_20260810/aggregate/wave_0000_0059_f00f57c40852/campaign_aggregate_receipt.json` | Complete 60/60 compact campaign receipt and dynamic line-rate gate |
| `transport/campaigns/o8_parma511_line_nominal_180m_20260810/aggregate/wave_0000_0059_f00f57c40852/response/response_64seed_summary.json` | Frozen 420-eV response, primary counts, 20/40/80 angular checks, and analysis replicas |
| `recomposition/outputs/final_line_campaign_180m_20260811/recomposition_manifest.json` | Offline single-module replacement, occupancy correction, protected hashes, and output hashes |
| `recomposition/outputs/final_line_campaign_180m_20260811/RECOMPOSITION_RESULT.md` | Human-readable day-15 and conditional 20-day result |

## Claim boundary

Safe now:

- PARMA natively provides a single atmospheric annihilation line at
  `0.51099895 MeV`;
- the stated day-15 line flux and angular fractions are reproducible from the
  archived code;
- only one discrete line family has been generated here;
- the corrected atmospheric-line O8 module passes its count/RSE and 40/80
  angular-response gates at the stated frozen response and selection;
- the old broadband line term is offline identifiable and has exactly zero
  Broad480--550/W511 selected-rate contribution;
- M sampling used no new simulation, and no continuum, prompt, delayed,
  activation, signal, other-particle, geometry-A/B, or full-chain simulation
  was started.

Not safe yet:

- treating the recomposed total background or mission sensitivity as
  publication authority;
- treating the factor-1000 legacy broadband-gamma energy axis as a physically
  validated continuum;
- describing the frozen 50-keV mask as a pure BGO or BGO+plastic veto while
  its name predicate also includes passive Kapton wrappers;
- treating response-seed replicas as independent transported photons.
