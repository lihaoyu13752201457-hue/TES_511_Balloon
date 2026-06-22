# Project List: Migration And Required Outputs

Last updated: 2026-06-10 (review additions from the 2026-06-10 full-chain
review are marked "REVIEW-ADD"; they close gaps that would otherwise carry
known problems into the new branch)

Purpose: if the project is restarted in a new directory for a revised mass
model, this file tells Codex what code/configuration must be migrated and what
outputs must exist before any new background or sensitivity number is quoted.

Read with `Project_Memory.md`. This checklist is not a science result; it is a
handoff contract for a clean rerun.

## Migration Rules

- Start from code/config/source definitions, not from old large `runs/` products.
- Treat old `outputs/` and `stepwise_maintenance/*/outputs/` as reference
  evidence only until regenerated in the new directory.
- Before editing a new branch, run `git status --short` and preserve unrelated
  user changes.
- If the final concept is DR rather than ADR, do not just rename files. Rebuild
  the geometry/mass model, then rerun the full chain.
- Keep path compatibility only deliberately. Old `ADR`, `v4c`, and `cm` tokens
  may survive in filenames during transition, but final documentation must say
  whether the contents are DR or ADR.

## Must Migrate: Core Code

### Geometry And Mass Model

- `code/geometry/GenerateGeo_ADR_v4c_mkflange.py`
- `code/tools/build_cm_geometry.py`
- `records/00_geometry/make_geo_2d_schematic.py`
- `stepwise_maintenance/step01_geo/code/build_step01_geo.py`
- `stepwise_maintenance/step01_geo/source_snapshots/build_step01_geo.py`
- `stepwise_maintenance/step01_geo/source_snapshots/make_geo_2d_schematic.py`

DR rewrite note:

- Remove/replace ADR-specific volumes such as `ADR_Magnet_Coil_Cu`,
  `ADR_Magnet_Yoke_Fe`, `ADR_SaltPill_Proxy`, `ADR_SaltPill_Cu_Can`, and
  `ADR_HeatSwitch_Stainless_Link`.
- Decide explicitly which generic cold-stage structures remain in DR:
  TES can/shields, cold plates, thermal buses, pulse-tube/cold-head interfaces,
  Be/Al windows, passive Cu/W shields, wiring/readout proxies.
- Add DR-specific proxies as needed: mixing chamber, still, heat exchangers,
  plumbing/lines, supports, shields, and any DR service masses that materially
  affect activation/background.

### Atmospheric Prompt And Activation

- `code/tools/run_equiv2602_pipeline_NEW_GEO.py`
- `stepwise_maintenance/step02_raw_background_simulation/code/build_step02_event_aligned_summary.py`
- `stepwise_maintenance/step02_raw_background_simulation/code/build_step02_raw_background_summary.py`
- `stepwise_maintenance/step02_raw_background_simulation/source_snapshots/run_equiv2602_pipeline_NEW_GEO.py`
- `stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py`
- `stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py`

Important: `makedecaysourcewithplot_rpip.py` and `build_fixed_delay_source.py`
are required for delayed-source construction/ground-state fixing. If they are
not promoted into the new branch `code/tools/`, migrate them from
`source_snapshots/` or from the upstream source used to make those snapshots.

### Delayed Source Audits

- `stepwise_maintenance/step03_delay_source/code/build_step03_delay_source_audit.py`
- `stepwise_maintenance/step03_delay_source/code/build_step03_rpip_production_map.py`

Upgrade target:

- Add or preserve exact-RPIP position sampling tests for beta-plus emitters
  such as O-15/C-11/N-13/F-18.
- Add material-containment rejection/checks for PCON or bounding-annulus
  approximations before relying on fallback source positions.

REVIEW-ADD: the exact-position method is now implemented and smoke-validated;
migrate these concrete files (see `tests/realpos_delayed_smoke/README.md`,
especially the "Filter semantics" section: production sampling must use the
`in_fixed_inventory` filter and ground-state-fixed activities, keeping
`(VN, ZA, exc)` granularity):

- `tests/realpos_delayed_smoke/build_realpos_smoke_source.py`
- `tests/realpos_delayed_smoke/reparse_full_rpip_table.py`
- `tests/realpos_delayed_smoke/run_smoke.sh`
- `tests/realpos_delayed_smoke/README.md`

