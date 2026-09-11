# S3d-O8 prompt physics audit (independent, read-only)

Date: 2026-08-14

Scope: three S3d-O8 gamma events that survive the exact 50-keV active veto in
measured W2, their complete incident-gamma denominator, and a seven-event
Mass_model_511 final-prompt cross-check.  No transport was run.  The source
tree and raw SIM files were only streamed.

## Bottom line

**FACT:** all three S3d gamma survivors cross a substantial, geometrically
continuous active layer before their first interaction: 23.434, 38.923, and
29.754 g cm-2 of active grammage.  Their raw records contain zero energy
deposit in every one of the six exact active scorers.  The primary gamma is
uncollided until pair production in two Nb locations and one DR copper
location.  A positron then stops/annihilates in Mu-metal or copper, and one
annihilation photon supplies exactly 510.99891 keV to the TES.

Therefore these three are **not evidence for an open active-shield aperture or
"low-active-grammage corridor."**  They are rare stochastic no-interaction
transits through thick active material followed by pair/annihilation in an
inner passive component.  A geometry-hole explanation is falsified for these
three rays.

**FACT:** the six Mass_model_511 final gamma events also pair in internal
passive cryostat/support material (Al, Nb, Cu, stainless steel; no CsI or W
pair host).  This supports the general inner-passive pair/annihilation
topology, but falsifies any claim that the existing evidence uniquely selects
Nb, Mu-metal, or copper as the universal host.

**UNKNOWN:** with only three equally weighted S3d leaks (leakage Neff=3 and
Neff=1 in each occupied direction/energy/grammage cell), their directions
cannot be extrapolated to a solid-angle hotspot and cannot select an
engineering change.  The complete E x direction x exact incoming-active-
grammage denominator is now available, but conditioning makes the nonzero
cells smaller (71, 94, and 92 incident rays) without adding any leak event.

## Authorities and paths

Canonical analysis selection and scorer list:

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/analysis_inputs.json`

Canonical S3d setup:

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

The `.geo` and `.det` with the same stem are the geometry and scorer sources.

Prompt input manifest and published cutflow:

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/01_prompt/prompt_input_manifest.csv`

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/01_prompt/prompt_cutflow.csv`

Retained compact S3d gamma catalog (present in the raw main tree, omitted from
the lightweight worktree handoff copy):

`/home/ubuntu/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/01_prompt/catalog/S3d_O8/gamma.pkl`

Prior TES-positive event reduction (not an incident denominator):

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_20260814/data/prompt_w2_event_summary.csv`

The three large raw SIMs are listed, with no abbreviation, in
`prompt_leak_interaction_points.csv`.  They live under
`/home/ubuntu/TES_511_Balloon/runs/...`; adjacent `.source`,
`.dat.inc1.dat`, and `.log` files exist for all three.  IA and CC records in
the SIM are the retained track/interaction truth; no separate higher-fidelity
track product was found.

## Geometry and coordinate reconstruction

The true placement is `InstrumentFrame.Rotation 0 45 0`.  The independently
reconstructed World-to-InstrumentFrame direction transform is

```
x_if = cos(45 deg) * (x_world - z_world)
y_if = y_world
z_if = cos(45 deg) * (x_world + z_world)
```

Theta is measured from `+x_if`; azimuth about `+x_if` is
`atan2(z_if,y_if)` modulo 360 degrees.  Substituting the three raw INIT
directions reproduces the compact-table values.  Projecting each INIT ray to
its PAIR point gives perpendicular residuals 0.000188, 0.000282, and 0.000184
cm, consistent with the five-decimal SIM print precision.

True-volume membership was queried through MEGAlib `MDGeometry` against the
canonical setup, not inferred from names or ideal cylinders.  The read-only
point-query source is
`engineering/s3d_o8_loop_engineering_20260814/code/query_megalib_geometry.cc`.
The ray trace used 0.001-cm membership steps and binary-refined every CSG
boundary below 1e-9 cm; its source is
`engineering/s3d_o8_loop_engineering_20260814/agents/prompt/trace_true_geometry_rays.cc`.

