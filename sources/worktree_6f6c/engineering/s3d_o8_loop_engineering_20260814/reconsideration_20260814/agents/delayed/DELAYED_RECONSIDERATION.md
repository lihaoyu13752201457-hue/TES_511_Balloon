# S3d-O8 delayed reconsideration: AF1-48 reverse budget and focused falsifier

Status: **MODIFY / ENGINEERING-CONDITIONAL OPTIMUM; not yet promoted.**  This is
read-only post-processing of the official S3d-O8 lineage and mission fold.  No
transport was launched.

## Technical summary

The earlier conclusion that “even perfect all-Cu removal fails, therefore no
simple candidate exists” is too strong.  Exact removal of the final 48-volume
candidate's incumbent Copper term leaves `29552.2862` background counts,
`2479.2776` counts or 9.16% above the unchanged-signal gate.  But those 47
residual selected events have mission-integrated event `Neff=7.339`; the
largest single event is `5017.1640` counts, and the excess is only `0.227` of
the diagnostic event-weight concentration scale.  This is an observed-central
FAIL, not a statistical KILL.

The component-deletion screen also freezes production, source host, decay
coupling, and active-veto response.  It therefore cannot rule out a coherent
topology that simultaneously removes near-TES Cu parents, changes where 511 keV
partners are absorbed, reduces the Nb/Mu selected term, moderates incident
secondaries with existing BPE, and catches prompt partners with the existing
BGO channel.

The single preferred topology for focused falsification is **AF1-48**:

- the explicit 48-volume non-readout cold-core passive Copper whitelist is
  changed in place to the existing elemental `Aluminium` material;
- the 11 XS400 above-4 K/manifold Copper volumes and the remote precool flex
  link remain Copper;
- Nb and Mu-metal sleeve/back-cap walls are reduced from 2.0 to 0.5 mm while
  retaining their inner surfaces;
- released mass adds a 5 mm, 3.744 kg liner of the same BPE at the certified
  inner annulus while the original outer BPE remains unchanged; the existing
  top BGO channel is extended inward with the actual service reliefs retained.

The frozen proxy setup is
`agents/geometry/candidate_proxy/S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup`.
The separate 60-Copper-volume prototype is **stale/KILL** for this decision: its
extra 12 substitutions have no observed Copper W2 credit and only add Al
activation and thermal-interface risk.

Elemental Al is the sole preferred transport material.  “6061” is not allowed
to reuse an elemental-Al card: Mg/Si/Cu/Cr/Fe impurity parents would be omitted.
6061 remains only an optional comparator after an exact alloy card exists.

The unique first go/no-go blocker for the Cu-to-Al delayed lever is the candidate's own
`new-Al production/activity × exact-position realized W2 coupling`.  The
nominal 95% net Cu-term suppression is arithmetically possible but aggressive;
existing far-away Al gives no transferable bound for Al placed at the MXC,
50 mK can, L0, and cold-plate positions.

The candidate's focused 511 signal has now been measured: 37194 trials gave
27855 baseline and 27993 candidate selections, retention `1.00495422725`.
This sets `S20_candidate=1653.53937791` and the candidate-own exact gate
`B20,max=27341.9247429`.  It resolves the signal coordinate only; prompt, Cu,
Nb/Mu, and new-host background suppressions remain unmeasured hypotheses.

## Authority, normalization, and strict definitions

All joins stay inside `S3d_O8 × BUILDUP × incident family`; decay response stays
inside exact `geometry × family × parent_ZA × source-volume/source-position`
keys.  Families are never pooled.

For inventory key `k=(family, volume, parent_ZA)`:

- production rate is `q_k=sum(RP_k)/sum(TT_geometry,BUILDUP,family)` in s^-1,
  including TT from zero-RP DATs;
- `A_k(15 d)` is the activity after the half-life/saturation fold in Bq, not
  the production rate;
- realized-trigger coupling is
  `epsilon_k=n_selected,k/N_realized,k` W2 per decay, numerically cps/Bq only
  for that same source mixture and position;
- mission counts are the time fold
  `C20,k=sum_t A_k(t)*epsilon_k*quadrature_weight_t*live_t`.

Thus “production Bq” and `W2/Bq` must be reported separately.  A candidate
selected-term suppression is a product of its activity ratio and coupling
ratio; it cannot be called a pure coupling reduction unless activity is held
fixed.

