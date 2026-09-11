# opticsim

Baseline code for 500-511 keV focusing-optics simulation work.

Current priority: Geant4 focusing optics. Detector-only code remains in the
tree as a staged-interface regression guard. The Laue line now has a
table-driven five-ring Geant4 scaffold using a Zachariasen/Darwin mosaic
diffraction table. The channel line now has a Geant4 four-ring, table-driven,
multi-bounce parameterized scaffold aligned to the headline 511-CAM optics
numbers; full wall-by-wall IDL geometry recovery remains the next physics
closure step.

The current runnable deliverables are Python baselines:

- calibrated 511-CAM-style channel optics ray tracing;
- calibrated detector-only TES/BGO response fed by optics `phase_space.csv`;
- Laue-lens table-driven Geant4 focusing using Bragg geometry and a benchmarked
  Zachariasen/Darwin mosaic diffraction table;
- 511-CAM channel Geant4 focusing with W/Si table lookup and per-bounce history
  in a four-ring multi-bounce process;
- tests for reflection geometry, probability handling, channel benchmarks, detector response, and Laue geometry.

## Run

```bash
python3 external_baseline/channel_raytrace_py/run_cam511_baseline.py \
  --config config/cam511_channel_baseline.yaml \
  --n 100000 \
  --out runs/channel_baseline

python3 external_baseline/laue_raytrace_py/run_toy_lens.py \
  --config config/laue_toy_baseline.yaml \
  --n 50000 \
  --out runs/laue_toy

python3 analysis/run_4ring_diagnostic.py \
  --n 100000 \
  --out runs/channel_4ring_parratt

python3 analysis/calibrate_4ring_theta.py \
  --n 100000 \
  --out runs/channel_4ring_calibrated

python3 external_baseline/detector_response_py/run_detector_only.py \
  --config config/detector_tes_bgo.yaml \
  --source runs/channel_4ring_calibrated_v2/phase_space.csv \
  --out runs/detector_only_4ring_calibrated_v2 \
  --seed 20260517

python3 analysis/validate_io_contract.py \
  --out runs/io_contract_validation

python3 analysis/crosscheck_wsi_parratt.py \
  --out runs/wsi_parratt_crosscheck

python3 analysis/benchmark_laue_darwin.py

python3 analysis/benchmark_laue_kohnle1998.py

python3 analysis/run_pytte_ge111_check.py
python3 analysis/audit_laue_physics_confidence.py

python3 analysis/freeze_baseline.py --out reports/baseline
python3 analysis/compare_to_baseline.py \
  --baseline reports/baseline/baseline_metrics.json \
  --current reports/baseline/baseline_metrics.json

/tmp/opticsim-build/channel_two_wall_table_demo \
  --n 1000 \
  --energy-keV 511 \
  --theta-rad 1.5e-4 \
  --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid_dense.csv \
  --out runs/geant4_channel_two_wall_table \
  --seed 20260517

/tmp/opticsim-build/channel_single_curved_demo \
  --n 20 \
  --R 1 --A 0 --T 0 \
  --segments 64 \
  --bend-angle-rad 0.003833333333 \
  --out runs/geant4_channel_single_curved_bend12m_constant \
  --seed 20260517

python3 analysis/scan_single_curved_geometry.py \
  --out runs/geant4_channel_single_curved_scan

python3 analysis/scan_single_curved_gap.py \
  --out runs/geant4_channel_single_curved_gap_scan

python3 analysis/estimate_channel_geometry_constraints.py \
  --out runs/channel_geometry_constraints

python3 analysis/reconcile_channel_bounce_path.py \
  --out runs/channel_bounce_path_reconciliation

python3 analysis/audit_channel_physics_confidence.py

/tmp/opticsim-build/detector_only_demo \
  runs/channel_4ring_calibrated_v2/phase_space.csv \
  runs/geant4_detector_only_1k \
  1000 \
  20260517

python3 analysis/plot_detector_contract_outputs.py \
  --hits runs/geant4_detector_only_1k/hits.csv \
  --event-summary runs/geant4_detector_only_1k/event_summary.csv \
  --out runs/geant4_detector_only_1k

/tmp/opticsim-build/laue_one_ring_demo \
  2000 \
  runs/geant4_laue_one_ring \
  20260517

python3 -m external_baseline.laue_raytrace_py.build_mosaic_darwin_table \
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \
  --out-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \
  --mosaic-arcsec 30 \
  --crystallite-um 5 \
  --delta-multiple 4 \
  --n-delta 81 \
  --optimize-thickness

/tmp/opticsim-build-g4-11.4.0/laue_multiring_table_demo \
  --n 100000 \
  --seed 20260520 \
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \
  --out runs/geant4_laue_multiring_darwin

/tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo \
  --n 100000 \
  --seed 20260520 \
  --ring-config data/channel/cam511_channel_rings.csv \
  --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid_dense.csv \
  --out runs/channel/geant4_4ring_multibounce_calibrated

/tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo \
  --n 20000 \
  --seed 20260520 \
  --theta-policy paper_bend \
  --open-fraction-policy paper_once \
  --out runs/channel/geant4_4ring_multibounce_paper_bend_openfraction

/tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo \
  --n 20000 \
  --seed 20260520 \
  --theta-policy paper_bend \
  --open-fraction-policy paper_once \
  --path-absorption-policy si_length \
  --out runs/channel/geant4_4ring_multibounce_paper_formula_strict

python3 analysis/run_channel_wallbywall_rebuild.py \
  --n 20000 \
  --seed 20260521 \
  --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid_dense.csv \
  --out runs/channel_wallbywall_rebuild

python3 analysis/run_channel_wallbywall_rebuild.py \
  --n 5000 \
  --seed 20260521 \
  --no-si-path-absorption \
  --out runs/channel_wallbywall_rebuild_no_si_abs_smoke

python3 analysis/validate_io_contract.py \
  --phase-space runs/channel_wallbywall_rebuild/phase_space.csv \
  --optics-history runs/channel_wallbywall_rebuild/optics_history.csv \
  --hits none \
  --event-summary none \
  --out runs/io_contract_validation_channel_wallbywall_rebuild

env -i HOME="$HOME" USER="$USER" SHELL=/bin/bash \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  bash -lc 'source /home/ubuntu/software/geant4-11.4.0-install/bin/geant4.sh; cd /home/ubuntu/opticsim; /tmp/opticsim-build-g4-11.4.0/detector_only_demo runs/channel_wallbywall_rebuild/phase_space.csv runs/geant4_detector_wallbywall_1k 1000 20260521'

python3 analysis/validate_io_contract.py \
  --phase-space runs/channel_wallbywall_rebuild/phase_space.csv \
  --optics-history runs/channel_wallbywall_rebuild/optics_history.csv \
  --hits runs/geant4_detector_wallbywall_1k/hits.csv \
  --event-summary runs/geant4_detector_wallbywall_1k/event_summary.csv \
  --out runs/io_contract_validation_channel_wallbywall_detector_1k

python3 analysis/complete_channel_optics_plan.py

python3 analysis/build_channel_confidence_report.py

python3 analysis/build_channel_independent_closure.py

/tmp/opticsim-build/channel_4ring_effective_demo \
  20000 \
  runs/geant4_channel_4ring_effective \
  20260517
```

