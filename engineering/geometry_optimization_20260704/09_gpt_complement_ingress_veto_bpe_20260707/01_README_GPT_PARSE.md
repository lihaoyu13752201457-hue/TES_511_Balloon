# GPT Complement Package: W2 Ingress, Veto, BPE Evidence

This directory intentionally contains exactly 10 files for upload to GPT.
It complements the previous `07_clue_1p5e5_20260707` 10-file package, which focused on the 20-day background budget, high-level levers, and geometry visuals.

## What This Adds

- Event-level W2 particle trajectory rows: source point, direction, first recorded volume, TES centroid, and entry proxy.
- Explicit separation of `side_window` versus `side_wall` ingress proxy.
- Event-level veto flags for plastic-skin veto, non-plastic active veto, and Compton/FoV veto.
- Plastic-skin veto on/off evidence and e+ plastic-hit evidence.
- BPE/shield-stack activation and neutron-interaction proxy evidence versus Mass_model_511.

## Read Order For GPT

1. `02_fact_summary.json` for headline facts and caveats.
2. `03_w2_particle_trajectories_enriched.csv` for the event-level ingress geometry.
3. `06_w2_veto_cutflow_by_particle.csv` and `07_w2_event_veto_flags.csv` for veto behavior.
4. `08_plastic_skin_veto_effect.csv` and `09_bpe_neutron_activation_effect.csv` for the plastic/BPE shield evidence.
5. `10_w2_neutron_energy_depth_events.csv` for W2 neutron energy-depth proxy.

## Important Definitions

- W2 window: `510.58-511.42 keV` TES total energy.
- Active threshold: `50 keV` deposited in a veto volume.
- `side_window`: side-envelope entry within +/-15 deg of the local negative-X side-window axis.
- `side_wall`: side-envelope entry outside that side-window proxy.
- Veto priority: plastic skin, then non-plastic active, then Compton/FoV, then final pass.

## Caveats

- BPE effect is not isolated by a no-BPE A/B transport; current evidence is for the S1/BPE/W5 shield stack.
- Plastic-off means post-processing veto accounting off; plastic material remains in transport.
- Entry window is a proxy based on envelope crossing near local negative-X side-window axis, not a CAD boundary scorer.
- Neutron depth table uses first-hit depth proxy, not continuous energy-loss-vs-depth scoring.

## Files

- `01_README_GPT_PARSE.md`: human-readable instructions and previous-package comparison
- `02_fact_summary.json`: machine-readable headline facts, source definitions, and caveats
- `03_w2_particle_trajectories_enriched.csv`: one row per W2 raw TES background event with geometry path and veto class
- `04_w2_entry_geometry_counts.csv`: counts by particle and envelope-entry class, including window vs wall proxy
- `05_w2_theta_phi_binned_counts.csv`: theta/phi histograms by particle and entry class
- `06_w2_veto_cutflow_by_particle.csv`: plastic skin, non-plastic active, Compton/FoV, and final-pass counts by particle
- `07_w2_event_veto_flags.csv`: one row per event with explicit veto flags and deposited veto energies
- `08_plastic_skin_veto_effect.csv`: plastic-skin veto on/off and positron-hit evidence
- `09_bpe_neutron_activation_effect.csv`: BPE/shield-stack neutron activation and neutron RPIP effect summary
- `10_w2_neutron_energy_depth_events.csv`: W2 neutron energy versus first-hit depth proxy event table