The official mission decomposition closes exactly:

| baseline term | 20-day counts |
|---|---:|
| prompt | 55398.979434 |
| exact geometry-material Copper | 59252.576459 |
| Nb + MuMetal | 27605.141950 |
| fixed other, including retained CuNi + Ag | 1947.144243 |
| total | 144203.842086 |
| unchanged-signal count gate `(S20/10)^2` | 27073.008579 |

All 373 exact-Copper selected rows and all 11 selected Copper source volumes
lie inside the 48-volume whitelist.  The older `59276.314267` “all-Cu” audit
bucket additionally contains one CuNi event worth `23.737807` counts; AF1-48
retains CuNi, so that event remains in `Other`.

The 48-volume baseline inventory is `161.530445 s^-1`, `110.079477 Bq` at day
15, and 4749 RP.  Incident n/p/alpha contribute respectively `28.581429`,
`58.172266`, and `20.454266 Bq`, together 97.39% of this activity.

## Why the 9.1% all-Cu excess does not KILL

| scope | rows | 20-day counts | event Neff | largest event | diagnostic sqrt(sum w^2) |
|---|---:|---:|---:|---:|---:|
| baseline delayed | 420 | 88804.8627 | 28.6867 | 5017.1640 | 16580.4480 |
| exact Copper | 373 | 59252.5765 | 22.5179 | 5017.1393 | 12486.5701 |
| residual after exact Cu removal | 47 | 29552.2862 | 7.3392 | 5017.1640 | 10908.5665 |
| Nb + MuMetal | 45 | 27605.1420 | 6.6094 | 5017.1640 | 10737.6332 |

The mission fold reuses each selected event across time nodes, so
`sqrt(sum w^2)` is a weight-concentration diagnostic, not a formal cumulative
Monte Carlo confidence interval.  Nevertheless, a central excess smaller than
one quarter of that scale, controlled by `Neff<8`, cannot support a categorical
no-solution verdict.  The corrected decision is **MODIFY / unresolved** and
requires a matched candidate sample.

The shared-lever objection is physical, not accounting rhetoric.  Perfect
removal sets each old selected row to zero but does not simulate:

1. Al replacing Cu as the production and 511-interaction host;
2. Nb/Mu thinning changing both parent Bq and `W2/Bq`;
3. inner BPE changing the n/p/alpha secondary cascade;
4. top BGO changing whether the prompt annihilation partner makes an active hit.

These effects can help or hurt and must be measured together.  This is exactly
why neither the 9.1% central deficit nor a source-mix central pass promotes the
candidate.

## Joint mission feasible region

Define

`B20 = P(1-sP) + C(1-sCu_old) + M(1-sNM_eff) + O + Delta_new`,

where `P,C,M,O` are the four baseline terms above.  `sCu_old` suppresses only
the incumbent 48-volume Cu-parent contribution; replacement-material counts
enter nonnegative `Delta_new`.  For magnets,

`sNM_eff = 1 - (A_candidate/A_baseline)*(epsilon_candidate/epsilon_baseline)`.

The signal-retention screen uses
`Bmax(rS)=27073.008579*rS^2`; final promotion must instead use the candidate's
own `(S20_candidate/10)^2`.

Selected zero-new-host boundaries are:

| signal retention | prompt suppression | Nb/Mu effective suppression | minimum incumbent-Cu-term suppression | new-host headroom at 100% old-Cu removal |
|---:|---:|---:|---:|---:|
| 1.00 | 0.80 | 0.75 | 0.87942 | 7144.78 counts |
| 0.95 | 0.80 | 0.75 | 0.92397 | 4505.16 counts |
| 0.95 | 0.90 | 0.50 | 0.94694 | 3143.78 counts |
| 0.95 | 0.90 | 0.75 | 0.83047 | 10045.06 counts |
| 0.95 | 0.95 | 0.50 | 0.90019 | 5913.73 counts |

As a conservative pre-signal sensitivity point,
`(rS,sP,sCu_net,sNM_eff)=(0.95,0.80,0.95,0.75)`, the exact 48-volume budget is:

| term | candidate-screen counts |
|---|---:|
| prompt | 11079.795887 |
| replacement + remaining-Cu term, capped at 5% of old Cu | 2962.628823 |
| Nb + MuMetal | 6901.285488 |
| fixed other | 1947.144243 |
| total | 22890.854440 |
| candidate screen gate | 24433.390243 |
| central margin | 1542.535803 |

Equivalently, with the other three assumptions fixed, net Cu suppression must
be at least 92.3967%.  Complete removal of the old Cu term permits at most
`4505.164626` new-host counts; the nominal net-95% point allocates only
`2962.628823` counts (`0.00175194` baseline-live rate-equivalent cps) to all
replacement/remaining-Cu counts and keeps the 1543-count margin.  These are
budget allocations, not transport predictions.

### Candidate-own focused-signal row

Using the measured candidate signal rather than the 95% sensitivity assumption,
while retaining the still-unmeasured background assumptions
`(sP,sCu_net,sNM_eff)=(0.80,0.95,0.75)`, gives:

| quantity | candidate-own value |
|---|---:|
| focused trials | 37194 |
| baseline / candidate selected | 27855 / 27993 |
| signal retention | 1.00495422725 |
| candidate S20 | 1653.53937791 |
| exact candidate gate | 27341.9247429 counts |
| arithmetic residual background | 22890.8544399 counts |
| central margin | 4451.0703031 counts |
| gate ratio | 0.837207134 |
| minimum Cu-net suppression at `sP=.80, sNM_eff=.75` | 0.874879717 |
| full-old-Cu-removal allowance for new Al/migration | 7413.6991260 counts |

The residual does not change because the background suppression coordinates
have not been rerun; only the allowable gate changes.  Therefore this row is a
measured signal result plus a background counterfactual, not a candidate
background PASS.

## Al activation audit and material decision

Current elemental-Al volumes in the baseline geometry provide a useful hazard
list but not a near-TES coupling measurement:

- production `189.075553 s^-1`; day-15 activity `105.669646 Bq`;
- 85615 realized Al decays and zero selected W2 rows;
- named beta-plus/EC-capable screening parents total `18.730541 Bq`, including
  F-18 `6.947825 Bq`, Al-25 `3.109164 Bq`, Mg-23 `1.990580 Bq`, O-15
  `1.513874 Bq`, Na-21 `1.119877 Bq`, and C-11 `1.038953 Bq`;
- the sum of familywise zero-event 95% rate diagnostics is `0.0193423 cps`.

Those Al volumes are mostly outer/far, whereas AF1-48 places about `6.1122 kg`
of elemental Al at former cold Cu positions.  The zero-event observation is
therefore not transferable.  Its diagnostic upper rate is about 11 times the
nominal AF1-48 replacement allowance.

If the candidate Al inventory happened to be about 100 Bq, the nominal
`2962.63`-count allowance would imply a mission-rate-equivalent coupling proxy
below `1.75e-5 cps/Bq`.  The incumbent 48-volume Copper's static selected-rate
over day-15 activity proxy is `3.30e-4 cps/Bq`, about 19 times larger.  This
does not prove the required Al coupling, because the parent mixtures and time
profiles differ; it quantifies how aggressive net 95% is.

The mass audit gives `20.26989993 kg` Cu becoming `6.11221016 kg` elemental Al
at identical geometry, releasing `14.15768977 kg` for existing BPE/BGO
reallocation.  These masses do not qualify Al thermally or structurally.

Decision:

- **KEEP for focused physics falsification:** existing elemental `Aluminium`.
- **KILL as currently named:** 6061 without an exact alloy material card.
- **OPTIONAL comparator only:** exact 6061 card with explicit impurity
  composition, run with the same histories and decay gate; it is not on the
  elemental-Al promotion critical path.

## Denominator-complete focused proof

The retained rich BUILDUP SIMs do contain INIT-to-RP history ancestry.  Existing
same-family denominators are 232991 n primaries (`TT=44.5656746 s`), 25448 p
primaries (`TT=20.0382191 s`), and 4343 alpha primaries
(`TT=33.6719935 s`).  InstrumentFrame is `World Ry(+45 deg)`; theta is measured
from IF `+x`, and azimuth is `atan2(IF_z,IF_y)`.  Existing cells use one energy
decade, 30-degree theta, and 45-degree azimuth denominators.