## Three-event physical chain

### Event 3883, 4.148290 MeV gamma

- Enters through the bottom stack, crossing 1.049445 cm plastic and 3.148334
  cm BGO.  This is 23.434097 g cm-2 active grammage.
- It crosses BPE, Al/Kapton, the passive W bottom plate, inner copper, Mu-metal,
  and Nb.  Passive grammage before the first pair is 20.271318 g cm-2.
- `INIT -> PAIR` has no preceding COMP/PHOT/RAYL.  PAIR is in
  `Nb_MagShield_Inner_Cylinder_2mm`.
- The positron leaves Nb and annihilates in
  `MuMetal_MagShield_Outer_Cylinder_2mm` at (0.64778,-0.27399,-1.95866) cm.
- ANNI IA7 is the ancestor of TES IA17 and descendants.  The TES receives
  510.99891 keV in `TP_L2_00361`; the other annihilation photon deposits in
  passive material.

### Event 19932, 5.768820 MeV gamma

- Enters through the side stack, crossing 1.322554 cm plastic and 5.290292 cm
  BGO: 38.923306 g cm-2 active grammage.
- Passive grammage to first pair is 32.673819 g cm-2, dominated by 2.803801 cm
  of copper (two cold plates plus 0.970119 cm of DR mixing chamber).
- The uncollided primary pairs and the positron annihilates locally in
  `DR_MixingChamber_Cu` (PAIR-to-ANNI displacement about 0.007 cm).
- ANNI IA10 is the ancestor of TES IA15 and descendants.  It deposits
  510.99891 keV in `TP_L2_00329`; the opposite photon deposits 510.99891 keV
  in passive material.

### Event 8081, 6.345940 MeV gamma

- Enters through the side stack, crossing 1.010960 cm plastic and 4.044046 cm
  BGO: 29.754013 g cm-2 active grammage.
- It crosses volumes named `rectcut_window_band`, but the exact CSG query puts
  the ray in solid material, not a relief void.  Passive grammage to pair is
  18.122864 g cm-2.
- The uncollided primary pairs in `Nb_MagShield_Inner_Cylinder_2mm`.  The
  positron transports through the inner region and annihilates in
  `Cu_SubstrateSupport_SolidDisk_L0_deepest`.
- ANNI IA9 feeds the TES: 69.58439 keV in `TP_L5_00019` plus 441.41452 keV in
  `TP_L5_00006`, total 510.99891 keV.  This two-pixel topology fails Step05.

Exact interaction coordinates and ancestry are in
`prompt_leak_interaction_points.csv`; material chords and densities are in
`prompt_leak_material_chords.csv`; the compact event view is in
`prompt_leak_event_summary.csv`.

## Active scorer proof

The six veto volumes in `analysis_inputs.json` are exactly the six sensitive
volumes defined in the canonical `.det`:

1. `BGO_S3C_FullWrap_SideShell_WindowCut_40mm`
2. `BGO_S3D_O8_FullWrap_BottomCap_30mm`
3. `BGO_S3D_O8_FullWrap_TopAnnulus_10mm`
4. `GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm`
5. `GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm`
6. `GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm`

The current prompt parser sums these exact names, separating BGO and plastic.
Every one of the three raw event blocks has zero `CC HIT` records in all six
names.  Thus `bgo_total_keV=0` and `plastic_total_keV=0` are not caused by a
threshold or volume-alias mismatch in the current scorer contract.  This does
not prove that unmodeled services/CAD are harmless; it proves the result in the
declared simulation geometry.

## Complete incident denominator

The S3d/instant/gamma cell consists of 132 manifest-listed SIM jobs:

- 3,207,738 manifest histories;
- 3,207,738 raw `IA INIT` records (exact equality checked);
- sum(TT) = 59.0965413 s;
- event weight = 1/sum(TT) = 0.016921464065444387 cps.

