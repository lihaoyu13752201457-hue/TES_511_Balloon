# S3d-O8 prompt candidate necessity review

Date: 2026-08-14  
Scope: read-only prompt review; no transport was run.  This note tests whether
the complete existing gamma denominator selects a mass-conserving BGO
redistribution or closure of a thin non-optical region.  It does not treat
`HANDOFF_B` as an authority.

## Decision first

**There is no denominator-supported directional BGO engineering topology in
the present data.**  Keep the current BGO/plastic layout as the prompt
reference.  Kill, as an evidence-selected first candidate, both (i) choosing a
BGO donor/receiver sector from the three survivors and (ii) thickening/closing
the 1 cm top annulus or a relief merely because it is geometrically thin.  A
mass-conserving redistribution can be made geometrically precise, but the data
do not presently tell us which region should donate mass or receive it.

There *is* one precise causal topology:

```text
4--8 MeV incident gamma
 -> crosses a real, thick plastic+BGO chord with zero active energy deposit
 -> first PAIR in an inner passive body
 -> positron stops/annihilates in an inner passive body
 -> one 511 keV photon reaches TES and passes the common response
```

That is a mechanism topology, not a single spatial patch.  Its observed entry
faces, directions, pair hosts, and annihilation hosts are mixed.  Therefore it
does not define a unique BGO topology to manufacture.

Verdicts:

| proposition | verdict | reason |
|---|---|---|
| Retain current 4 cm side / 3 cm bottom / 1 cm top-annulus active geometry as the prompt reference | **KEEP** | All three leaks are stochastic zero-deposit traversals through real active material; no repeatable weak face is established. |
| Mass-conserving directional BGO redistribution chosen from the three leak rays | **KILL** | Each populated leak cell has one survivor; the rays occupy three disjoint energy-direction-grammage cells and two different entry-face classes. |
| Close/thicken the top annulus, service relief, or other non-optical thin region as the first prompt fix | **KILL** | No observed S3d survivor uses the top annulus or a modeled relief; the complete sample contains no leak cluster that points there. |
| Preserve redistribution only as a future predeclared sensitivity test after a named-volume denominator exists | **MODIFY** | Require per-volume chords and an inner-causal-envelope denominator before choosing donor/receiver regions; then test one fixed topology with matched transport. |

## 1. Complete denominator and the three actual active chords

### FACT: normalization and event support

The complete S3d-O8 instantaneous gamma set contains `3,207,738` source
histories in 132 raw SIM jobs and has `TT = 59.0965413 s`.  There are 120
pre-veto W2 events, three exact active-veto survivors, and two Step05 survivors.
The equal event weight is `0.0169214640654 cps`.

For the veto-leak probability, `k/N = 3/3,207,738 = 9.35238e-7`; its exact
one-sided 95% upper is `2.41717e-6`.  Conditional on the 120 pre-veto W2
events, the active escape fraction is `3/120 = 2.5%`, with one-sided 95% upper
`6.334%`.  These are counting statements, not a smooth angular response.

### FACT: true CSG ray intersections to first pair

| event | E (MeV) | entry class | plastic chord (cm) | BGO chord (cm) | active grammage (g cm^-2) | first pair host | annihilation host |
|---|---:|---|---:|---:|---:|---|---|
| 3883 | 4.14829 | bottom | 1.049445 | 3.148334 | 23.434097 | `Nb_MagShield_Inner_Cylinder_2mm` | `MuMetal_MagShield_Outer_Cylinder_2mm` |
| 19932 | 5.76882 | side | 1.322554 | 5.290292 | 38.923306 | `DR_MixingChamber_Cu` | `DR_MixingChamber_Cu` |
| 8081 | 6.34594 | side | 1.010960 | 4.044046 | 29.754013 | `Nb_MagShield_Inner_Cylinder_2mm` | `Cu_SubstrateSupport_SolidDisk_L0_deepest` |

Every exact BGO and plastic scorer records `0 keV` for all three events.  The
primary's first interaction is PAIR in each case; there is no preceding COMP,
PHOT, or RAYL interaction.  Thus these are not threshold leaks and not rays
that avoided the active shield.  They are uncollided tails through 3.15--5.29
cm BGO plus 1.01--1.32 cm plastic.

### FACT: denominator-resolved directions do not repeat

With predeclared bins in energy, equal-solid-angle direction (`mu_x`, azimuth),
and exact total active grammage, the three nonzero cells are:

| event | E bin (MeV) | `mu_x` bin | azimuth bin | active grammage bin (g cm^-2) | N incident | k | one-sided 95% upper on k/N |
|---|---|---|---|---|---:|---:|---:|
| 3883 | 4--5 | 0--0.25 | 45--90 deg | 15--25 | 71 | 1 | 6.51% |
| 19932 | 5--6 | -0.75---0.5 | 270--315 deg | 35--50 | 94 | 1 | 4.95% |
| 8081 | 6--8 | -1---0.75 | 0--45 deg | 25--35 | 92 | 1 | 5.05% |

Each leakage cell has `Neff = 1`.  Removing the grammage axis only increases
their denominators to 867, 702, and 633; it does not create a repeated
direction.  Selecting any of the three sectors after observing the numerator
would be a post-hoc sector, not a denominator-supported hotspot.

The global active-grammage denominator provides an additional falsifier of an
aperture story: `1,924,489` incoming rays have zero chord to their closest
approach and produce zero pre-veto W2 events, while all three leaks occur at
15--50 g cm^-2.  This does **not** prove that every zero-chord ray is harmless;
many simply miss the inner causal envelope.  It does prove that the observed
leaks are not members of the zero-chord population.

### UNKNOWN required for face redistribution

The exact query computes total BGO and total plastic chords; the retained
denominator bins their combined active grammage and the summary retains the two
mean chords.  It does not retain the per-ray named chord vector

```text
(L_side_BGO, L_bottom_BGO, L_top_annulus_BGO,
 L_side_plastic, L_bottom_plastic, L_top_plastic)
```

for every incident ray, nor whether an uncollided ray intersects a predeclared
inner causal envelope.  Direction alone is not a safe proxy for a named CSG
face because the side shell contains window/service/NF2 subtractions and
oblique rays can intersect more than one component.  Consequently there is no
face-specific leakage denominator from which to choose BGO donor and receiver
regions.  The observed face counts (two side, one bottom, zero top) are only a
three-event numerator.

## 2. Inner host mixing rejects a single local patch

The S3d first-pair hosts are Nb, Cu, and Nb; their positrons stop in Mu-metal,
Cu, and Cu.  The independent Mass_model final prompt comparison broadens the
same mechanism rather than localizing it: its six gamma first-pair hosts are
4 K Al bottom cap, Nb inner cylinder, MXC copper cold plate, a stainless-steel
100 mK--Still support rod, L0 copper disk, and the 50 mK copper-can bottom.
The seventh Mass event is an incident positron whose bremsstrahlung pairs in
the Nb back cap.

This supports an `inner passive pair opacity x positron stop x TES solid angle`
mechanism.  It falsifies “Nb cylinder only”, “mixing-chamber Cu only”, and any
claim that moving one local pair host necessarily removes the chain; host
migration is a live failure mode.

## 3. Budget arithmetic: how much prompt attenuation is actually required?

### Official common-response S3d boundary

The official 20-day central values are

```text
S20 = 1645.387753 counts
B20 = 144203.842086 counts
     = P20 55398.979434 + D20 88804.862652
B20,max = (S20/10)^2 = 27073.008579 counts.
```

Here `P20`, `D20`, and `S20` were independently reconstructed from the 81-node
mission timeline as `sum(rate_noacc x accidental_live_factor x
trajectory_quadrature_weight_s)` and reproduce the stored cumulative totals.

Therefore the prompt-only target would be

```text
P20,target <= B20,max - D20 = -61731.854072 counts,
```

which is unphysical.  Even perfect prompt removal gives
`F3 = 5.43340e-5`, and the delayed component would still need a 69.51%
reduction.  The total background must fall by at least 81.23% if the signal is
unchanged.  **Hence no finite BGO transmission suppression of the official
`0.03384293 cps` prompt component can by itself make the total budget
acceptable.**

If, only as an algebraic scale, prompt and delayed were both multiplied by the
same factor, that factor would have to satisfy

```text
r_total <= 27073.008579 / 144203.842086 = 0.187741,
```

an 81.23% suppression.  Applying that common factor to the day-15 prompt rate
would give `0.00635371 cps`, but this is not a prompt-only target and is not a
candidate performance prediction.

### Why the quoted 77.2% is conditional, and the valid rate boundary

Independently repeating the arithmetic for the *frozen selection plus LC2
uniform-activity-mass proxy* gives

```text
S20,frozen = 1490.802230
B20,max    = 22224.912885
D20,proxy  = 15885.526788
P20,current,frozen = 27807.088280
r_prompt <= (22224.912885 - 15885.526788) / 27807.088280
         = 0.227977343,
```

or at least 77.2023% prompt suppression.  This confirms the arithmetic but not
the proxy physics.  In that same frozen-selection boundary, the prompt rate is
`0.016921464 cps`, so the conditional target is `<= 0.003857710 cps`.