The old Cu-61/62/64 parent histories span broad directions rather than a narrow
ray: n-family medians are roughly `0.216–1.361 GeV`, p-family medians
`16.2–18.7 GeV`, and alpha-family medians `31.8–41.6 GeV`, with theta ranges
covering approximately `6–175 deg`.  High-energy p/alpha primaries frequently
make the Cu parents through secondary neutrons.  Consequently the focused run
must retain full INIT denominators; it cannot sample only old selected W2 or
three hot directions.

Minimum critical path, before any full chain:

1. **B1 — isolated Al substitution BUILDUP.**  Use the 48-volume elemental-Al
   geometry without BPE/BGO/magnet changes.  Replay matched n/p/alpha INIT
   phase space, keep each family TT separate, and stratify the populated
   energy-theta-azimuth cells.  Rare-cell oversampling requires an explicit
   inverse sampling weight.  Inventory every positive ground-state Al parent,
   not only a beta-plus shortlist.
2. **D1 — exact-position Al decay.**  Transport B1's own
   `family × parent × volume/position` inventory.  Report production rate,
   day-15 Bq, realized triggers, W2, `W2/Bq`, mission counts, event/position
   Neff, and the largest-event share.  Continue any path capable of more than
   10% of the Al allocation until `Neff>=30` with no event above 10%, or until
   a pre-registered one-sided upper limit already decides the budget.
3. **Immediate Al falsifier.**  The nominal net-95% claim fails if candidate Al
   plus remaining Cu exceeds `2962.628823` counts.  Under the measured
   candidate-own signal gate and the assumed `sP=.80, sNM_eff=.75`, AF1-48 is
   impossible even at complete old-Cu removal if the one-sided conditional
   new-host upper consumes `7413.699126` counts.  Promotion-quality evidence
   should leave at least 1000 counts of headroom rather than balance on one
   event.
4. **B3/D2 — unified affected-material test.**  Only if D1 survives, run the
   single AF1-48 proxy for n/p/alpha.  Inventory added BPE/BGO and thinned
   Nb/Mu separately.  For Y-85, Nb-89, Nb-90, Co-54, and every positive new
   parent, report candidate Bq and `W2/Bq` independently; require the lower-
   confidence joint point to lie inside the feasible frontier.
5. **D3 plus paired prompt/signal.**  Combine only candidate-own focused decay,
   denominator-complete gamma prompt, and focused S20 signal.  Recompute the
   candidate's gate and require central plus the pre-registered conditional
   bound to pass, with no >10% single-event path.  Only then is a full-chain
   run justified.

The optional exact-6061 B2/D1 comparator is run only if engineering rejects
elemental Al.  Calling elemental Al “6061” is itself a falsifier.

## Final delayed verdict

- **KILL:** the stale 60-volume substitution; unmodeled 6061; and the prior
  inference that a 9.1% low-Neff central excess proves no solution.
- **MODIFY/KEEP:** the exact AF1-48 unified proxy, solely as the next focused
  falsification target.
- **ENGINEERING-CONDITIONAL OPTIMUM:** elemental-Al AF1-48 is the single best
  current topology because it creates a joint production/coupling/veto lever
  within the allowed passive hardware and has an arithmetically nonempty
  mission region.

The focused signal coordinate passes and slightly improves the gate, but this
is not a background physics PASS.  The unique first delayed go/no-go blocker is
the exact-position Al inventory-to-W2 result.  If it survives, prompt and
Nb/Mu effective suppression still require candidate transport; if it fails the
allocated count bound, AF1-48 is falsified and there is no second parallel
material recommendation.

## Reproducible artifacts

- `build_delayed_reconsideration.py`: post-processing rebuild and assertions;
- `joint_feasible_boundary.csv` and `joint_feasible_anchor_points.csv`: mission
  feasible region;
- `statistical_reconsideration.csv`: low-Neff/single-event audit;
- `TC_AF1_budget_audit.csv`: exact 48-volume nominal-point budget;
- `current_elemental_Al_*`: current-Al production/activity/zero-event screens;
- `Al_material_option_comparison.csv`: elemental Al versus exact-6061 decision;
- `focused_BUILDUP_exact_decay_test_matrix.csv`: minimum test and falsifiers;
- `suppression_variable_definitions.csv`: strict variable definitions;
- `audit_summary.json`: numerical closure and candidate-scope assertion.
