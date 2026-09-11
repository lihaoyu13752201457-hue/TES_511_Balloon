# Optics evidence gap closure

- date: 2026-05-24
- scope: Laue vector diagnostics, Laue fake-table branch regression, Laue detector handoff regression, W/Si reflectivity provenance, Channel wall-by-wall roughness sweep, Channel schema separation
- guardrail: public wall-by-wall transmission was not tuned toward 0.80

## Outputs

- `final_summary.md`
- `laue/`: production Laue vector diagnostics, q/G residual tables, fake-table regression, all-diffract detector handoff regression
- `channel/`: public wall-by-wall roughness sweep summary, per-ring table, grazing-angle histogram
- `reflectivity/`: W/Si local xraydb/manual-Parratt backend cross-check and roughness table
- `schema/`: calibrated handoff vs public wall-by-wall schema separation validation

Deprecated small-smoke Laue vector invariant files were removed from this closure directory after the 100k production diagnostics superseded them.
Large `runs/` directories are treated as reproducible intermediates. The compact audit artifacts above are the committed evidence record.

## Commands

```bash
analysis/run_with_geant4_114.sh cmake --build /tmp/opticsim-build-g4-11.4.0 --target laue_multiring_table_demo laue_multiring_darwin_guan_demo channel_4ring_multibounce_demo detector_only_demo -j2
analysis/run_with_geant4_114.sh /tmp/opticsim-build-g4-11.4.0/laue_multiring_darwin_guan_demo --n 100000 --seed 20260524 --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv --out runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k
python3 analysis/audit_laue_event_invariants.py --run-dir runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k --out records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_event_invariants.md
python3 analysis/audit_laue_vector_diagnostics_groups.py --run-dir runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k
python3 analysis/test_laue_fake_table_no_double_absorption.py
python3 analysis/test_laue_all_diffract_detector_handoff.py
python3 analysis/run_wsi_reflectivity_provenance_sweep.py
analysis/run_with_geant4_114.sh /tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo --n 1000 --seed 20260524 --ring-config data/channel/cam511_channel_rings.csv --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid_dense.csv --out runs/channel/geant4_4ring_multibounce_schema_smoke
python3 analysis/run_channel_wallbywall_rebuild.py --n 1000 --seed 20260524 --out runs/channel_wallbywall_schema_smoke
python3 analysis/run_channel_wallbywall_roughness_sweep.py
python3 analysis/validate_channel_schema_separation.py --calibrated runs/channel/geant4_4ring_multibounce_schema_smoke/summary.json --wallbywall runs/channel_wallbywall_schema_smoke/summary.json --wallbywall runs/channel_wallbywall_roughness_sweep/summary_roughness_0p0nm.json --wallbywall runs/channel_wallbywall_roughness_sweep/summary_roughness_0p2nm.json --wallbywall runs/channel_wallbywall_roughness_sweep/summary_roughness_0p5nm.json --wallbywall runs/channel_wallbywall_roughness_sweep/summary_roughness_1p0nm.json --wallbywall runs/channel_wallbywall_roughness_sweep/summary_roughness_2p0nm.json --wallbywall runs/channel_wallbywall_roughness_sweep/summary_roughness_5p0nm.json --wallbywall runs/channel_wallbywall_roughness_sweep/summary_roughness_10p0nm.json
python3 -m unittest tests.integration.test_geant4_laue_darwin_guan_demo tests.integration.test_geant4_laue_multiring_table_demo tests.integration.test_geant4_channel_4ring_multibounce_demo tests.integration.test_channel_wallbywall_rebuild tests.integration.test_geant4_detector_only_demo
```

## Boundary

- Laue Guan-style diagnostics were run at production scale: 100000 primaries, 24467 diffracted events, per-ring and per-tile residual tables.
- `scattering_q_vector_*` is the explicit name for `|k|*(k_out-k_in)`; `reciprocal_vector_*` remains a backward-compatible alias. `lattice_G_nominal_*` and `lattice_G_perturbed_*` are emitted separately.
- `q-G` and relative Bragg residuals are reported as model-systematics diagnostics. They are nonzero because the current virtual-crystallite model elastically reflects off-Bragg/mosaic-detuned events while the branch probability is scalar-detuning based.
- Table-driven Laue keeps design-focus plane diagnostics, but this remains a scaffold where focal-plane mosaic jitter is separate from strict vector diffraction.
- The all-diffract fake-table detector-handoff regression verifies that Laue diffracted phase-space photons are not dropped at the detector boundary.
- Channel wall-by-wall roughness sweep changes only local W/Si roughness tables and reports transmissivity, effective area, spot D90, event/bounce-weighted reflectivity, and grazing-angle histograms.
- Channel calibrated handoff and public wall-by-wall summaries carry different schema flags and both set `is_first_principles_80pct_closure=false`.
- `xraydb`/manual Parratt is treated as a local backend cross-check only. External IMD/DarpanX/CXRO/Henke provenance remains open.
