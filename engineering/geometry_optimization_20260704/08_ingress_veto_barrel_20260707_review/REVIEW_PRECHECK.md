# XHGIH-REVIEW Precheck: Ingress, Veto, Barrel e+ Hypothesis

Status: `PRECHECK_ONLY_WAITING_FOR_XHGIH_EXEC_OUTPUTS`

Date: 2026-07-07

Role boundary: this file is an independent review checklist and baseline evidence digest. It does not implement the new geometry, does not launch transport, and does not modify the original `511_Mass` / `Mass_model_511` geometry.

## 1. Files Read For Current Baseline

- Current geo-opt geometry manifest: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geo_opt_s1_bottomw_b4c_manifest.json`
- Current geo-opt geometry README: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/README.md`
- Step05 detector response: `stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.json`
- Step05 rates CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_rates.csv`
- Step08 time-dependent summary: `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json`
- Neutron/plastic audit: `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/geo_opt_neutron_plastic_audit_summary.json`
- Neutron/plastic audit README: `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/GEO_OPT_NEUTRON_PLASTIC_AUDIT.md`
- Plastic on/off prompt-by-tag table: `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_prompt_by_tag_comparison.csv`
- Atmospheric 511 replay summary: `engineering/geometry_optimization_20260704/06_atm511_replay_20260707/p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json`
- Atmospheric 511 source card: `runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1/Atm511LowerUnit3M_GeoOptS1BpeW5.source`

## 2. Current Authority Values To Preserve

Current geo-opt branch is `geo_opt_s1_bpe_w5_fullstat_v1`; all values below are geometry-optimization evidence, not final promotion.

### 2.1 Step05 W2 raw -> active -> Compton/FoV

Window: `w2_510p58_511p42`.

| stream | raw events | active-pass events | final events | raw cps | active cps | final cps | active veto rejection vs raw | Compton/FoV rejection vs active |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| prompt total | 133 | 53 | 48 | 0.0950097 | 0.0359824 | 0.0325872 | 62.13% | 9.44% |
| delayed total | 42 | 30 | 26 | 0.00451240 | 0.00322314 | 0.00279339 | 28.57% | 13.33% |
| science signal | 30304 | 30304 | 29684 | 0.814755 | 0.814755 | 0.798086 | 0.00% | 2.05% |

Gate: any new EXEC veto table must report both count-based and rate-weighted versions of these fractions, because prompt source event weights are not uniform across particle/source families.

### 2.2 Current W2 by prompt tag

Source: `plastic_veto_on_off_prompt_by_tag_comparison.csv`, plastic-active accounting ON.

| prompt tag | raw cps | active-pass cps | final cps | active veto rejection vs raw | Compton/FoV rejection vs active | note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `eplus` | 0.0421004 | 0.0271615 | 0.0237663 | 35.49% | 12.50% | dominant residual charged-particle component |
| `n` | 0.0407118 | 0.00882089 | 0.00882089 | 78.33% | 0.00% | current plastic ON/OFF gives no W2 neutron change |
| `gamma` | 0.00542791 | 0 | 0 | 100% | n/a | no final W2 gamma in this table |
| `muplus` | 0.00541532 | 0 | 0 | 100% | n/a | no final W2 mu+ |
| `muminus` | 0.000675721 | 0 | 0 | 100% | n/a | plastic-off table has one active-pass muminus contribution |
| `p` | 0.000678574 | 0 | 0 | 100% | n/a | no final W2 proton |

Plastic accounting ON/OFF for W2 `eplus` final: `0.0359890 -> 0.0237663 cps`, a `33.96%` final-rate reduction. This is not transport attenuation, because the plastic material remains present in both accounting modes.

### 2.3 Neutron / BPE / activation evidence

Source: `GEO_OPT_NEUTRON_PLASTIC_AUDIT.md`.

- Mass_model_511 fixed total activity: `141.833438 Bq`
- Geo-opt fixed total activity: `106.482268 Bq`, down `24.924%`
- Geo-opt internal activity excluding added GeoOpt layers: `105.564815 Bq`, down `25.571%` vs Mass
- CsI activity: `63.0197707 Bq` vs `89.4649266 Bq`, down `29.559%`
- Added GeoOpt layer activity: `0.917453416 Bq`
- Geo neutron weighted RPIP points: total `31016`, internal `30769.5`, CsI `23927.5`
- Mass neutron weighted RPIP points: total/internal `40687.5`, CsI `32453.625`
- Required plot already exists for current branch: `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/figures/neutron_energy_depth_hexbin.png`

Gate: this supports that the whole current outer shield stack reduces activation; it does not isolate BPE-only causality.

### 2.4 Plastic veto evidence

Source: `GEO_OPT_NEUTRON_PLASTIC_AUDIT.md`.

- Prompt e+ generated events parsed: `1949816`
- Any GeoOpt plastic hit: `345248` (`17.707%`)
- `sec=e+` ionization hit in plastic: `331474` (`17.0%`)
- `sec=e+` plastic deposit >= 50 keV: `141634` (`7.264%`)
- W2 prompt e+ events vetoed only when plastic is active: `19`, rate `0.0129017275 cps`
- W2 final background with plastic active: `0.0353806162 cps`
- W2 final background with plastic disabled only in veto accounting: `0.0484939025 cps`

Gate: EXEC must not describe plastic ON/OFF as material removal unless it reruns transport with geometry physically changed.

### 2.5 Atmospheric 511 replay evidence

Source: `p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json`.

- Generated events: `3000000`
- Observation time: `265.314 s`
- Source normalization: total lower-hemisphere line flux `1.0 ph cm^-2 s^-1`
- W2 raw events: `108`, raw transfer `0.407064836 cps/(ph cm^-2 s^-1)`
- W2 active-pass events: `108`, active transfer `0.407064836 cps/(ph cm^-2 s^-1)`
- W2 final events: `95`, final transfer `0.358066291 cps/(ph cm^-2 s^-1)`
- Active anticoincidence rejection: `0%`
- Compton/FoV rejection vs active: `12.04%`
- Harris Rc~11-13 GV added W2 background: `0.00834351749 cps`
- Harris-included W2 background: `0.04372413365 cps`
- Harris-included W2 `F3(20d)`: `4.08478147108e-05 ph cm^-2 s^-1`

Gate: active-veto performance on atmospheric 511 must be reported separately from physical shielding transfer. Current active veto kills `0/108` W2 raw candidates.

### 2.6 Current performance budget

The current component budget after Harris atmospheric 511 is:

| component | W2 cps |
| --- | ---: |
| prompt e+ residual | 0.0237663402 |
| prompt neutron residual | 0.00882088514 |
| atmospheric 511 Harris | 0.00834351749 |
| delayed activation residual | 0.00279339081 |
| total with Harris atmospheric 511 | 0.04372413365 |

To reach `F3(20d) <= 1.5e-5` at fixed signal acceptance, prior clue evidence estimated a target total background of about `0.005896 cps`. Any EXEC optimization claim must therefore show roughly an `86.5%` reduction in total W2 background or an equivalent signal-efficiency improvement.

## 3. Ingress Statistics Checklist

EXEC must provide an ingress table for `eplus`, `n`, and atmospheric `511` with both selected-event and source-population context.

Required minimum columns:

- `source_family`: `eplus`, `n`, or `atm511`
- `window`: at least `w2_510p58_511p42`; `broad_480_550` is recommended
- `stage`: `raw`, `active_veto_pass`, `side_compton_fov_pass`
- `event_count`
- `rate_or_transfer`: `cps` for prompt e+/n, `cps/(ph cm^-2 s^-1)` for atmospheric 511
- `source_theta_bin` and `source_phi_bin` or equivalent source angular label
- `first_recorded_volume`
- `first_recorded_material`
- `entry_region`: one of `side_window`, `side_wall`, `bottom`, `top`, `support`, `unknown`
- `first_recorded_x_cm`, `first_recorded_y_cm`, `first_recorded_z_cm`
- `tes_energy_keV`
- `active_veto_energy_keV`
- `side_compton_class`

Review interpretation rules:

- Source-bin ingress and first-recorded-volume ingress are different quantities. The former is source angular direction; the latter is where the event first deposits or records an interaction. Both must be preserved.
- If the SIM format does not record pure boundary crossings, EXEC must state that `first_recorded_volume` is a first recorded interaction/deposit proxy, not an exact geometrical entry surface.
- For e+ and neutron, counts must be rate-weighted because full-sphere source cards have unequal flux/spectrum bins.
- For atmospheric 511, the unit transfer normalization must remain `1.0 ph cm^-2 s^-1` over lower hemisphere bins unless explicitly documented otherwise.
- Do not infer "from a gap" unless the geometry has an actual documented opening and the first recorded location supports that classification.

## 4. Veto Performance Checklist

Every veto table must keep these denominators:

- Active anticoincidence efficiency: `1 - active_veto_pass / raw`
- Compton/FoV veto efficiency: `1 - side_compton_fov_pass / active_veto_pass`
- Total post-veto rejection: `1 - side_compton_fov_pass / raw`

Required outputs from EXEC:

- `veto_efficiency_by_source_window_stage.csv`
- `veto_efficiency_by_ingress_region.csv`
- `side_compton_class_counts.csv`
- A machine-readable summary JSON with the exact active-veto volume rule, threshold, and reject policy.

Review gates:

- `raw`, `active_veto_pass`, and `side_compton_fov_pass` must come from the same underlying event population.
- `reject_policy=keep` means `reject_kept` classes survive; they must not be counted as Compton vetoes.
- Active veto energy must include only active volumes named in the rule. Passive W/SS/Al barrel deposits must not be counted as active veto.
- A geometry A/B comparison measures transport plus downstream veto together. It is not by itself an active anticoincidence efficiency.
- A postprocess active-volume ON/OFF comparison measures accounting only. It is not by itself physical attenuation.

## 5. Hypothesis Barrel Geometry Review Checklist

User's hypothesis geometry requirement: new geometry, original geometry unchanged, only TES array and CsI scintillator position/shape retained, external supports retained, an outer barrel-shaped passive W or stainless-steel shield added, side thin Al window added, and only e+ transport run for this hypothesis.

Expected EXEC evidence:

- New directory under `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_exec/` or another clearly dated sibling, not under original `511_Mass` / Mass geometry directories.
- New `.geo.setup`, `.geo`, `.det`, materials file if needed, WRL view, and 2D detail figure.
- A geometry manifest with:
  - source geometry path
  - generated geometry path
  - barrel material: `W` or `SS`
  - barrel dimensions and mass
  - thin Al window thickness and side-window dimensions
  - explicit allowlist of retained volume prefixes
  - explicit denylist report for removed internal passive structures
- Source card for e+ only, with geometry line pointing to the new barrel `.geo.setup`.
- Cosima log and SIM header proving the new geometry was used.
- Overlap check or at least a smoke transport result showing the geometry loads.

Geometry allowlist concept for review:

- Must retain TES array volumes: `TES_L*`, `TP_L*`, `TES_Pixel_*`, and detector entries needed for TES readout.
- Must retain CsI scintillator volumes with their original positions/shapes: `CsI_*`.
- May retain world/coordinate containers such as `WorldVolume` / `InstrumentFrame`.
- May retain explicitly named external support volumes, but EXEC must list them and justify why they are external supports.
- May add new passive barrel and thin Al window volumes.

Geometry denylist examples that should not remain unless EXEC explicitly justifies them:

- Internal cryostat/passive shell stack: `Vacuum_Jacket_*`, `Shield_60K_*`, `Shield_4K_*`, `Still_Shield_*`, `Plate_300K_*`, `Win_50mK_*`, `Win_Still_*`, `Win_4K_*`, `Win_60K_*`, `Win_Be_*`, `Win_Outer_*`
- Internal DR/passive support stack: `DR_*`, `ColdPlate_*`, `Cu_ColdFinger_*`, `Cu_MXC_*`, `Cu_SubstrateSupport_*`, `Si_Substrate_*`
- Current geo-opt add-ons if the hypothesis is supposed to isolate barrel physics: `GeoOpt_S1_PlasticFullWrap_*`, `GeoOpt_BPE5_*`, `GeoOpt_W_BottomBaffle_*`

Detector map gates:

- `.det` must include TES detector definitions and CsI scintillator detector definitions.
- `.det` must not include stale detector entries for removed passive volumes.
- If CsI is the only active anticoincidence layer in the barrel hypothesis, the active-veto rule must say so explicitly.

## 6. e+ Hypothesis Run Review Gates

EXEC should run only e+ for the barrel hypothesis, but the output must still be auditable.

Required e+ run artifacts:

- e+ source card path
- e+ SIM path
- cosima log path
- generated/processed event counts
- prompt normalization used to convert selected events to cps
- event selection summary for W2 and broad windows
- ingress summary for W2 `raw`, `active_veto_pass`, and `side_compton_fov_pass`
- veto efficiency summary with the denominator rules above
- comparison against current geo-opt e+ W2 values:
  - raw `0.0421004 cps`
  - active-pass `0.0271615 cps`
  - final `0.0237663 cps`
  - plastic-off final `0.0359890 cps`

Review gates:

- The source card must point to the new barrel geometry; a current geo-opt or Mass geometry path invalidates the run.
- If the barrel material changes from W to SS or both are tried, each variant must have its own geometry label and run directory.
- The run must state whether the barrel physically attenuates e+ before CsI, or whether it creates secondary gamma/annihilation photons that still pass into TES.
- The analysis must not claim a 20-day final performance from e+ only; it may only report e+ component suppression and projected algebraic impact.

## 7. Specific Risks To Audit After EXEC

- Mixing rate denominators: using `raw` as denominator for Compton/FoV veto instead of `active_veto_pass`.
- Treating the current plastic ON/OFF postprocess as if plastic material was removed.
- Counting passive W/SS/Al energy deposits as active veto energy.
- Reporting unweighted event counts for e+ or neutron source bins as if they were normalized flux contributions.
- Calling first recorded deposit volume the true ingress boundary without caveat.
- Retaining internal cryostat structures in the barrel hypothesis, which would violate "only TES + CsI + external supports + barrel/window".
- Leaving stale `.det` sensitive volumes for removed geometry volumes.
- Reusing current geo-opt Step05 signal or source files while labeling the run as barrel geometry.
- Overclaiming atmospheric 511 suppression from e+ barrel-only transport.
- Comparing current full e+/n/atm background against a barrel e+-only run and calling it a total-background improvement.

## 8. Review Decision Template For Later

When XHGIH-EXEC provides paths, review should fill:

- `INGRESS_PASS` / `INGRESS_FAIL`: Are e+, n, and atm511 ingress statistics present with source-bin and first-recorded-volume definitions?
- `VETO_DENOMINATOR_PASS` / `VETO_DENOMINATOR_FAIL`: Are active and Compton/FoV denominators correct?
- `TRANSPORT_VS_ACCOUNTING_PASS` / `TRANSPORT_VS_ACCOUNTING_FAIL`: Are physical attenuation and postprocess active-veto accounting separated?
- `BARREL_GEOMETRY_PASS` / `BARREL_GEOMETRY_FAIL`: Does geometry retain only allowed volumes and add only barrel/window/supports?
- `EPLUS_RUN_PASS` / `EPLUS_RUN_FAIL`: Does the e+ run source card and SIM header point to the new barrel geometry?
- `CLAIM_BOUNDARY_PASS` / `CLAIM_BOUNDARY_FAIL`: Are claims limited to what the e+ hypothesis run can prove?

