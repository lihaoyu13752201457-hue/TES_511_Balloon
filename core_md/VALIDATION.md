# NEW_GEO_RE Validation

Status: **LEGACY_PRE_FIX_REVIEW_HOLD**

2026-06-12 review hold: this file records legacy DEMO2/mainline validation
outputs. The delayed-activation source behind `fixed_activity_Bq=624.27109184`
has been reproduced as over-normalized by `x8.0116` for I-128, so rows derived
from that source are provenance records only. Do not quote the W2/spatial
headline values here as current sensitivity authority until the div-corrected
mainline source and downstream Step05+ chain are rerun.

| check | status | details |
| --- | --- | --- |
| source_card_unit_guard | PASS | checked 6 science HomogeneousBeam cards; Be r=1.898; z_range=[-22.35,16.051] |
| geometry_authority | PASS | DEMO2 cm authority, TES 0.3 cm, Be 1.898/0.015 cm, CsI active shield, staged Al windows, Cu/W passive shield |
| csi_det_no_native_trigger_block | PASS | det=outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.det; native_trigger_residue=False; CsI_segments=20; threshold50=20/20; noise_equals_threshold=20/20; native trigger/veto block intentionally absent so activation buildup stores full events |
| production_paths_aligned | PASS | missing=[]; delayed_obs_s=1584.61; generated=1000000; expected_obs_s=1601.8681836603337; obs_rel_delta=0.010773785156839886; triggers=1000000; fixed_activity_Bq=624.2710918416268 |
| fixed_source_groundstate_removed | PASS | W-183/W-180 ParticleType 74183/74180 absent |
| half_life_prefix_unit_audit | PASS | claim=L1_HALF_LIFE_PREFIX_UNIT_AUDIT; prefix_rows=74; units=['Ey', 'Gy', 'My', 'Ty', 'ky']; self_tests=['Ey', 'Gy', 'My', 'Py', 'Ty', 'ky']; prefix_rel=0.0; line_rel=0.0; line_mismatches=0; W180_new_Bq=5.093794371872413e-21; forbidden_ZA=[]; nubase=True; csv=True; md=True |
| csi_activation_baseline | PASS | claim=L1_CSI_ACTIVATION_BASELINE_NO_BGO_CONTROL; activity_rel=1.839324415325258e-14; CsI_activity_fraction=0.8988607824850076; I128_fraction=0.8542374310958233; delayed_final_cps=2.31224086683797; BGO_control=NOT_RUN; md=True; csv=True |
| bgo_control_geometry | PASS | claim=L1_BGO_CONTROL_GEOMETRY_SCAFFOLD_NO_TRANSPORT; BGO_segments=20; veto_triggers=20; threshold50=20; noise_equals=20; BGO_active_mass_kg=102.57185459941465; mass_ratio=1.5742793791574277; transport=NOT_RUN; overlap=PASS; stale=[]; md=True |
| review_20260531_closure | PASS | claim=L1_REVIEW_20260531_CLOSURE_MATRIX; items=11; open_p0=[]; open_or_partial=['P1_CSI_ACTIVATION_BASELINE', 'P2_PROFILE_LIKELIHOOD_LIMA', 'P2_BGO_FULL_CONTROL_CHAIN']; stale_hits=[]; md=True; csv=True |
| timeline_expectation_closure | PASS | relative differences={'raw': 0.0015152458456195556, 'bgo': 0.007075636508620271, 'final': 0.007740016399235618}; tolerance=0.05 |
| compton_fov_backprojection | PASS | synthetic Be-window-center two-hit event is kept |
| step06_mission_time_variation | PASS | offsets lat/lon/alt=0.25/0.25/2.5; T_day15_error=2.999822612537173e-13; activity_closure=4.307130767749644e-14; per_nuclide_rel_error=1.0; rate_closure=6.272174113014999e-14; alt_prompt_corr=-0.9953348805867768; alt_T_corr=0.997952343357823 |
| step07_source_cases | PASS | claim=L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING; A closure rel=[0.0, 0.0]; B default=6.430033645383193e-06 cps; B/source policy=skipped_by_design_for_diffuse_source; focused mono A uses Step09 EventList source; V404_redshift_narrow_response=0.0; eventlist_sources=1; written_sources=1; missing=[] |
| step08_significance | PASS | claim=L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL; day15_acc_loss=0.0010373943106274375; A_ref_Z20d=0.7669158563686436; A_ref_T3_day=306.0392090474061; T3_status=extrapolated_beyond_20d; template_gain=1.0; bootstrap_rows=3; missing=[] |
| line_window_sensitivity | PASS | claim=L1_LINE_WINDOW_DETECTOR_COUPLED_FOCUS; broad_Z20d=1.3327565730763067; line_pm_3sigma_background_cps=0.18434717748640367; line_pm_3sigma_Z20d_time=2.735425315169172; gain=2.054808768892056; T3_day=24.055964903748688; csv=True; md=True |
| spatial_line_proxy | PASS | claim=L1_SPATIAL_LINE_DETECTOR_COUPLED_CLOSED; rows=12592; best_cut=spot_r68; rmax=1.6965521015564764; line_background=0.18434717748640367; best_background=0.018225396313875198; best_signal_fraction=0.6800921417516116; line_Z20d=2.735425315169172; best_Z20d=5.925176748683124; gain=2.166089754242361; csv=True; md=True |
| detector_coupled_focus_response | PASS | status=PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST; Aeff_resid=0.04379499999999992; generated=11910; W2_signal_response=8.982877815429566; W2_background=0.18434717748640367; spot_r90=0.5236921318617493; spot_r90_Z20d=4.527484229695351; md=True |
| step09_optics_bridge | PASS | status=PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED; rows=12592; max_radius_cm=1.4576682480028988 <= Be 1.898; z_plane=16.051; first_eventlist_z=16.051; uz_max=-0.9999685935009206; smoke_events=1000; stale_hits=[] |
| no_live_stale_paths | PASS | no stale background path tokens in live files |
| optics_bfull_policy | PASS | status=PASS_BFULL_XOPMAP_EVENTLIST_READY; model=B-FULL XOP-map; focused_signal_within_be=12592; diffracted_focal=12605; r99=0.2914104898226177; Be=1.898; channel_optics_used=False |