All 132 SIMs and DAT files exist.  All SIM headers and all 132 source cards
resolve to the canonical S3d setup.  The source cards contain 2,640 corrected
gamma spectrum references (20 angular sources per card), all under
`spectra/correct_keV_total/gamma_bin...`.  Five early jobs store their source
card in a `job_sources/` subdirectory rather than adjacent to the SIM.  The
corrected gamma source already includes the annihilation bump; no mono-511 was
added.

The only unbiased realized phase-space denominator is one `IA INIT` per raw
history.  A source card supplies the expected spectrum/flux, and a DAT supplies
TT, but neither supplies each realized impact parameter.  The compact catalog
is TES-positive only, and `prompt_w2_event_summary.csv` is W2-preselected, so
neither is a denominator.

`stream_gamma_denominator.py` streamed all 132 files and wrote:

- `denominator/gamma_denominator_summary.json`
- `denominator/incident_gamma_E_mux_az_denominator.csv`
- `denominator/pre_w2_gamma_events_with_denominator.csv`

`stream_gamma_active_grammage.py` then sent each INIT ray to the compiled
read-only `active_chord_query.cc`.  For each ray, it integrates the true six
active CSG volumes from the source point to the ray's closest approach to the
InstrumentFrame origin (the incoming half-ray, so the far-side exit shield is
not double-counted).  It wrote:

- `denominator/incident_gamma_E_mux_az_active_grammage.csv` (5,578 populated
  cells);
- `denominator/active_grammage_summary.json`.

All 3,207,738 INIT rays were accounted for.  The mean incoming chords are
1.76919 cm BGO and 0.80605 cm plastic, or 13.39147 g cm-2.  1,924,489 rays have
zero active chord and none of those produces even a pre-veto W2 event.  All
three leaks lie instead in 15-50 g cm-2.  Thus active grammage strengthens,
rather than weakens, the rejection of an open-hole explanation.

Direction bins are equal-solid-angle bins in `mu_x = cos(theta_from_+x_if)`,
with 45-degree azimuth sectors; using uniform theta bins would bias solid
angle.  The three occupied leak cells are:

| Event | E bin (MeV) | mu_x bin | azimuth bin | N incident | k leak | k/N | one-sided 95% upper |
|---|---:|---:|---:|---:|---:|---:|---:|
|3883|4-5|0 to 0.25|45-90 deg|867|1|1.153e-3|5.460e-3|
|19932|5-6|-0.75 to -0.5|270-315 deg|702|1|1.425e-3|6.740e-3|
|8081|6-8|-1 to -0.75|0-45 deg|633|1|1.580e-3|7.472e-3|

All 640 E x direction cells are populated; 637 have zero leaks.  Each nonzero
cell has leakage Neff=1.  These three large point estimates are consequently
not hotspot measurements and must not be rendered as a smooth leakage field.

Energy alone contains a physically useful but still low-count observation:
all three veto leaks are in 4-8 MeV (111,410 incident histories), whereas 105
of the 120 pre-veto W2 gamma events originate above 20 MeV and all are vetoed.
This is consistent with a low-shower pair/annihilation path, but three events
are insufficient to define an optimization band.

Across the full gamma cell:

- veto leak: k=3, p=9.3524e-7 per generated history, central rate
  0.05076439 cps;
- exact one-sided 95% p upper = 2.4172e-6, corresponding to 0.131203 cps;
- Step05: k=2, central 0.03384293 cps, one-sided 95% upper 0.106534 cps;
- conditional veto escape among pre-veto W2 events: 3/120 = 2.5%, with
  one-sided 95% upper 6.334%.

The next denominator axis must be **two material-resolved active chords**, not
a label inferred from entry direction:

`G_BGO = 7.1 * L_BGO` and `G_plastic = 1.03 * L_plastic` in g cm-2.