Multiplying the official `0.033842928 cps` by 0.227977 gives
`0.007715421 cps`, but that number mixes the official prompt selection with a
different signal and delayed proxy.  It is therefore **not** a valid gate
target and must not be used as such.

## 4. Exponential attenuation is only a scale, not proof

For an effective uncollided BGO attenuation coefficient `mu_eff(E)` or mass
coefficient `kappa_eff(E) = mu_eff/rho_BGO`, a desired prompt transmission
ratio `r` would require

```text
Delta tau = -ln(r)
Delta L_BGO = Delta tau / mu_eff
Delta G_BGO = Delta tau / kappa_eff.
```

For the conditional LC2 arithmetic ratio, `r = 0.227977` and
`Delta tau = 1.47851`.  For the common official total-background scale,
`r = 0.187741` and `Delta tau = 1.67269`.  No numerical thickness is asserted
here because `mu_eff` is not a single known coefficient for this selection: it
depends on 4--8 MeV energy, incidence angle, which interaction deposits enough
active energy, secondary escape, and the downstream pair/annihilation/TES
response.  Moreover, mass conservation means any added optical depth is paid
for by reduced optical depth elsewhere.

The geometry itself shows the scale of the proposed trade: comments in the
canonical geometry give approximately 250.689 kg for the 4 cm side shell,
42.674 kg before relief for the 3 cm bottom, and 4.440 kg before relief for the
1 cm top annulus.  Raising the top annulus from 1 to 3 cm would require about
8.88 kg before relief.  A linearized side-shell donor estimate would reduce the
side thickness by roughly 0.14 cm.  This makes a mass-conserving CAD change
easy to define, but it does not make it evidence-selected: two of the three
observed leaks cross the side shell and none crosses the top annulus.

## 5. Is there one precise prompt engineering topology now?

**No.**  The data define one mechanism but not one spatially localized BGO
solution.  A topology such as “top annulus 1 -> 3 cm, reduce the side outer
radius until exact BGO mass is conserved, preserve the 20.9 cm optical opening
and all service/NF2 reliefs” is precise enough to simulate.  It is not selected
by the denominator and should not be promoted as the first candidate.

The only defensible present prompt choice is therefore:

```text
KEEP the baseline BGO topology;
do not claim a prompt-optimized BGO redistribution;
let a separately justified delayed/engineering candidate carry the next
focused S20 test, with prompt treated as a required falsification gate.
```

## 6. Minimal evidence that could reverse this decision

1. Add named active-volume chord vectors and an inner-causal-envelope flag to
   all `3,207,738` existing gamma INIT rays.  This is a read-only geometry
   calculation, not transport.
2. Predeclare one receiver region and one donor region before looking at new
   survivors.  The receiver must show a leakage excess using its own incident
   denominator; the donor must show low inner-causal coupling, not merely zero
   total active chord.
3. Run exactly one matched baseline/candidate focused S20 gamma campaign only
   after that predeclaration.  Report the candidate/baseline transmission with
   a one-sided interval; do not smooth the `Neff=1` cells.
4. As a counting scale only, if the gate were `r_prompt <= 0.227977` and the
   candidate produced zero Step05 events, the one-sided 95% Poisson upper
   `2.996` implies at least `2.996/(2 x 0.227977) = 6.57` times the present
   baseline-equivalent gamma exposure merely to put the upper ratio below the
   target relative to the two-event central baseline.  Baseline uncertainty,
   non-gamma prompt families, signal change, and systematics require more; this
   is not a promotion-statistics prescription.

## Auditable inputs

- Full denominator summary:
  `engineering/s3d_o8_loop_engineering_20260814/agents/prompt/denominator/gamma_denominator_summary.json`
- E x direction denominator:
  `engineering/s3d_o8_loop_engineering_20260814/agents/prompt/denominator/incident_gamma_E_mux_az_denominator.csv`
- E x direction x exact-active-grammage denominator:
  `engineering/s3d_o8_loop_engineering_20260814/agents/prompt/denominator/incident_gamma_E_mux_az_active_grammage.csv`
- Three exact ray chords:
  `engineering/s3d_o8_loop_engineering_20260814/agents/prompt/prompt_leak_material_chords.csv`
- Three event summaries:
  `engineering/s3d_o8_loop_engineering_20260814/agents/prompt/prompt_leak_event_summary.csv`
- Mass_model final pair-host comparison:
  `engineering/s3d_o8_loop_engineering_20260814/agents/prompt/mass_model_final_prompt_pair_hosts.csv`
- Official mission timeline used for the independent count decomposition:
  `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/06_mission/mission_timeline.csv`
- Canonical S3d geometry:
  `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
