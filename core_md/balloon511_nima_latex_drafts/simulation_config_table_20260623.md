# Simulation Configuration Authority 20260623

Created UTC: 2026-06-23T08:38:09+00:00

| Component | Value | Status | Source |
|---|---|---|---|
| `cosima_executable` | `/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima` | `current` | `outputs/reports/fix5_fullstat_v2/fix5_fullstat_delayed_transport_release.json` (json_pointer:/commands/0/command) |
| `megalib_version` | `4.02.00` | `current` | `runs/step02_instant_fix5_fullstat_v2/logs/Background_n_fullsphere20_rep05_part01.log` (line 6) |
| `geant4_version_from_run_log` | `geant4-10-02-patch-03` | `current_run_log` | `runs/step02_instant_fix5_fullstat_v2/logs/Background_n_fullsphere20_rep05_part01.log` (line 21) |
| `geant4_config_executable_version` | `11.2.0` | `current_environment_not_run_authority` | `command: geant4-config --version` (stdout) |
| `physics_list` | `QGSP_BIC_HP 2.0` | `current_run_log` | `runs/step02_instant_fix5_fullstat_v2/logs/Background_n_fullsphere20_rep05_part01.log` (line 27) |
| `electromagnetic_physics` | `G4EmLivermorePolarizedPhysics` | `current_run_log` | `runs/step02_instant_fix5_fullstat_v2/logs/Background_n_fullsphere20_rep05_part01.log` (lines 29 and 32) |
| `neutron_hp_data` | `G4NDL4.5` | `current_run_log` | `runs/step02_instant_fix5_fullstat_v2/logs/Background_n_fullsphere20_rep05_part01.log` (lines 523-525) |
| `atomic_deexcitation` | `G4UAtomicDeexcitation initialized` | `current_run_log` | `runs/step02_instant_fix5_fullstat_v2/logs/Background_n_fullsphere20_rep05_part01.log` (lines 545 and 690) |
| `root_config_version` | `6.36.06` | `current_megalib_environment` | `/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/bin/root-config` (stdout from /home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/bin/root-config --version) |
| `python_version` | `3.10.12` | `current_environment` | `command: python3 --version` (stdout) |
| `gcc_version` | `11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3)` | `current_environment` | `command: gcc --version` (stdout line 1) |
| `fix5_geometry_setup` | `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup` | `current` | `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` (json_pointer:/checks/sim_header_geometry) |
| `prompt_seed_policy` | `seed = 1000003 + ordinal*7919; base card seed 12345` | `current` | `outputs/reports/fix5_fullstat_v2/fix5_source_manifest.json` (random seed policy section) |
| `delayed_exactpos_seed` | `260613` | `current` | `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` (json_pointer:/seed) |
| `step05_rng_seed` | `260512` | `current` | `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` (json_pointer:/normalization/rng_seed) |
| `focused_signal_seed` | `260616` | `current` | `outputs/reports/fix5_fullstat_v2/fix5_source_manifest.json` (random seed policy section) |
| `delayed_transport_events` | `1000000` | `current` | `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` (json_pointer:/checks/delayed_transport_counts) |
| `production_cuts` | `Explicit G4ProductionCuts values are not printed in the recovered fix5 run log; EM process/range-table parameters are logged for DefaultRegionForTheWorld.` | `not_explicitly_reported_in_run_log` | `runs/step02_instant_fix5_fullstat_v2/logs/Background_n_fullsphere20_rep05_part01.log` (no production-cut keyword match; EM/range-table parameters around lines 520-700) |
| `radioactive_decay_data_version` | `RadioactiveDecay4.3.2; G4ENSDFSTATE1.2.3; PhotonEvaporation3.2` | `current_megalib_environment_data_tree` | `/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/share/Geant4-10.2.3/data` (directory entries; run log confirms G4RadioactiveDecay at line 39) |
| `custom_megalib_or_geant4_patches` | `No Geant4 toolkit bottom-code modification is identified for the Laue optics audit; custom Laue branch counters are application-level optics code, not a Geant4 source patch. No additional custom MEGAlib/Geant4 patch inventory was identified in this audit.` | `current_scoped_audit` | `stepwise_maintenance/step04_opticsim/outputs/step04_opticsim_audit.json` (fields geant4_bottom_code_modified=false and custom_laue_only_branch_counters=true) |

Important: the run-log Geant4 version is `geant4-10-02-patch-03`; `geant4-config --version = 11.2.0` only describes the current shell executable and is not the historical Cosima run authority.

Explicit production-cut values were not recovered from the run log; do not present a numeric cut table unless the generating configuration is separately located. The custom-code statement is scoped to recovered audits and run logs, not a full source-control archaeology of every historical MEGAlib checkout.