Outputs include `summary.json`, focal-spot PNGs, and CSV tables. The channel
baseline writes `phase_space.csv`, intended as the future Geant4 detector-only
primary-source handoff. Channel runs also write `per_ring_summary.csv/json` for
the four 511-CAM rings. Detector-only runs write standard `hits.csv`,
`event_summary.csv`, a reconstructed-energy spectrum, a TES pixel map, and
event-outcome diagnostics. The IO contract validator checks the staged
`phase_space`, `optics_history`, `hits`, and `event_summary` interface so optics
and detector mass models can remain separate simulations.

If the shell currently has MEGAlib/Geant4 10.2 data variables such as
`G4ENSDFSTATEDATA`, run the 11.4 executables from a clean environment. Otherwise
Geant4 11.4 may load the old ENSDFSTATE data and abort before tracking:

```bash
env -i HOME="$HOME" USER="$USER" SHELL=/bin/bash \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  bash -lc 'source /home/ubuntu/software/geant4-11.4.0-install/bin/geant4.sh; cd /home/ubuntu/opticsim; /tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo --n 500 --seed 20260520 --out runs/channel/geant4_4ring_multibounce_smoke'
```

Generate and use a first W/Si physical candidate reflectivity table:

```bash
python3 data/reflectivity/generate_wsi_parratt_table.py
python3 external_baseline/channel_raytrace_py/run_cam511_baseline.py \
  --config config/cam511_channel_baseline.yaml \
  --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid.csv \
  --fixed-theta-rad 5e-5 \
  --n 20000 \
  --out runs/channel_parratt_theta5e-5
```

## Test

