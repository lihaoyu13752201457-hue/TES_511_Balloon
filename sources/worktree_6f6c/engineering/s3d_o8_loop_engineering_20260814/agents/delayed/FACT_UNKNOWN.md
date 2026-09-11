# S3d-O8 delayed activation independent audit — FACT / UNKNOWN

Scope: existing corrected S3d-O8 day-15 inventory, source-mix table, official
full Step05 delayed lineage, compact delayed catalogs, and existing rich
BUILDUP SIMs.  This is read-only post-processing.  No transport was launched.

## Normalization boundary and definitions

All production denominators remain inside one exact
`geometry × mode × incident-family` cell.  Here that cell is
`S3d_O8 × BUILDUP × f`.

- Parent production rate for inventory key
  `k=(family, source_volume, parent_ZA)` is
  `q_k = sum(RP_k) / sum(TT_S3d_O8,BUILDUP,family)`.  The retained authority
  includes TT from zero-RP DATs.  Families are never pooled.
- `A_k(15 d)` is the transported ground-state day-15 activity in Bq after the
  inventory half-life/saturation fold.  It is not the same quantity as `q_k`.
- Every delayed family transport contains `N_f=250000` realized decays and has
  per-selected-event weight `w_f=A_f/N_f` cps.
- The realized-decay coupling for one exact key is
  `epsilon_k = n_selected,k / N_realized,k` W2 per decay.  Numerically this is
  also cps/Bq when multiplied by an activity with the same source mixture.
- The official observed contribution is
  `r_obs,k = n_selected,k * A_f / 250000`.  If the realized source mixture is
  not identical to the inventory mixture, `r_obs,k/A_k` is **not** a decay
  coupling.
- A full-inventory source-mix screening estimate is
  `r_hat,k=A_k*epsilon_k`.  It is applicable only if the realized locations and
  nuclear states represent the full inventory key and the decay transport is
  unchanged.  Keys with no realized trigger have unknown coupling.  Keys with
  zero selected rows have a finite-sample zero observation, not zero physics;
  `delayed_key_flow.csv` gives the exact one-sided 95% zero-count upper bound.
- Position bubbles show weighted selected contribution.  There is no
  realized-trigger denominator at each exact position, so a bubble is not a
  position-specific efficiency estimate.

## Global closure — FACT

- Official full delayed selection: 420 W2 rows, `0.0544797522273 cps`.
- Event-weight `Neff=28.7537`; 66 distinct source positions; position-rate
  `Neff=24.9280`.  This already fails a promotion-quality `Neff>=30` screen.
- Transported ground activity: `1404.13106873 Bq`; known excited-state holdout:
  `0.09980926898 Bq`.
- All 420 selected rows matched a compact-catalog source coordinate and parent
  key.  Every one of the eight family transports closes to 250000 triggers.
- Family activities (Bq): alpha 280.414464, e- 0.780764, e+ 3.754846,
  gamma 8.170116, mu- 0.250163, mu+ 1.47783e-5, n 348.222164,
  p 762.538537.

## Component production/activity to W2 — FACT with statistical status

`W2/Bq` below is `r_hat / coupling-supported Bq`, i.e. an activity-weighted
mean of exact-key `epsilon_k`; it is not obtained from `r_obs/full Bq`.

| component | production rate (s^-1) | day-15 Bq | official W2 cps (share) | source-mix-screen W2 cps | supported W2/Bq | Bq coverage | position Neff | largest position share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MXC 50 mK plate | 28.51245 | 20.28089 | 0.01677150 (30.78%) | 0.01878838 | 9.7573e-4 | 94.95% | 7.773 | 18.19% |
| Nb inner cylinder | 4.31151 | 1.01631 | 0.00780860 (14.33%) | 0.00756042 | 9.6299e-3 | 77.25% | 2.953 | 39.06% |
| 50 mK can bottom | 9.85412 | 6.77797 | 0.00401569 (7.37%) | 0.00434965 | 7.0777e-4 | 90.67% | 3.133 | 34.69% |
| L5 Cu support | 0.07960 | 0.04990 | 0.00305015 (5.60%) | 0.00099809 | 2.0000e-2 | ~100% | 1.000 | 100% |
| L0 Cu disk | 0.37160 | 0.24489 | 0.00584951 (10.74%) | 0.00748044 | 4.4067e-2 | 69.32% | 2.194 | 47.62% |
| L2 Cu support | 0.12225 | 0.07236 | 0.00139289 (2.56%) | 0.00131993 | 5.8824e-2 | 31.01% | 1.000 | 100% |
| Mu-metal outer cylinder | 4.70608 | 1.15215 | 0.00776545 (14.25%) | 0.00548405 | 7.5698e-3 | 62.88% | 2.930 | 39.28% |
| Ag sinter proxy | 4.63560 | 4.56151 | 0.00112166 (2.06%) | 0.00096842 | 2.2551e-4 | 94.14% | 1.000 | 100% |