For every E x mu_x x azimuth x (G_BGO,G_plastic) cell, retain
`N_incident`, `N_preW2`, `N_veto`, `N_Step05`, `sum(w)`, `sum(w^2)`, and
`Neff=(sum w)^2/sum(w^2)`, plus exact one-sided intervals.  Also retain an
all-generated denominator and a separate diagnostic conditional on
intersecting the inner cryostat envelope.  Do not silently replace the former
with the latter.

After adding the total-active-grammage axis, the three nonzero cells contain
only 71, 94, and 92 incident rays, respectively, each still with k=1 and
leakage Neff=1.  Their one-sided 95% probability uppers are 6.51%, 4.95%, and
5.05%.  These are even less suitable for a smooth directional leakage map.

## Mass_model_511 cross-check

The seven final measured-W2 prompt events were reconstructed from the retained
compact catalogs and then returned to their raw SIM lineages.  The complete
machine-readable table is `mass_model_final_prompt_pair_hosts.csv`.

Six are gamma events.  Their primary first-pair hosts are:

- 4K Al bottom cap;
- Nb inner cylinder;
- MXC copper cold plate;
- stainless support rod;
- L0 copper disk (after one Compton interaction in that disk);
- 50mK copper can bottom.

Five of six primary gammas have PAIR as their first key interaction.  One has
COMP then PAIR in the same L0 copper disk.  One gamma deposits 31.79124 keV in
CsI, below the 50-keV veto; the other five have zero CsI.  The seventh event is
an eplus shower whose TES lineage is BREM -> PAIR in the Nb back cap ->
annihilation in the Nb cylinder.  No final-event pair host is CsI or W.

This is evidence for a general inner-passive `pair opacity x positron stop x
TES solid angle x no-veto` mechanism.  It is not evidence for one universal
material, and it does not justify adding another high-Z target near the TES.

## FACT / UNKNOWN / falsifiers

### FACT

- The three S3d leaks are equal-weight gamma events, not three arbitrary
  weights from mixed normalization cells.
- They cross 23-39 g cm-2 active grammage and have exactly zero active deposit.
- Their first recorded interaction is primary-gamma PAIR in true Nb/Nb/Cu
  volumes.
- Their TES energy descends from one of the two corresponding annihilation
  photons and sums to 510.99891 keV.
- The Mass_model final events show the same broad inner-passive topology but a
  mixed Al/Nb/Cu/steel host population.

### UNKNOWN

- A directional leakage field: each observed E x direction cell has Neff=1.
- The ranking of Nb versus Cu versus Mu-metal versus other inner passive
  components: three S3d hosts cannot estimate it.
- Candidate performance: no candidate-specific transport has yet been run.
- Whether a genuine repeatable geometry subpopulation exists inside any
  active-grammage cell; every observed nonzero cell still has leakage Neff=1.

### Prove/falsify tests

1. **Geometry-hole hypothesis — KILL for these events.** It would require an
   exact CSG chord near zero in BGO/plastic.  The measured chords are 23-39
   g cm-2.
2. **Nb-only fix hypothesis — MODIFY/unsupported.** It predicts the same host
   dominance in Mass_model.  The Mass final gamma hosts are mixed
   Al/Nb/Cu/steel.
3. **Inner-passive pair mechanism — retained, falsifiable.** A candidate that
   materially changes the implicated inner component but leaves the
   candidate-specific pair->ANNI->TES rate unchanged, at fixed source and
   denominator, falsifies causal attribution to that component.
4. **Directional hotspot — not established.** It requires nonzero leakage Neff
   in a predeclared E x equal-solid-angle x active-grammage bin, or an upper
   bound that separates it from neighboring bins.  One event per bin fails
   this requirement.
5. **Minimum transport evidence for a candidate:** run focused candidate S20
   only after freezing the above bins and the event-key/weight contract; retain
   every single-event contribution explicitly.  Promotion needs either enough
   effective survivors to estimate the candidate/baseline ratio or a
   one-sided upper limit below its allocated prompt budget.  A smooth heatmap
   or central value from one high-weight event is not proof.