```bash
python3 -m unittest discover -s tests
g++ -std=c++17 $(geant4-config --cflags) -Igeant4_app/include \
  -c geant4_app/src/optics/GammaChannelReflection.cc \
  -o /tmp/GammaChannelReflection.o
cmake -S . -B /tmp/opticsim-build
cmake --build /tmp/opticsim-build
timeout 10s /tmp/opticsim-build/channel_two_wall_demo 1 1 0 0
timeout 10s /tmp/opticsim-build/channel_two_wall_demo 1 0 1 0
timeout 10s /tmp/opticsim-build/channel_two_wall_demo 1 0 0 1
timeout 10s /tmp/opticsim-build/channel_two_wall_table_demo --n 3 --R 1 --A 0 --T 0 --out runs/geant4_channel_two_wall_table_reflect_audit
timeout 10s /tmp/opticsim-build/channel_two_wall_table_demo --n 3 --R 0 --A 1 --T 0 --out runs/geant4_channel_two_wall_table_absorb_audit
timeout 10s /tmp/opticsim-build/channel_two_wall_table_demo --n 3 --R 0 --A 0 --T 1 --out runs/geant4_channel_two_wall_table_leak_audit
/tmp/opticsim-build/detector_only_demo \
  runs/channel_4ring_calibrated_v2/phase_space.csv \
  runs/geant4_detector_only_smoke \
  50 \
  20260517
/tmp/opticsim-build/laue_one_ring_demo 8 runs/geant4_laue_one_ring_smoke 23
/tmp/opticsim-build/channel_4ring_effective_demo 500 runs/geant4_channel_4ring_smoke 29
/tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo --n 500 --seed 20260520 --out runs/channel/geant4_4ring_multibounce_smoke
/tmp/opticsim-build/channel_single_curved_demo --n 5 --R 1 --A 0 --T 0 --segments 64 --bend-angle-rad 0.003833333333 --out runs/geant4_channel_single_curved_smoke --seed 20260517
```

## Scope

This repository does not yet claim a completed wall-by-wall Geant4 channel
geometry. The repository now includes a compile-checked
`GammaChannelReflection` process nucleus with both constant toy R/A/T handling
and table-driven W/Si CSV lookup, plus `channel_two_wall_table_demo` for
per-boundary validation. `channel_single_curved_demo` is the first segmented
curved-wall geometry v0 and is currently diagnostic: it proves the geometry and
history path. The scan in `analysis/scan_single_curved_geometry.py` shows that
small bends can survive with the current W/Si table, while the simple 46 mm /
12 m focusing bend estimate drives the local grazing angle too high. The gap
scan in `analysis/scan_single_curved_gap.py` shows that shrinking the channel
half-gap down to 0.05 um does not rescue the simple 12 m interpretation:
W/Si table survival remains zero. `analysis/estimate_channel_geometry_constraints.py`
adds an analytic consistency check showing that the four configured focusing
bends require roughly 6-13 small-angle reflections at theta near 1.5e-4 rad.

`channel_4ring_multibounce_demo` is the current Channel mainline. It uses the
four 511-CAM rings, looks up the dense W/Si 511 keV table for each bounce,
writes standard `phase_space.csv` and `optics_history.csv`, and reproduces the
paper's headline optics scale in the calibrated mode: about 80% transmissivity,
about 50.89 cm2 effective area, and about 3.6 cm focal-spot D90. Its diagnostic
`paper_bend + paper_once` mode deliberately applies the paper bend angles plus
open fraction as a separate one-time loss; with the current W/Si table this
falls well below 80%, so the result is retained as a model-gap audit rather
than tuned away. A stricter `--path-absorption-policy si_length` mode also
applies the Si 511 keV path attenuation along each ring length, making the
paper-formula pressure test explicit in Geant4 rather than only in the Python
audit. `analysis/audit_channel_physics_confidence.py` is the current
confidence guard: it shows that the headline performance is not yet a 100%
first-principles wall-by-wall prediction.

`analysis/run_channel_wallbywall_rebuild.py` is the first public-geometry
wall-by-wall Channel reconstruction. It samples photons into the 150 nm Si
spacer implied by the 30/150 nm W/Si bilayer, rejects W-layer entry hits by
geometry, lets the bent channel generate wall hits naturally, and looks up
W/Si `R/A/T(E, theta)` at each hit. It does not use calibrated bounce counts or
calibrated grazing angles. Its current 20k run has survivor mean bounce count
near 20, but lower throughput than the calibrated headline model; this is an
explicit physics-closure diagnostic, not a tuned replacement for the mainline.
`analysis/complete_channel_optics_plan.py` records the current plan completion
state: public-geometry wall-by-wall optics is done for the current stage,
Geant4 remains the parameterized optics handoff plus detector/activation
environment, and original IDL/IMD provenance remains open. A 1k detector-only
Geant4 smoke driven by the wall-by-wall `phase_space.csv` passes the full
source/detector contract.
`analysis/build_channel_confidence_report.py` generates the current HTML report
from principles to implementation:
`records/2026-05-21_channel_confidence_report.html`. Its core conclusion is
that the conservative public-geometry Channel model has high current-stage
research-prototype confidence, while the 80% headline remains a calibrated
handoff claim until original IDL/IMD provenance or an independent reflectivity
export closes the gap.
`analysis/build_channel_independent_closure.py` adds that independent closure
package. It cross-checks CXRO/Henke-range optical constants, the 511 keV
electron-density limit, and an IMD/DarpanX-equivalent Parratt recursion, then
compares no-fudge public-geometry wall-by-wall predictions against the CAM511
80%/50.89 cm2 headline. The current result closes reflectivity/constant
provenance but still does not derive the 80% headline without an accounting
gap.
The detector-only TES/BGO response remains a staged-interface scaffold, not the
active mainline.