REVIEW-ADD conditional: if the new branch adopts exact-position `PointSource`
sampling as the production Step03 pipeline, the Step03 required-output list
below changes shape (no `RadialProfileBeam` `profiles/` files; instead a
point-sampled `.source` plus a sampling manifest). Record the chosen pipeline
explicitly in the new branch's Step03 README before quoting numbers.

### Detector Response, Veto, And Reports

- `code/tools/make_complete_day15_report_ADR.py`
- `code/tools/make_day15_report_ADR.py`
- `code/tools/summarize_science_511_ADR.py`
- `stepwise_maintenance/step05_veto_time_axis/README.md`

Rename or document `ADR` script names if the new branch is DR. Do not change
physics silently; update file names only after tests/outputs still match.

### Optics And EventList Bridge

- `stepwise_maintenance/step04_opticsim/code/build_real_laue_lens_design_20260601.py`
- `stepwise_maintenance/step04_opticsim/code/build_step04_opticsim_audit.py`
- `stepwise_maintenance/step04_opticsim/code/build_step04_source_model_explainer.py`
- `stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_line_config.csv`
- `stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_xop_map.csv`
- `stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`
- `stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py`
- `stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py`

If replacing the optics with `laue.png` design values, do not treat
`Focus area=100 cm2` as effective area. Build an explicit ring/tile/mosaicity
model and regenerate Step04/Step09. Current scale reference:

- current B-FULL `A_eff(511)=15.29928 cm2`;
- Ge(111), `f=10 m`, Bragg-annulus estimate `A_eff ~18 cm2`;
- a designed `A_eff=20 cm2` lens gives only `F3_1Ms(spot_r90) ~6.7e-5`;
- full 450-550 keV coverage requires more than a single narrow 511 keV ring.

### Time Variation, Sources, Significance, And Figures

- `stepwise_maintenance/step06_mission_time_variation/code/build_step06_mission_time_variation.py`
- `stepwise_maintenance/step07_source_cases/code/build_step07_source_cases.py`
- `stepwise_maintenance/step08_significance/code/build_step08_significance.py`
- `stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py`
- `stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py`
- `stepwise_maintenance/step08_significance/code/time_fold_common.py`
  (REVIEW-ADD: shared Step06 time-fold module; both sidecar scripts import it,
  forgetting it breaks both with ImportError)
- `code/tools/build_route_b_diffuse_supplement_20260602.py`
- `code/tools/build_experiment_report_20260601.py`
- `stepwise_maintenance/figure_pack/build_stepwise_figure_pack.py`
- `stepwise_maintenance/new_figure/build_new_figure_abc.py`

### Validators And Audits

- `code/tools/validate_new_geo_re.py`
- `code/tools/audit_groundstate_half_life_units.py`
- `code/tools/audit_csi_activation_baseline.py`
- `code/tools/build_review_20260531_closure.py`
- `code/tools/build_bgo_control_geometry.py` if a BGO/CsI comparison is kept.
- `tests/compton_fov_geometry.py` (REVIEW-ADD: the validator executes this
  test at startup; without it the validator fails immediately)
- `.gitignore` (REVIEW-ADD: includes `tests/*/outputs/`; without it the new
  branch can accidentally commit multi-GB/100MB generated products)

Validator must be updated for the new geometry names/materials. Remove ADR-only
assertions or replace them with DR-specific assertions.

## Must Migrate: Config And Reference Inputs

- `config/megalib_sources_fullsphere20/Background_*_fullsphere20.source`
- `config/run_configs/Science_511_onaxis_ADR_cm_local.source`
- `config/run_configs/Science_511_onaxis_ADR_cm_smoke1k.source`
- `config/science_511_onaxis_source/metadata/science_rate_ledger.csv`
- `config/science_511_onaxis_source/metadata/science_source_models.csv`
- `inputs/nubase/README.md`
- `inputs/nubase/nubase_2020.txt`
- `LAUE_LENS_DESIGN_SPEC_20260601.md`
- `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`
- `OPTICS_BFULL_BACKEND_INTEGRATION_20260601.md`
- `Project_Memory.md`
- `Project_List.md`

For a DR branch, duplicate and rename science/source cards only after replacing
geometry paths inside them. Source-card geometry must point to the new
`.geo.setup`, not copied ADR geometry.