The component source-mix screen sums to `0.05422752 cps`, close to the official
rate only by coincidence: unsupported keys are zero-imputed.  It is a ranking
screen, not a replacement authority.

The n/p/alpha day-15 activity split is also not neutron-primary dominated:

| component | n Bq | p Bq | alpha Bq | official n / p / alpha W2 cps |
|---|---:|---:|---:|---:|
| MXC | 5.1521 | 10.4024 | 4.0499 | 0.009750 / 0.006100 / 0 |
| Nb inner | 0.1720 | 0.6006 | 0.2217 | 0.001393 / 0.006100 / 0 |
| can bottom | 1.8999 | 3.1979 | 1.4840 | 0.002786 / 0 / 0.001122 |
| L0 | 0.1346 | 0.1017 | 0.0009 | 0.005572 / 0 / 0 |
| Mu-metal | 0.2903 | 0.6193 | 0.1886 | 0.001393 / 0.006100 / 0 |
| Ag proxy | 1.3790 | 2.1570 | 0.9273 | 0 / 0 / 0.001122 |

Zeros in the last column are finite decay-transport observations, not absent
production.  Since incident p/alpha cascades make many of their Cu parents via
secondary neutrons, an external-shield argument based only on the incident-n
family would miss the larger p/alpha production activity in several near-TES
components.  The reproducible 48-row split is
`delayed_component_family_summary.csv`.

Seven separate proton-family source positions each carry
`0.00305015415 cps` (5.60% of the entire delayed rate): MXC Cu-61, MXC Cu-62,
L5 Cu-64, Mu V-46, Mu Fe-53, Nb Y-85, and Nb Zr-85.  These are explicit
single-event high-weight controls in `delayed_position_bubbles.csv`; no smooth
heatmap may hide them.

For the MXC plate, all 21 official source positions give:

- `r<3 cm`: 51.99% of MXC selected contribution;
- `r<7.62 cm`: 62.15%; therefore 37.85% lies outside 7.62 cm;
- negative local-z face: 73.04%.

These are contribution fractions, not position-denominator efficiencies.  The
full official selection therefore falsifies the categorical claim that all MXC
hot contribution is confined to `r<7.62 cm`; it does not by itself prove an
outer-radius cut.

## Existing INIT -> RP production origins — FACT

The rich BUILDUP SIMs do contain a per-history association: one `ID` encloses
one `IA INIT` and its `CC IP RP` records.  The scan retained 577 requested RP
records and closed exactly to all targeted inventory keys (zero mismatches).

Denominators for every energy/direction cell are all INIT primaries in the same
family, not selected W2 events:

| family | all INIT primaries | sum TT (s) |
|---|---:|---:|
| n | 232991 | 44.5656746 |
| p | 25448 | 20.0382191 |
| alpha | 4343 | 33.6719935 |

InstrumentFrame is `World Ry(+45 deg)`.  `theta` is measured from IF `+x` and
azimuth is `atan2(IF_z, IF_y)`.  Denominator bins are one energy decade,
30 degrees in theta, and 45 degrees in azimuth.  Exact denominators are in
`incident_primary_energy_direction_denominators.csv` and joined product rates
are in `target_production_energy_direction_rates.csv`.

Across the requested Cu components (MXC, can, L0, L2, L5), the parent-producing
primary distributions conditioned on an RP are:

| incident family | parent | RP | day-15 Bq support | primary E median (GeV) | theta range | dominant simulated production mechanism |
|---|---|---:|---:|---:|---|---|
| n | Cu-61 | 15 | 0.33658 | 1.009 | 31.3–149.2 deg | 9 neutronInelastic; remainder p/pi secondaries |
| n | Cu-62 | 55 | 1.23413 | 1.361 | 8.9–168.3 deg | 51 neutronInelastic |
| n | Cu-64 | 161 | 3.61265 | 0.216 | 9.9–175.2 deg | 111 nCapture + 46 neutronInelastic |
| p | Cu-61 | 24 | 1.19771 | 16.201 | 11.1–126.9 deg | 14 neutronInelastic + 6 protonInelastic |
| p | Cu-62 | 55 | 2.74475 | 17.024 | 5.6–132.1 deg | 44 neutronInelastic |
| p | Cu-64 | 118 | 5.88875 | 18.672 | 8.3–138.0 deg | 84 nCapture + 31 neutronInelastic |
| alpha | Cu-61 | 13 | 0.38608 | 31.800 | 36.9–127.5 deg | 8 neutronInelastic; sparse remainder |
| alpha | Cu-62 | 37 | 1.09884 | 41.594 | 21.4–169.8 deg | 32 neutronInelastic |
| alpha | Cu-64 | 77 | 2.28677 | 36.334 | 7.6–135.1 deg | 52 nCapture + 22 neutronInelastic |

Thus high-energy incident protons/alphas mostly make the Cu parents through
secondary neutrons; they are not predominantly direct p/alpha transmutations.
The stated energy/theta values are RP-conditioned distributions.  They are not
incident spectra; the denominator-complete cell rates must be used for any
direction claim.

Sparse Nb/Y/Co lineages (energy, theta, azimuth in InstrumentFrame) are:

- `p -> Y-85` in inner Nb: two RP, `0.09980927 Bq`.  One direct
  protonInelastic history at 24.2949 GeV, 73.54 deg, 225.40 deg
  (501 primaries in its bin / 25448 p total); one secondary pi-minus
  capture-at-rest history at 88.4452 GeV, 58.91 deg, 159.65 deg
  (791/25448).  Decay transport: 1 W2 / 39 realized triggers,
  `epsilon=0.025641`, official `0.00305015 cps`.
- `n -> Nb-89` in inner Nb: two RP, `0.04487759 Bq`.  A secondary-proton
  inelastic history at 35.0447 GeV, 37.35 deg, 14.93 deg (181/232991), and a
  pi-minus inelastic history at 345.051 GeV, 98.60 deg, 326.38 deg
  (68/232991).  Decay transport: 1/34, `epsilon=0.029412`,
  `0.00139289 cps`.
- `p -> Nb-89`: two secondary-neutron inelastic RP at 11.1634 and 16.8149 GeV
  (direction bins 484/25448 and 853/25448), `0.09980927 Bq`; 0 W2 / 46
  realized triggers.  This is only a zero observation; the exact one-sided 95%
  coupling upper bound is 0.06305.
- `p -> Nb-90` ground state: two secondary-neutron inelastic RP at 10.7548 and
  12.6485 GeV (861/25448 and 308/25448), `0.09980927 Bq`; 0/64 and a 95% upper
  bound 0.04573.  The separate `eplus -> Nb-90` key has `0.02197083 Bq`,
  21/3955, and `0.000315407 cps`; eplus production ancestry was outside the
  requested n/p/alpha scan.
- `alpha -> Nb-89`: two pi-secondary RP at 25.8765 and 68.0715 GeV
  (64/4343 and 256/4343), `0.05939654 Bq`; 0/39 and a 95% upper bound 0.07394.
- `n -> Co-54` in outer Mu-metal: one RP, `0.02243879 Bq`, made by a secondary
  pi-plus inelastic interaction from a 2.55137 GeV primary at 32.93 deg,
  74.22 deg (318/232991).  Decay transport: 1/19, `epsilon=0.052632`,
  `0.00139289 cps`.  A separate MXC Co-54 RP came from a 0.109174 GeV neutron
  at 143.55 deg, 303.61 deg (1185/232991) and gave 0/25 selected decays.

`creator_process` and `interacting_particle` are Geant4 truth fields attached
to `CC IP RP`.  They identify the simulated mechanism; they are not evaluated
nuclear cross sections.

## UNKNOWN / unique promotion blocker

INIT-to-RP ancestry is **not** missing.  The unique blocking evidence is a
candidate-vs-control estimate of the joint quantity
`candidate production Bq × candidate realized-decay coupling` with adequate
independent production histories and source positions.  Current component
position Neff is below 8 for every named component; L5, L2 and Ag are one
selected position each, while the decisive Nb/Y/Co production chains contain
only one or two RP histories.

Minimum falsifiable focused proof, before a full chain:

1. Use identical weighted INIT phase-space lists for baseline and candidate in
   only the n/p/alpha energy-theta-azimuth cells appearing in
   `target_production_energy_direction_rates.csv`.  Keep each family TT and
   source weight separate.  Oversampling rare cells is allowed only with an
   explicit inverse sampling weight.
2. Rebuild only affected parent inventories: MXC/can/L0 Cu-61/62/64, inner-Nb
   Y-85/Nb-89/Nb-90, and Mu Co-54.  For every path capable of contributing more
   than 10% of delayed W2, require production-history Neff >=30 and no history
   above 10% of its path weight; otherwise report a confidence bound, not a
   point reduction.
3. Transport the candidate's own source mixture for those exact keys until the
   selected-event and selected-position Neff are each >=30 with no position
   above 10%, or until the one-sided 95% upper bound is already below its
   allocated W2 budget.  Apply the unchanged common response and Step05 gates.
4. Only then combine prompt + delayed and run the candidate's own focused S20
   signal replay; recompute central F3 and require
   `F3 <= 3e-5 photon cm^-2 s^-1` under the same geometry/mode/family
   normalization boundary.

Falsifiers:

- The MXC-first hypothesis is falsified if a denominator-complete paired run
  removes its apparent reduction or moves the dominant joint Bq×coupling to a
  different component at Neff >=30.
- Any L5/L2/Ag-driven geometry claim is falsified unless its present one-point
  hotspot independently replicates; L5 additionally has a realized/inventory
  mix ratio of 3.056, so its official contribution is inflated relative to the
  inventory screen.
- A directional shielding claim is falsified if the denominator-complete
  product rate is broad in azimuth or the candidate does not reduce both the
  affected parent Bq and the realized W2 coupling.

Delayed-only LOOP verdict:

- **KEEP** MXC as the sole first localization target: it is the largest
  aggregate named component in both official (30.78%) and source-mix-screened
  (34.65%) rankings and has 21 positions rather than one.
- **MODIFY** Nb/can/L0/Mu claims to monitored secondary controls; their current
  rates are physically possible but low-Neff, and Nb/Mu changes also require
  non-activation magnetic/mechanical evidence.
- **KILL** L5/L2/Ag and the categorical `MXC r<7.62 cm only` statement as design
  drivers on the present sample.  This kills the inference, not the hardware.

No delayed geometry is promoted by this audit alone.

## Durable small artifacts

- `delayed_position_bubbles.csv`: 66 selected source-position bubbles with
  correct component-local axes and explicit single-event flags.
- `delayed_production_to_w2_flow_compact.csv`: 76 exact family/volume/parent
  paths (all selected paths plus requested zero-selected parents).
- `delayed_component_summary.csv`: 9 component rows.
- `delayed_component_family_summary.csv`: 48 component-by-family rows.
- `delayed_material_summary.csv`: material-class production/activity/coupling.
- `DELAYED_CANDIDATE_NECESSITY.md` and `delayed_candidate_necessity.csv`:
  optimistic 100%-removal budget ceilings and the single engineering blocker.
- `delayed_key_flow.csv`: complete exact-key denominator audit and zero-count
  upper limits.
- `target_production_origin_events.csv`: 577 retained INIT->RP truth rows.
- `incident_primary_energy_direction_denominators.csv`: 988 denominator cells.
- `target_production_reaction_summary.csv` and
  `target_production_energy_direction_rates.csv`: process and
  denominator-joined rate summaries.
- `audit_summary.json` and `origin_scan_audit.json`: closure verdicts.