REVIEW-ADD warnings on two of the inputs above:

- `science_rate_ledger.csv` was regenerated on 2026-06-11 with
  `A_opt_cm2=15.299280`, matching the current B-FULL `A_eff(511)=15.29928 cm2`.
  Migrate the fixed CSV as the current mainline input, but regenerate it
  whenever the optics authority or detector geometry changes. Keep the Step05
  acceptance check that the ledger `A_opt_cm2` equals the Step04 A_eff authority
  and that `science_injection_rate = A_eff * T_atm * flux`.
- Step06 depends on the external EXPACS/PARMA C++ driver
  (`../COSMOSRAY_BALLOON_SIM/external/expacs_parma/phase2_parma_grid_driver`
  plus its `parma_cpp/` directory; alternate candidate paths are listed in
  `build_step06_mission_time_variation.py`). If the executable is missing the
  code SILENTLY falls back to the analytic depth/cutoff proxy
  (`status=FALLBACK_PROXY`). Migrate or rebuild this dependency, and assert the
  backend in Step06 acceptance (below).

## Do Not Blindly Migrate As Authority

- `runs/`: large production products; rerun in the new branch.
- `outputs/reports/day15_complete_report/work/event_catalog.pkl`: cache tied to
  old SIM paths/sizes/mtimes.
- Old `outputs/reports/*` summaries: reference only until regenerated.
- `__pycache__/` files.
- Old BGO products from `../new_geo_re_2` unless the new branch explicitly
  keeps the BGO comparison and reruns it.

## Required Outputs Before Quoting New Results

### Step01 Geometry Authority

Required files:

- `outputs/geometry/<NEW_GEOMETRY>/TibetTES_*.geo`
- `outputs/geometry/<NEW_GEOMETRY>/TibetTES_*.geo.setup`
- `outputs/geometry/<NEW_GEOMETRY>/TibetTES_*.det`
- `outputs/geometry/<NEW_GEOMETRY>/Materials_*.geo`
- `outputs/geometry/<NEW_GEOMETRY>/Intro_*.geo`
- `outputs/geometry/<NEW_GEOMETRY>/bounds.json`
- `outputs/geometry/<NEW_GEOMETRY>/mass_budget.json`
- `outputs/geometry/<NEW_GEOMETRY>/mass_budget.csv`
- `outputs/geometry/<NEW_GEOMETRY>/*.wrl`
- overlap-check source/log evidence and a PASS validation record.

Stepwise outputs:

- `stepwise_maintenance/step01_geo/README.md`
- `stepwise_maintenance/step01_geo/outputs/*_2d_schematic.png`
- `stepwise_maintenance/step01_geo/outputs/*/*.wrl` or equivalent WRL output.
- `stepwise_maintenance/outputs/geometry/README.md`
- `stepwise_maintenance/outputs/geometry/*_2d_schematic.png`
- `stepwise_maintenance/outputs/geometry/*.wrl`

Acceptance:

- Geometry loads in Cosima.
- Overlap check is clean.
- Mass budget explicitly identifies DR-specific structures and confirms ADR
  structures are absent or intentionally retained/renamed with explanation.

### Step02 Prompt And Activation Production

Required run products:

- `runs/step02_instant_<NEW_TAG>/run_summary.json`
- `runs/step02_instant_<NEW_TAG>/*/*.sim.gz` or equivalent particle outputs.
- `runs/step02_buildup_<NEW_TAG>/run_summary.json`
- `runs/step02_buildup_<NEW_TAG>/*/*.sim.gz`
- isotope production `.dat` ledgers for buildup.
- normalization/manifest CSV/JSON files for prompt and buildup.

Stepwise outputs:

- `stepwise_maintenance/step02_raw_background_simulation/outputs/step02_event_aligned_summary.json`
- `stepwise_maintenance/step02_raw_background_simulation/outputs/step02_event_aligned_summary.md`
- `stepwise_maintenance/step02_raw_background_simulation/outputs/step02_event_aligned_particle_counts.csv`
- `stepwise_maintenance/step02_raw_background_simulation/outputs/step02_event_aligned_summary.png`
- `stepwise_maintenance/step02_raw_background_simulation/source_snapshots/`
  with source cards, manifests, delayed-source inputs, and fix summaries.

Acceptance:

- Prompt and buildup have all planned jobs complete.
- Generated event totals match requested totals.
- Native `.det` trigger/veto blocks do not filter activation buildup unless the
  new design deliberately changes this and the validator documents it.

### Step03 Delayed Source

Required run products:

- `runs/step02_decay_source_<NEW_TAG>/activation_decay_day15.source`
- `runs/step02_decay_source_<NEW_TAG>/activation_inventory_day15.csv`
- `runs/step02_decay_source_<NEW_TAG>/unknown_isotopes_day15.csv`
- `runs/step02_decay_source_<NEW_TAG>/no_rpip_points_day15.csv`
- `runs/step02_delay_fix_<NEW_TAG>/activation_decay_day15_groundstate_fixed.source`
- `runs/step02_delay_fix_<NEW_TAG>/groundstate_activity_corrections.csv`
- `runs/step02_delay_fix_<NEW_TAG>/removed_or_rescaled_sources.csv`
- `runs/step02_delay_fix_<NEW_TAG>/source_fix_summary.json`

Stepwise outputs:

- `stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json`
- `stepwise_maintenance/step03_delay_source/outputs/fixed_source_blocks.csv`
- `stepwise_maintenance/step03_delay_source/outputs/activity_saturation_by_inventory.csv`
- `stepwise_maintenance/step03_delay_source/outputs/decay_source_sample_1000.csv`
- `stepwise_maintenance/step03_delay_source/outputs/decay_source_sample_10000.csv`
- `stepwise_maintenance/step03_delay_source/outputs/delay_source_2d_schematic.png`
- `stepwise_maintenance/step03_delay_source/outputs/rpip_production_map.png`
- `stepwise_maintenance/step03_delay_source/outputs/rpip_production_map_summary.json`
- `stepwise_maintenance/step03_delay_source/outputs/rpip_production_points_sample.csv`
- `stepwise_maintenance/step03_delay_source/outputs/w1_decay_line_activity_by_nuclide.csv`
- `stepwise_maintenance/step03_delay_source/README.md`

Acceptance:

- Fixed delayed source uses repo NUBASE half-life evidence.
- No physically relevant short-lived beta-plus emitter is silently omitted.
- RPIP production-position map and sampled source map are both generated and
  clearly distinguished.

### Delayed Transport

Required files:

- `runs/step02_delayed_transport_<NEW_TAG>/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- `runs/step02_delayed_transport_<NEW_TAG>/cosima_delayed_transport_1m.log`
- gzip integrity check evidence.
- stream count evidence for `SE`, `ID`, `TS`, and `TE`.

Acceptance:

- 1,000,000 stored events unless a new explicit production target is recorded.
- Observation time is parsed from the new log/source and is not reused from old
  constants or stale cache.

### Science On-Axis Reference Transport (REVIEW-ADD)

The Step05 `science` stream input is geometry-dependent and was missing from
this list. Required in the new branch:

- `runs/science_511_onaxis_source/Science_511_*.inc1.id1.sim.gz` rerun against
  the NEW geometry (not copied).
- `outputs/reports/science_511_ADR_100k/science_511_100k_summary.json` (or
  renamed DR equivalent) regenerated from the new run.
- `config/science_511_onaxis_source/metadata/science_rate_ledger.csv`
  regenerated with the current Step04 `A_eff(511)`.

Acceptance:

- Ledger `A_opt_cm2` equals the Step04 `optics_aeff_authority.json` value;
  the day-15 summary `science_injection_rate` is consistent with
  `A_eff * T_atm * flux`.

### Step04 Optics

Required outputs:

- `stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`
- `stepwise_maintenance/step04_opticsim/outputs/step04_opticsim_audit.json`
- `stepwise_maintenance/step04_opticsim/outputs/laue_*_2d_schematic.png`
- `stepwise_maintenance/step04_opticsim/outputs/laue_*_particles.wrl`
- `stepwise_maintenance/step04_opticsim/outputs/laue_*_stage_summary.csv`
- `stepwise_maintenance/step04_opticsim/README.md`
- `stepwise_maintenance/step04_opticsim/real_design_crosscheck_*.md`

Acceptance:

- `A_eff(511)` is explicit and not inferred from `Focus area`.
- W1/W2 passbands are stated.
- If using `laue.png`, off-axis FoV and broadband 450-550 keV coverage are
  explicitly modeled or explicitly marked as not achieved.

### Step09 EventList Bridge And Detector-Coupled Signal

Required outputs:

- `stepwise_maintenance/step09_optics_bridge/outputs/eventlists/*.eventlist.dat`
- `stepwise_maintenance/step09_optics_bridge/outputs/run_configs/*.source`
- `runs/step09_optics_bridge/*.sim.gz`
- `stepwise_maintenance/step09_optics_bridge/outputs/step09_optics_bridge_summary.json`
- `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json`
- `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.md`
- `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_windows.csv`
- `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_spatial_line_cuts.csv`
- `stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv`
- `stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_spectrum_480_550.csv`

Acceptance:

- EventList source is inside Be-window gate.
- Detector-coupled W2 response and spot-cut response are regenerated from the
  new detector geometry and new Step05 catalog.

### Step05 Time-Axis, Active Shield, And Compton/FoV

Required outputs:

- `outputs/reports/day15_complete_report/complete_day15_summary.json`
- `outputs/reports/day15_complete_report/audit.md`
- `outputs/reports/day15_complete_report/cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf`
  or renamed DR equivalent.
- `outputs/reports/day15_complete_report/work/event_catalog.pkl`
- `outputs/reports/day15_complete_report/timeline_spectrum_480_550_rates.csv`
- `outputs/reports/day15_complete_report/timeline_spectrum_100_10000_rates.csv`
- `outputs/reports/day15_complete_report/science_reference_sensitivity.csv`
- `outputs/reports/day15_complete_report/activation_inventory_day15_after_groundstate_fix.csv`
- report figures under `outputs/reports/day15_complete_report/figures/`.

Acceptance:

- Cache rebuilt after geometry/SIM changes.
- Prompt, delayed, and focused streams are on a common Poisson time axis.
- Active-shield threshold and Compton/FoV policy are stated.

### Step06 Time Variation

Required outputs:

- `stepwise_maintenance/step06_mission_time_variation/outputs/step06_mission_time_variation_summary.json`
- `stepwise_maintenance/step06_mission_time_variation/outputs/trajectory_profile.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/time_dependent_driver_grid.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/atmosphere_transmission_511_by_time.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/particle_flux_by_time.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/expacs_particle_scale_by_time.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/expacs_prompt_driver_summary.json`
- `stepwise_maintenance/step06_mission_time_variation/outputs/expacs_prompt_driver_weights.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/activity_by_time_nuclide_volume.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/total_activity_by_time.csv`
- `stepwise_maintenance/step06_mission_time_variation/outputs/background_time_variation.csv`
- Step06 figures if generated.

Acceptance:

- Day-15 closure to Step05 is near numerical tolerance.
- State clearly that Step06 is rate-level unless new time-bin Cosima transport
  has been added.
- REVIEW-ADD: `expacs_prompt_driver_summary.json` reports
  `backend=official_EXPACS_PARMA_CPP_driver` (not `FALLBACK_PROXY`), unless the
  new branch deliberately accepts the proxy and documents it.
- REVIEW-ADD: `expacs_prompt_driver_weights.csv` includes the
  `prompt_final_event_count` column; record the per-particle surviving-event
  counts so the statistical basis of the prompt weights stays visible.

### Step07 Source Cases

Required outputs:

- `stepwise_maintenance/step07_source_cases/outputs/source_case_summary.json`
- `stepwise_maintenance/step07_source_cases/outputs/source_case_rates.csv`
- `stepwise_maintenance/step07_source_cases/outputs/source_spectrum_summary.csv`
- `stepwise_maintenance/step07_source_cases/outputs/cosima_source_manifest.csv`
- `stepwise_maintenance/step07_source_cases/outputs/artifact_manifest.csv`
- `stepwise_maintenance/step07_source_cases/outputs/diffuse_aperture_foreground.csv`
- `stepwise_maintenance/step07_source_cases/outputs/point_vs_diffuse_discrimination.csv`
- `stepwise_maintenance/step07_source_cases/README.md`

Acceptance:

- Focused mono-511 source uses the new Step09 EventList response.
- Diffuse Route B is not given point-source spot-cut gains.
- If BGO/Route B is retained, Siegert disk `sigma_l_deg=60`,
  `sigma_b_deg=10.5` must remain sigma fields, not FWHM.

### Step08 Significance

Required outputs:

- `stepwise_maintenance/step08_significance/outputs/step08_significance_summary.json`
- `stepwise_maintenance/step08_significance/outputs/cumulative_significance_by_case.csv`
- `stepwise_maintenance/step08_significance/outputs/t3_t5_summary.csv`
- `stepwise_maintenance/step08_significance/outputs/accidental_veto_by_time.csv`
- `stepwise_maintenance/step08_significance/outputs/rate_independent_veto_efficiencies.csv`
- `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.csv`
- `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.md`
- `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity_summary.json`
- `stepwise_maintenance/step08_significance/outputs/line_window_time_dependent_significance.csv`
- `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.csv`
- `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.md`
- `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy_summary.json`
- `stepwise_maintenance/step08_significance/outputs/spatial_line_time_dependent_significance.csv`
- `stepwise_maintenance/step08_significance/outputs/which_number_is_headline.md`
- `stepwise_maintenance/step08_significance/README.md`

Acceptance:

- Headline W2 and spot-cut numbers are regenerated.
- 1 Ms / 20 day / T3 definitions are not mixed.

### Final Reports, Figures, And Validator

Required outputs:

- `outputs/reports/validation_new_geo_re/validation_new_geo_re.json`
- `outputs/reports/validation_new_geo_re/validation_new_geo_re.csv`
- `outputs/reports/validation_new_geo_re/VALIDATION.md`
- root `VALIDATION.md`
- `outputs/reports/experiment_report_*/experiment_report.md`
- `outputs/reports/experiment_report_*/figures/*`
- `outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json`
- `outputs/reports/csi_activation_baseline/csi_activation_baseline_summary.json`
  or renamed detector/material baseline equivalent.
- `outputs/reports/route_b_diffuse_supplement_*/route_b_diffuse_summary.json`
  if Route B is retained.
- `stepwise_maintenance/outputs/figures/stepwise_figure_pack_summary.json`
- `stepwise_maintenance/outputs/figures/stepwise_3sigma_headline_results.png`
- `stepwise_maintenance/outputs/figures/stepwise_background_component_breakout.png`
- `stepwise_maintenance/outputs/figures/stepwise_spectrum_laue_w2_windows.png`
- `stepwise_maintenance/outputs/figures/stepwise_trajectory_time_variation.png`
- `stepwise_maintenance/new_figure/a_w1_w2.csv`
- `stepwise_maintenance/new_figure/a_w1_w2.png`
- `stepwise_maintenance/new_figure/b_w1_w2.csv`
- `stepwise_maintenance/new_figure/b_w1_w2.png`
- `stepwise_maintenance/new_figure/c_laue_only.csv`
- `stepwise_maintenance/new_figure/c_laue_only.png`

Acceptance:

- Validator status is PASS.
- No live docs quote stale CeBr3, old homogeneous-beam, or broad-window-only
  numbers as current authority.
- Literature markers such as 511-CAM, SPI, and COSI are labeled with their
  original normalization and any sqrt-time scaling.

## Optional If BGO/CsI Comparison Is Kept

If the new DR branch still compares CsI/BGO, create or update a sibling BGO
branch and rerun the same chain rather than reusing CsI detector-coupled
EventLists as BGO results. Required BGO outputs mirror the CsI outputs:

- BGO geometry authority and attenuation verification.
- BGO prompt and activation production.
- BGO delayed source, delayed transport, Step05, Step06, Step07, Step08,
  Step09 detector-coupled response.
- BGO validator and BGO-vs-CsI experiment report.
- BGO `PROJECT_MEMORY.md` and `project_state.json` updated after final rerun.

## Minimal Completion Gate

The new branch is not ready for paper numbers until all of these are true:

- Geometry is DR-consistent and overlap-clean.
- Step02 prompt and buildup are full-stat and event-count aligned.
- Step03 source audit passes with beta-plus omissions addressed.
- Delayed transport has a fresh 1M SIM/log and gzip passes.
- Step05 cache is rebuilt from new prompt/delayed/science streams.
- Step09 detector-coupled focus response is rebuilt against the new detector.
- Step06/07/08 are rebuilt from the new Step05 and Step09 authorities.
- Final validator is PASS.
- Final report and figure pack are regenerated.
- `Project_Memory.md` is updated with the new authoritative numbers and
  remaining limitations.
