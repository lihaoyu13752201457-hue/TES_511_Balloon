# opticsim memory

## 2026-05-21 Channel optics plan completion checkpoint

- Loaded and used the `max-factual-confidence` skill standard for the Channel
  plan completion pass: claim boundaries were separated into high-confidence,
  medium-confidence, and open provenance items.
- New plan-completion artifacts:
  - `analysis/complete_channel_optics_plan.py`
  - `tests/integration/test_channel_optics_plan_completion.py`
  - `records/2026-05-21_channel_optics_plan_completion.md`
  - `runs/channel_optics_plan_completion/summary.json`
- Public-geometry wall-by-wall optics status:
  - `runs/channel_wallbywall_rebuild/summary.json`: 20000 primaries, 5804
    survived, transmissivity `0.2902`, effective area `18.4617 cm2`,
    survivor mean bounces `19.6239`, mean grazing angle `7.54866e-5 rad`.
  - This line no longer forces `n_bounce` or calibrated grazing angle; it is
    still a reconstruction because original IDL/IMD artifacts are unavailable.
- Optics-only contract for wall-by-wall run:
  - `runs/io_contract_validation_channel_wallbywall_rebuild/summary.json`
  - `ok=true`, 5804 `phase_space` rows, 209969 `optics_history` rows.
- IDL/Python optics + Geant4 detector handoff smoke:
  - Ran `/tmp/opticsim-build-g4-11.4.0/detector_only_demo` on
    `runs/channel_wallbywall_rebuild/phase_space.csv`.
  - Output: `runs/geant4_detector_wallbywall_1k/summary.json`, 1000 simulated,
    7102 hits, TES detection fraction `0.895`, BGO veto fraction `0.132`.
  - Full optics+detector contract:
    `runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json`,
    `ok=true`; source/detector event-id check treats the 1000 detector events
    as an allowed subset of 5804 phase-space photons.
- Current claim boundary:
  - High confidence: current-stage public-geometry wall-by-wall optics and
    wall-by-wall-to-detector handoff are implemented and contract-validated.
  - Medium confidence: the wall-by-wall line is the right IDL/IMD-style truth
    generator direction.
  - Open: original IDL path accounting, IMD reflectivity export, independent
    reflectivity provenance, and validated TES/BGO flight detector model.
- HTML confidence report:
  - `analysis/build_channel_confidence_report.py`
  - `records/2026-05-21_channel_confidence_report.html`
  - `runs/channel_confidence_report/summary.json`
  - Conclusion: conservative public-geometry Channel model now has high
    current-stage research-prototype confidence because Python wall-by-wall
    gives transmissivity `0.2902` and Geant4 strict public-parameter gives
    `0.2961` (about 2.01% relative difference). The 80% headline remains
    medium/calibrated, not first-principles.
- Independent closure package:
  - `analysis/build_channel_independent_closure.py`
  - `records/2026-05-21_channel_independent_closure.html`
  - `runs/channel_independent_closure/summary.json`
  - Optical-constant/reflectivity closure now passes: CXRO/Henke-range 30 keV
    constants agree with xraydb/Chantler at about `0.03%-1.30%`; 511 keV
    electron-density delta agrees at about `0.14%-1.07%`; manual
    IMD/DarpanX-equivalent Parratt recursion matches xraydb multilayer
    reflectivity with max `|delta R|=0`.
  - No-fudge CAM511 comparison still does not derive the 80% headline. Best
    idealized variant is roughness `0 nm`, no Si path absorption, `T=0.7615`.
    Literature-relevant roughness `1 nm`, no Si path absorption gives `T=0.7369`;
    roughness `1 nm` with Si path absorption gives `T=0.3659`.
  - Current interpretation: reflectivity provenance is no longer the main
    blocker; the remaining 80% gap is path/open-area/Si-absorption accounting
    or original IDL/IMD convention.

## 2026-05-20 Channel line current state after physics-confidence audit

- Channel optics has been advanced from Python/effective ray tracing to a
  Geant4 11.4.0 four-ring, table-driven, parameterized multi-bounce scaffold.
- Important correction after careful audit:
  - The first 511 keV W/Si table was too coarse near the critical-angle drop.
    It made the calibrated theta depend on a broad linear interpolation interval.
  - `analysis/audit_channel_physics_confidence.py` now generates a dense table
    at `data/reflectivity/WSi_511keV_parratt_grid_dense.csv` and recalibrates
    `data/channel/cam511_channel_rings.csv`.
  - C++ CSV parsing in `ReflectivityTable.cc` was hardened to handle
    subnormal tiny numeric values in dense tables.
- Important implementation artifacts:
  - `geant4_app/src/channel_4ring_multibounce_demo.cc`
  - `data/channel/cam511_channel_rings.csv`
  - `data/reflectivity/WSi_511keV_parratt_grid_dense.csv`
  - `analysis/audit_channel_physics_confidence.py`
  - `tests/integration/test_geant4_channel_4ring_multibounce_demo.py`
  - `systems/channel/README.md`
  - `analysis/build_channel_group_meeting_ppt.py`
- CAM511 source material:
  - paper: Shirazi et al., `The 511-CAM Mission...`, arXiv `2206.14652`
  - local PDF/text: `records/channel_external_sources/511cam_arxiv_2206_14652.pdf`
    and `.txt`
  - aligned public inputs: 511 keV, 12 m focal length, four rings at 2.25/3/3.75/4.5 cm,
    W/Si 30/150 nm, 9 cm aperture, 3.6 cm focused beam, 80% channel
    transmissivity, 50.89 cm2 optics effective area.
- Main Channel run:
  - output: `runs/channel/geant4_4ring_multibounce_calibrated/`
  - 100000 primaries, 80075 survived, 17531 absorbed, 2394 leaked
  - transmissivity `0.80075`, effective area `50.9415 cm2`, spot d90 `3.61328 cm`
  - output tables: `phase_space.csv`, `optics_history.csv`, `per_ring_summary.csv`,
    `summary.json`
  - WRL visualization: `runs/channel/geant4_4ring_multibounce_calibrated/channel_4ring_multibounce_scene.wrl`
  - `geant4_bottom_code_modified=false`; Geant4 toolkit source was not modified.
- Diagnostic Channel run:
  - output: `runs/channel/geant4_4ring_multibounce_paper_bend_openfraction/`
  - mode: `theta-policy=paper_bend`, `open-fraction-policy=paper_once`
  - 20000 primaries, transmissivity `0.5614`, effective area `35.7147 cm2`,
    spot d90 `3.59367 cm`
  - interpretation: the stricter direct public-parameter combination does not
    naturally recover 80%; remaining uncertainty is the original IDL channel
    path/open-fraction accounting, not Geant4 source-code capability.
- Paper-formula pressure-test Channel run:
  - output: `runs/channel/geant4_4ring_multibounce_paper_formula_strict/`
  - mode: `theta-policy=paper_bend`, `open-fraction-policy=paper_once`,
    `path-absorption-policy=si_length`
  - 20000 primaries, 5922 survived, 10356 absorbed, 6907 of those from
    `si_path_absorption`, 3722 leaked
  - transmissivity `0.2961`, effective area `18.8371 cm2`, spot d90 `3.59982 cm`
  - interpretation: adding an explicit Si path attenuation term makes the
    public-parameter pressure test much more conservative; this is deliberately
    a diagnostic, not the default calibrated handoff model.
- Physics-confidence audit:
  - `records/2026-05-20_channel_physics_confidence_audit.html`
  - `runs/channel/physics_confidence_audit/summary.json`
  - conclusion: `headline_performance_is_fully_first_principles=false`.
  - W/Si critical-angle estimate at 511 keV is `1.642949e-4 rad`; the calibrated
    theta values are physically plausible in magnitude, but if the public bend
    angles are accumulated as `2Ntheta`, the rings need about 6-13 bounces, not
    the current 1/2/2/3 calibrated bookkeeping.
  - Focal spot D90 is currently imposed by a configured Gaussian target, not
    produced by full wall-by-wall channel geometry.
- Channel group-meeting deck:
  - `records/2026-05-20_channel_geant4_group_meeting_presentation.html`
  - assets in `records/channel_group_ppt_assets/`
  - generated directly from the local run CSV/JSON files.
- Validation after Channel push:
  - build: `cmake --build /tmp/opticsim-build-g4-11.4.0 -j2` passed.
  - new integration test: `python3 -m unittest tests.integration.test_geant4_channel_4ring_multibounce_demo` passed.
  - full suite: `python3 -m unittest discover -s tests` ran 35 tests with
    `OK (skipped=6)`.
  - IO contract for main Channel run: `ok=true`, `phase_space` rows `80075`,
    `optics_history` rows `284317`.
  - IO contract for strict paper-formula run: `ok=true`, `phase_space` rows
    `5922`, `optics_history` rows `119696`.
  - Runtime environment note: current shell can retain MEGAlib/Geant4 10.2
    `G4*DATA` variables; run Geant4 11.4 jobs from `env -i` plus
    `source /home/ubuntu/software/geant4-11.4.0-install/bin/geant4.sh` to avoid
    the ENSDFSTATE mismatch abort.
- Cleanup:
  - transient Channel smoke runs were removed from `runs/channel/`.
  - retained main calibrated run, two diagnostic runs, physics-confidence audit,
    and optics-only IO validation outputs.
- Current Channel claim boundary:
  - Strong engineering confidence for a Geant4 event-bookkeeping scaffold that
    reproduces CAM511 headline optics metrics and writes audit-grade handoff tables.
  - Not a 100% first-principles or publication-grade wall-by-wall recovery of
    the original IMD/IDL ray trace; that still requires the missing channel
    path/open-area/absorption-accounting details.

## 2026-05-20 Laue physics-confidence audit under the same standard

- New audit artifacts:
  - `analysis/audit_laue_physics_confidence.py`
  - `records/2026-05-20_laue_physics_confidence_audit.html`
  - `runs/laue_physics_confidence_audit/summary.json`
- Audit conclusion:
  - Status: `AUDIT_COMPLETE_HIGH_CONFIDENCE_FOR_CURRENT_STAGE`.
  - Laue is more physically closed than Channel because the main performance is
    driven by Bragg geometry and a Zachariasen/Darwin mosaic table, not by a
    headline-efficiency calibration.
  - Current stage does not require exact same-lens experimental closure. The
    appropriate claim is formula-driven Geant4 plus adjacent literature
    benchmarks; assembly/alignment, material batch, and crystal non-uniformity
    uncertainties remain future systematics if the work moves toward publication
    or engineering freeze.
- Key audit numbers:
  - Main run unchanged: `runs/geant4_laue_multiring_darwin`, 100000 primaries,
    diffracted `24638`, absorbed `35894`, transmitted `39468`, diffraction
    fraction `0.24638`, spot d90 `0.220582 cm`.
  - Bragg radius recomputation agrees with config to about `0.012 mm`.
  - Bragg tile audit checks 360 tiles with max deflection residual
    `1.42868e-6 rad`.
  - Barriere 2009 Cu/Au benchmark remains `ok=true`, max peak-efficiency error
    `0.00893`, max reflectivity error `0.01581`.
  - Kohnle 1998 Ge(111) endpoint benchmark remains `ok=true`, max endpoint
    error `0.01349`.
  - PyTTE perfect-crystal cross-check remains `ok=true`; it is an independent
    sanity check, not a mosaic-table replacement.
- Channel improvement made during this audit:
  - `channel_4ring_multibounce_demo.cc` now caches per-ring `nBounce/theta/RAT`
    instead of looking up the dense reflectivity table for every event.
  - It now also supports `--path-absorption-policy si_length`, which records
    `si_path_absorption` rows and writes `n_path_absorbed`/`path_survival` to
    the run outputs.
  - `analysis/audit_channel_physics_confidence.py` now also reports a
    paper-formula pressure test including `R^N`, open fraction, and a Si
    path-length absorption estimate; this makes the remaining path/absorption
    ambiguity explicit.

## 2026-05-20 Laue line current state before channel push

- Laue optics has been advanced from toy/constant probability to a table-driven
  Geant4 11.4.0 scaffold using a Zachariasen/Darwin mosaic-crystal efficiency
  table.
- Important implementation artifacts:
  - `external_baseline/laue_raytrace_py/mosaic_darwin.py`
  - `external_baseline/laue_raytrace_py/build_mosaic_darwin_table.py`
  - `geant4_app/include/optics/LaueEfficiencyTable.hh`
  - `geant4_app/src/optics/LaueEfficiencyTable.cc`
  - `geant4_app/src/laue_multiring_table_demo.cc`
  - `data/laue/Ge111_480_550keV_darwin_mosaic_table.csv`
  - `data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- Main Laue run:
  - output: `runs/geant4_laue_multiring_darwin/`
  - 100000 primaries, 5 Ge(111) rings, 480/500/511/530/550 keV, 8.3 m focal length
  - diffracted `24638`, absorbed `35894`, transmitted `39468`
  - diffraction fraction `0.24638`, spot d90 `0.220582 cm`
  - WRL visualization: `runs/geant4_laue_multiring_darwin/laue_multiring_scene.wrl`
  - `geant4_bottom_code_modified=false`; Geant4 toolkit source was not modified.
- Laue validation:
  - Barriere 2009 Cu/Au Darwin benchmark: `runs/laue_darwin_benchmark/summary.json`,
    max peak-efficiency error `0.00893`, max reflectivity error `0.01581`.
  - Kohnle 1998 direct Ge(111) 200-500 keV endpoint check:
    `runs/laue_kohnle1998_ge111_benchmark/summary.json`, max endpoint error `0.01349`.
    The 500 keV calculated value is `0.433551`, from formula and absorption:
    Darwin no-abs peak `0.494320` times Ge 3 mm transmission `0.877066`; no
    correction/fudge factor was used.
  - PyTTE 1.0 perfect-crystal Takagi-Taupin check:
    `runs/laue_pytte_ge111_check/summary.json`; it is a sanity check, not a
    mosaic-table replacement.
  - Bragg geometry audit:
    `runs/laue_bragg_geometry_audit/summary.json`, 360 tiles checked, max
    deflection residual about `1.43e-6 rad`.
  - Sensitivity scan:
    `runs/laue_darwin_sensitivity/summary.json`.
- Laue group-meeting deck:
  - `records/2026-05-20_laue_group_meeting_presentation.html`
  - assets in `records/laue_group_ppt_assets/`
  - old intermediate Laue HTML reports were deleted to keep `records/` clean.
- Current Laue claim boundary:
  - Strong research-prototype confidence for the table-driven Ge(111) Laue
    Geant4 chain and literature alignment.
  - Not a 100% publication-grade material closure because the current five-ring
    table uses 30 arcsec mosaicity and about 10 mm thickness, while Kohnle's
    directly checked Ge(111) endpoint is about 3 arcsec and 3 mm.
- Full tests after Laue deck generation: `python3 -m unittest discover -s tests`
  gave `33 passed, 6 skipped`.

## 2026-05-17 initial implementation notes

- Source guidance read from `/home/ubuntu/下载/CODEX_GEANT4_LAUE_CHANNEL_GUIDE.md` and `/home/ubuntu/下载/500keV_Laue_511keV_Channel_Geant4_调研报告.pdf`.
- Empty working directory except hidden placeholders, so this turn starts a maintainable baseline from scratch.
- Project priorities from the docs:
  - Do not rely on standard Geant4 gamma EM processes for focusing optics.
  - Do not geometrically model every 30 nm W + 150 nm Si multilayer.
  - Build effective-surface / effective-channel models with explicit `R/A/T/open_fraction` handling.
  - Keep every placeholder clearly labeled as toy or calibrated.
  - Use explicit units in variable names.
  - Always emit seed/config/metadata with run outputs.
- This implementation pass focuses on the highest-confidence deliverable available in an empty repo:
  - Python 511-CAM channel ray-tracing baseline.
  - Python Laue toy focusing baseline.
  - Tests for geometry, reflection, probability handling, and benchmark-style outputs.
- Geant4 C++ process work remains the next implementation tier after the ray-tracing and detector interfaces are stable.

## Key benchmark targets

- Channel optics baseline:
  - Energy: 511 keV.
  - Focal length: 12 m.
  - Rings: radii 2.25, 3.0, 3.75, 4.5 cm.
  - W/Si multilayer: 30 nm W + 150 nm Si.
  - Focused beam diameter target: 3.5-3.6 cm.
  - Transmissivity target: about 0.80.
  - Optics effective area target: about 50.89 cm2.
- Laue toy:
  - Use Bragg law and `F = r / tan(2 theta_B)`.
  - Start with constant diffraction/absorption probabilities and parameterized focus.
  - Do not claim dynamical diffraction until a validated external table is introduced.

## Current design choices

- Channel ray tracer uses an effective per-ring axisymmetric thin-lens model for focusing plus a separate two-wall bounce kernel for specular-reflection unit/integration tests.
- `open_fraction` is treated exactly once: the configurable calibrated transmissivity is the total survival probability unless explicitly overridden. This avoids double-counting open fraction.
- Random transport uses accept/reject sampling, not mixed event weights.
- Phase-space CSV is the bridge to future Geant4 detector-only work.
- Laue toy config uses Ge(111), 511 keV, focal length 8.3 m, and a single ring radius of about 6.166 cm from Bragg law.
- Smoke result before full test pass:
  - Channel 20k photons with seed 12345: transmissivity 0.8037, spot d90 3.612 cm, effective area 51.13 cm2.
  - Laue 10k photons with seed 12345 before radius fix: all diffracted, spot d90 about 1.03 cm; radius was adjusted to match 8.3 m.
- Full baseline runs after fixes:
  - Channel 100k photons with seed 12345: transmissivity 0.8021, spot d90 3.609 cm, effective area 51.03 cm2.
  - Laue 50k photons with seed 12345: all diffracted, focal-length check 8.299997 m, spot d90 1.035 cm.
- Local Geant4 is available at `/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/bin/geant4-config`, version 10.2.3.
- Added compile-checked Geant4 process nucleus `geant4_app/src/optics/GammaChannelReflection.cc` with constant toy R/A/T, boundary check by volume-name token, surface-normal reflection, absorption, and leak-kill policy.
- C++ audit fix: use post-step boundary position for `GetGlobalExitNormal()` and propose a tiny `1e-9 mm` post-reflection displacement to reduce boundary re-trigger loops.
- Geant4 compile check passed with:
  `g++ -std=c++17 $(geant4-config --cflags) -Igeant4_app/include -c geant4_app/src/optics/GammaChannelReflection.cc -o /tmp/GammaChannelReflection.o`
- CMake configure/build also passed in `/tmp/opticsim-build`, producing `libgamma_optics_geant4.a`.

## 2026-05-17 extended implementation notes

- Added `xraydb`-based W/Si 30/150 nm reflectivity generator:
  - Script: `data/reflectivity/generate_wsi_parratt_table.py`.
  - Output: `data/reflectivity/WSi_511keV_parratt_grid.csv`.
  - Default table spans `1e-8` to `5e-3 rad` at 511 keV.
  - Summary: `R>=0.5` extends to about `1.49e-4 rad`; high-angle reflectivity goes to zero.
- Added table-driven channel tracing:
  - CLI option: `--reflectivity-table`.
  - Supports `fixed`, `ring_bending`, and `ring_bending_per_bounce` theta policies.
  - Uses per-bounce accept/reject, so multi-bounce survival is naturally `R^n`.
  - Reflectivity lookup now interpolates in theta and still rejects table-range extrapolation.
- Reflectivity-driven results:
  - Fixed `theta=5e-5 rad`, 20k photons: transmissivity `0.99015`, effective area `62.99 cm2`.
  - `ring_bending_per_bounce`, 20k photons: transmissivity `0`; this demonstrates that total bending angle is not the local grazing angle.
  - Theta scan found target-like angle `1.496e-4 rad`; 50k photons at this angle gave transmissivity `0.79732`, spot d90 `3.599 cm`, effective area `50.72 cm2`.
- Added analysis scan:
  - Script: `analysis/scan_reflectivity_theta.py`.
  - Outputs in `runs/reflectivity_theta_scan_zoom/`.
- Added Geant4 two-wall demo:
  - Source: `geant4_app/src/channel_two_wall_demo.cc`.
  - CMake target: `channel_two_wall_demo`.
  - Initial primary-position shift strategy caused Geant4 10.2 boundary loops for `R=1`; fixed by killing the boundary-primary and spawning a reflected secondary.
  - Smoke results with `timeout 10s /tmp/opticsim-build/channel_two_wall_demo ...`:
    - `R=1,A=0,T=0`: `boundary=2 reflect=2 absorb=0 leak=0`.
    - `R=0,A=1,T=0`: `boundary=1 reflect=0 absorb=1 leak=0`.
    - `R=0,A=0,T=1`: `boundary=1 reflect=0 absorb=0 leak=1`.

## 2026-05-17 four-ring diagnostic

- Added explicit four-ring output to channel runs:
  - `per_ring_summary.csv`
  - `per_ring_summary.json`
- Added `analysis/run_4ring_diagnostic.py` for the W/Si table-driven 4-ring run.
- Fixed-theta 4-ring result with `theta=1.496e-4 rad`, 100k photons:
  - total transmissivity `0.7978`
  - effective area `50.75 cm2`
  - spot d90 `3.610 cm`
  - ring survival: ring0 `0.879`, ring1 `0.777`, ring2 `0.780`, ring3 `0.684`
  - interpretation: common local grazing angle plus different bounce counts makes outer ring underperform.
- `ring_bending_per_bounce` diagnostic run at 20k photons gives zero transmission in all rings, confirming this is not the correct local grazing-angle policy for the xraydb W/Si table.
- Added `analysis/calibrate_4ring_theta.py` to choose one effective grazing angle per ring for the target survival.
- Ring-calibrated 4-ring result, 100k photons:
  - total transmissivity `0.79942`
  - effective area `50.8569 cm2`
  - spot d90 `3.605 cm`
  - ring theta map:
    - ring0 `1.5044773216627076e-4 rad`
    - ring1 `1.4947488385194609e-4 rad`
    - ring2 `1.4947488385194609e-4 rad`
    - ring3 `1.4912572180977586e-4 rad`
  - per-ring survival: ring0 `0.79797`, ring1 `0.79943`, ring2 `0.79981`, ring3 `0.80181`

## 2026-05-17 progress PDF report

- Added `reports/build_progress_pdf.py`.
- Generated `reports/opticsim_progress_report.pdf`.
- PDF has 6 pages and summarizes:
  - implemented Python channel ray tracer, W/Si reflectivity table, 4-ring calibrated effective model, Laue toy baseline, and Geant4 two-wall demo;
  - key 4-ring calibrated metrics: transmissivity `0.79942`, effective area `50.8569 cm2`, spot d90 `3.605 cm`;
  - per-ring survival and effective-area contribution plots;
  - W/Si reflectivity curve, fixed-theta scan image, per-ring theta calibration table;
  - comparison against fixed-theta, wrong bending/bounce policy, Laue toy, and Geant4 smoke tests;
  - current validation status and residual risks.
- Verified with `pdfinfo`: 6 pages, file size about 850 KB.
- Verified first page can be rendered with `pdftoppm`.

## 2026-05-17 detector-only TES/BGO prototype

- Added detector-only Python backend:
  - Config: `config/detector_tes_bgo.yaml`.
  - Package: `external_baseline/detector_response_py/`.
  - CLI: `external_baseline/detector_response_py/run_detector_only.py`.
- Model status:
  - calibrated/probabilistic detector response fed by optics `phase_space.csv`;
  - not a full Geant4 energy-deposition model.
- Implemented:
  - 8-layer Bi TES absorber, 20x20 pixels, 1.45 x 1.45 x 2.0 mm pixels;
  - phase-space propagation to detector plane;
  - pixel mapping and first-interaction layer sampling;
  - `hits.csv` in the guide detector-hit schema;
  - `event_summary.csv` with total TES edep, single/multihit flags, BGO veto, reco energy, and line-window selection;
  - diagnostic plots: detector spectrum, TES pixel map, event outcomes.
- Real 4-ring calibrated detector-only run:
  - Command: `python3 external_baseline/detector_response_py/run_detector_only.py --source runs/channel_4ring_calibrated_v2/phase_space.csv --out runs/detector_only_4ring_calibrated_v2 --seed 20260517`.
  - Input photons from 4-ring optics: `79942`.
  - Geometric active-pixel acceptance: `0.83731`.
  - TES detection fraction total: `0.54232`.
  - TES detection given active pixel: `0.64769`.
  - Unvetoed detected line-window fraction: `0.93047`.
  - Measured peak FWHM: `392.07 eV`.
  - BGO self-veto on TES detected events: `0.01015`.
  - Selected line-window events: `39930`, selected fraction total `0.49949`.
- Fixed a detector summary bug:
  - `bgo_veto_fraction_of_tes_detected` originally counted pass-through BGO veto events without TES hits;
  - corrected numerator to only TES-detected events with BGO veto.
- Added tests:
  - `tests/unit/test_detector_geometry.py`;
  - `tests/integration/test_detector_only.py`.
- Full Python test suite now has `17` tests passing.
- Updated README, physics assumptions, and validation matrix.
- Refreshed `reports/opticsim_progress_report.pdf`:
  - now 7 pages, about 907 KB;
  - added detector-only TES/BGO page with spectrum, pixel map, and metrics table;
  - verified with `pdfinfo`, `pdfimages`, and page-5 `pdftoppm` render.
- Re-ran CMake/Geant4 checks after detector update:
  - `cmake --build /tmp/opticsim-build` OK.
  - `channel_two_wall_demo 1 1 0 0`: `boundary=2 reflect=2 absorb=0 leak=0`.
  - `channel_two_wall_demo 1 0 1 0`: `boundary=1 reflect=0 absorb=1 leak=0`.
  - `channel_two_wall_demo 1 0 0 1`: `boundary=1 reflect=0 absorb=0 leak=1`.

## 2026-05-17 staged IO contract

- User clarified that optics and TES/BGO mass models do not need direct one-world coupling because they are far apart; staged simulation with phase-space handoff is acceptable and likely preferable.
- Implemented explicit staged CSV contract validator:
  - Package: `external_baseline/io_contract_py/`.
  - CLI: `analysis/validate_io_contract.py`.
- Contract tables validated:
  - `phase_space.csv`: guide primary table / post-optics photons.
  - `optics_history.csv`: optics provenance and losses.
  - `hits.csv`: detector raw hits.
  - `event_summary.csv`: detector event aggregation.
  - detector crosslinks: hit event IDs and per-event TES/BGO aggregation consistency.
- Real full-run validation:
  - Command: `python3 analysis/validate_io_contract.py --out runs/io_contract_validation`.
  - Overall status: PASS.
  - Rows:
    - phase_space `79942`
    - optics_history `100000`
    - hits `66886`
    - event_summary `79942`
    - detector_crosslinks `79942`
  - `event_summary` has five extra diagnostic columns: `status`, `x_det_mm`, `y_det_mm`, `in_line_window`, `selected_signal`; these are backward-compatible extensions beyond the guide's minimum fields.
- Added `tests/unit/test_io_contract.py`.
- Full Python test suite now has `19` tests passing.
- Updated README, physics assumptions, and validation matrix to state the staged optics/detector interface policy.
- Refreshed `reports/opticsim_progress_report.pdf`:
  - now 8 pages, about 930 KB;
  - added "分步模拟接口契约" page;
  - verified page 3 render with `pdftoppm`.
- Re-ran CMake/Geant4 checks after IO-contract update:
  - `cmake --build /tmp/opticsim-build` OK.
  - `channel_two_wall_demo 1 1 0 0`: `boundary=2 reflect=2 absorb=0 leak=0`.
  - `channel_two_wall_demo 1 0 1 0`: `boundary=1 reflect=0 absorb=1 leak=0`.
  - `channel_two_wall_demo 1 0 0 1`: `boundary=1 reflect=0 absorb=0 leak=1`.

## 2026-05-17 Geant4 detector-only scaffold

- Added standalone Geant4 detector-only executable:
  - Source: `geant4_app/src/detector_only_demo.cc`.
  - CMake target: `detector_only_demo`.
- Function:
  - Reads staged `phase_space.csv`.
  - Starts photons at local detector entrance using phase-space x/y and direction.
  - Builds minimal 8-layer Bi TES pixel stack:
    - 20x20 pixels per layer.
    - 1.45 x 1.45 x 2.0 mm pixels.
    - 8 layers, direct placements in world.
  - Builds BGO side and bottom shields:
    - side thickness 2 cm.
    - bottom thickness 5 cm.
  - Uses `G4EmStandardPhysics`.
  - Records raw Geant4 energy deposition through a sensitive detector.
  - Writes contract-compatible `hits.csv`, `event_summary.csv`, and `summary.json`.
- First smoke uncovered a real C++/Python CSV portability bug:
  - Python-generated CSV used CRLF line endings.
  - C++ header parser saw `source_tag\r`.
  - Fixed `SplitCSV()` to trim whitespace/CR/LF from cells.
- Added C++ detector integration test:
  - `tests/integration/test_geant4_detector_only_demo.py`.
  - It runs `/tmp/opticsim-build/detector_only_demo` on a temporary phase-space CSV if the executable exists.
  - It validates outputs with the same IO contract.
- Strengthened IO contract:
  - `detector_crosslinks` now also checks `total_tes_edep_keV` against TES hit energy sums.
  - Added `source_detector_event_ids` check to ensure detector event IDs are sourced from phase_space.
  - Subset detector runs are allowed and reported as warnings.
- Real Geant4 detector-only runs:
  - 50-event smoke: `runs/geant4_detector_only_smoke`, contract PASS.
  - 1000-event reference: `runs/geant4_detector_only_1k`, contract PASS.
- 1000-event reference metrics:
  - `n_simulated`: `1000`
  - `n_hits`: `6256`
  - `n_tes_detected`: `771`
  - `n_bgo_veto`: `277`
  - `tes_detection_fraction`: `0.771`
  - `bgo_veto_fraction`: `0.277`
  - `total_tes_edep_keV`: `373176`
  - `total_bgo_edep_keV`: `133405`
- Added generic detector contract plotting:
  - `analysis/plot_detector_contract_outputs.py`.
  - Outputs for the 1k Geant4 run:
    - `runs/geant4_detector_only_1k/detector_contract_spectrum.png`
    - `runs/geant4_detector_only_1k/detector_contract_pixel_map.png`
- Validation after this update:
  - `cmake --build /tmp/opticsim-build` OK.
  - Full Python test suite: `20` tests passing.
  - `runs/io_contract_validation_geant4_detector_1k`: PASS.
- PDF refreshed:
  - `reports/opticsim_progress_report.pdf` now has 9 pages, about 1.0 MB.
  - Added "Geant4 Detector-only Scaffold" page.
  - Verified page 7 render with `pdftoppm`.

## 2026-05-17 residual-risk closure push

- User asked to continue toward closing listed residual risks and keep the PDF updated.
- W/Si physical table cross-check:
  - Added manual s-polarization Parratt recursion:
    - `manual_parratt_reflectivity_s()` in `external_baseline/channel_raytrace_py/parratt_reflectivity.py`.
    - `compute_manual_parratt_rows()`.
  - Added `analysis/crosscheck_wsi_parratt.py`.
  - Cross-check output: `runs/wsi_parratt_crosscheck/`.
  - Result: `n_rows=240`, `max_abs_delta_R=0.0`, `mean_abs_delta_R=0.0`, `status=PASS`.
  - Important boundary: this does not call `xraydb.multilayer_reflectivity`, but it still uses xraydb/Chantler material optical constants. Publication-level provenance still needs IMD/DarpanX or another independent optical-constant source.
  - Added/updated tests in `tests/unit/test_parratt_reflectivity.py`.
- Geant4 Laue one-ring toy:
  - Added `geant4_app/src/laue_one_ring_demo.cc`.
  - CMake target: `laue_one_ring_demo`.
  - Implements a local `LaueToyProcess` as a `G4VDiscreteProcess`.
  - Builds a Ge crystal one-ring tile scaffold.
  - Uses constant `p_diff=1`, `p_abs=0`.
  - Writes `phase_space.csv`, `optics_history.csv`, `summary.json`.
  - Run: `/tmp/opticsim-build/laue_one_ring_demo 2000 runs/geant4_laue_one_ring 20260517`.
  - Result: `n_primaries=2000`, `n_diffracted=2000`, `diffraction_fraction=1.0`, contract PASS.
  - Plot: `runs/geant4_laue_one_ring/focal_spot.png`.
  - Added integration test: `tests/integration/test_geant4_laue_one_ring_demo.py`.
  - Boundary: toy process, not dynamical diffraction.
- Geant4 4-ring channel effective scaffold:
  - Added `geant4_app/src/channel_4ring_effective_demo.cc`.
  - CMake target: `channel_4ring_effective_demo`.
  - Builds four rings of channel tile volumes.
  - Implements local `Channel4RingEffectiveProcess` as a `G4VDiscreteProcess`.
  - Uses ring-calibrated effective survival probabilities from the Python 4-ring result.
  - Writes `phase_space.csv`, `optics_history.csv`, `summary.json`.
  - Run: `/tmp/opticsim-build/channel_4ring_effective_demo 20000 runs/geant4_channel_4ring_effective 20260517`.
  - Result:
    - `n_primaries=20000`
    - `n_survived=15943`
    - `transmissivity=0.79715`
    - `effective_area_cm2=50.7125`
    - `spot_d90_cm=3.59411`
    - contract PASS.
  - Plot: `runs/geant4_channel_4ring_effective/focal_spot.png`.
  - Added integration test: `tests/integration/test_geant4_channel_4ring_effective_demo.py`.
  - Boundary: effective survival/focus scaffold, not curved-channel wall-by-wall reflection geometry.
- IO contract updates:
  - `analysis/validate_io_contract.py` now accepts `none/null/-` for omitted tables.
  - Laue and channel optics-only Geant4 runs can validate only `phase_space` + `optics_history`.
- Generic detector/contract plotting:
  - `analysis/plot_detector_contract_outputs.py` already supports Geant4 detector-only plots.
- Documentation updated:
  - `README.md`
  - `docs/physics_assumptions.md`
  - `docs/validation_matrix.md`
  - `data/reflectivity/README.md`
- Validation after this push:
  - `cmake --build /tmp/opticsim-build` OK.
  - Full Python/integration suite: `23` tests passing.
  - `runs/io_contract_validation_geant4_laue_one_ring`: PASS.
  - `runs/io_contract_validation_geant4_channel_4ring_effective`: PASS.
  - `runs/io_contract_validation_geant4_detector_1k`: PASS.
- PDF refreshed:
  - `reports/opticsim_progress_report.pdf` now has 12 pages, about 1.3 MB.
  - Added W/Si Parratt cross-check page.
  - Added Geant4 4-ring channel scaffold page.
  - Added Geant4 Laue one-ring toy page.
  - Updated validation/final-risk page to 23 OK and current residual boundaries.
  - Render-checked pages 4, 7, 9, and 12 with `pdftoppm`.
- Final smoke after PDF refresh:
  - `channel_two_wall_demo 1 1 0 0`: `boundary=2 reflect=2 absorb=0 leak=0`.
  - `channel_two_wall_demo 1 0 1 0`: `boundary=1 reflect=0 absorb=1 leak=0`.
  - `channel_two_wall_demo 1 0 0 1`: `boundary=1 reflect=0 absorb=0 leak=1`.
  - `pdfinfo reports/opticsim_progress_report.pdf`: 12 pages, about 1.3 MB.

## 2026-05-17 project-review readiness push

- User asked to treat the work as a project assessment and bring it to the level where GPT Pro can review it against the original research-plan MD.
- Added project-level audit tooling:
  - `analysis/run_project_audit.py`
  - Runs 11 checks: Python unittest suite, CMake build, three Geant4 two-wall smoke cases, Python detector IO contract, Geant4 detector IO contract, Geant4 Laue IO contract, Geant4 channel IO contract, W/Si Parratt cross-check, and PDF readability via `pdfinfo`.
  - Final result: `PASS`, 11 checks, duration `43.928 s`.
  - Report: `reports/project_audit/audit_report.md`.
- Added GPT Pro review packet tooling:
  - `analysis/build_gpt_pro_review_packet.py`
  - Writes `reports/gpt_pro_review_packet.md` and `reports/gpt_pro_review_manifest.json`.
  - Packet states the review objective, top-level evidence, explicit claim boundaries, reproduction commands, key artifacts, GPT Pro review questions, and SHA256 hashes for key files/artifacts.
  - Important boundary in packet: the project is ready for staged prototype/scaffold review, not a publication-grade end-to-end instrument claim.
- Updated the PDF:
  - `reports/opticsim_progress_report.pdf` now has 13 pages.
  - Added "GPT Pro 审核就绪状态" page with audit PASS, 11 audit checks, 23 tests OK, review packet READY, and explicit review-boundary table.
  - Render-checked page 13 with `pdftoppm` and `view_image`.
- Updated `docs/validation_matrix.md` with a project-level review-packet row.
- Final verification after this push:
  - `python3 analysis/run_project_audit.py --out reports/project_audit`: PASS.
  - `pdfinfo reports/opticsim_progress_report.pdf`: 13 pages, generated 2026-05-17 21:46:50 CST.
  - `python3 analysis/build_gpt_pro_review_packet.py`: regenerated final packet and manifest hashes.

## 2026-05-17 optics-mainline next-task push

- User added `CODEX_NEXT_STEPS_OPTICSIM.md` to the project and clarified that detector mass-model refinement should not be the mainline. Current priority is Geant4 focusing optics itself, ideally a Geant4 focusing-optics system simulation.
- Interpreted the new route as:
  - Keep detector code only as staged-interface regression protection.
  - Push channel optics first: baseline freeze, table-driven per-bounce process, then curved-wall and 4-ring wall-by-wall geometry.
- Added baseline freeze/regression tooling:
  - `analysis/freeze_baseline.py`
  - `analysis/compare_to_baseline.py`
  - Outputs in `reports/baseline/`: `baseline_metrics.json`, `baseline_manifest.json`, `baseline_report.md`, `baseline_compare_report.md`.
  - Current self-compare: PASS.
- Added Geant4 table-driven per-bounce channel nucleus:
  - `geant4_app/include/optics/ReflectivityTable.hh`
  - `geant4_app/src/optics/ReflectivityTable.cc`
  - `GammaChannelReflection` now supports both old constant R/A/T mode and CSV table-driven lookup.
  - Added optional per-boundary history recording with event id, track id, grazing angle, R/A/T, pre/post directions, position, and action.
- Added two-wall table-driven executable:
  - `geant4_app/src/channel_two_wall_table_demo.cc`
  - CMake target: `channel_two_wall_table_demo`.
  - Constant checks:
    - `R=1,A=0,T=0`, 3 events -> `boundary=6 reflect=6 absorb=0 leak=0`.
    - `R=0,A=1,T=0`, 3 events -> `boundary=3 reflect=0 absorb=3 leak=0`.
    - `R=0,A=0,T=1`, 3 events -> `boundary=3 reflect=0 absorb=0 leak=3`.
  - W/Si table run:
    - Command: `/tmp/opticsim-build/channel_two_wall_table_demo --n 1000 --energy-keV 511 --theta-rad 1.5e-4 --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid.csv --out runs/geant4_channel_two_wall_table --seed 20260517`
    - Result: `n_boundary=1845`, `n_reflect=1556`, `n_absorb=251`, `n_leak=38`, `n_survived=711`, `survival_fraction=0.711`.
    - Table lookup at 1.5e-4 rad: `R=0.84345805142`, `A=0.13709801725`, `T=0.0194439313303`.
    - Boundary history rows equal `n_boundary`.
- Added tests:
  - `tests/integration/test_baseline_freeze.py`
  - `tests/integration/test_geant4_channel_two_wall_table_demo.py`
  - Full suite now: 26 tests OK.
- Updated project audit:
  - `analysis/run_project_audit.py` now includes baseline freeze/self-compare, table-driven two-wall constant branches, and W/Si table mode.
  - Final audit: PASS, 17 checks, duration `47.473 s`.
- Updated docs and review packet:
  - `README.md`
  - `docs/physics_assumptions.md`
  - `docs/validation_matrix.md`
  - `reports/gpt_pro_review_packet.md`
  - `reports/gpt_pro_review_manifest.json`
- Updated PDF:
  - `reports/opticsim_progress_report.pdf` now has 14 pages.
  - Added "Geant4 Two-wall Table-driven Channel" page.
  - Final PDF render checks: page 5 table-driven two-wall page and page 14 audit-readiness page.
  - `pdfinfo`: 14 pages, generated 2026-05-17 22:44:43 CST.
- Important current boundary:
  - This is now a table-driven two-wall per-bounce Geant4 channel nucleus.
  - It is not yet segmented curved-wall channel geometry and not yet full four-ring wall-by-wall optics.
  - Next implementation target should be `channel_single_curved_demo` / segmented curved wall, using the same `GammaChannelReflection` + `ReflectivityTable` pathway.

## 2026-05-17 single-curved Geant4 channel v0 push

- Continued along the optics-only mainline.
- Extended `GammaChannelReflection`:
  - Boundary history now records `sourceEventId`, `surfaceCopyNo`, and `surfaceName`.
  - Curved wall segments can use local placement rotation plus navigator normals.
  - Segment end faces are filtered so the curved-wall process does not intentionally reflect off segment end caps.
  - Boundary counter now counts actionable reflective/loss boundary actions, not ignored non-wall faces.
- Added first segmented curved-wall channel executable:
  - `geant4_app/src/channel_single_curved_demo.cc`
  - CMake target: `channel_single_curved_demo`.
  - Supports constant R/A/T and W/Si CSV table-driven mode.
  - Writes `phase_space.csv`, per-boundary `optics_history.csv`, and `summary.json`.
- Key runs:
  - Constant R=1, 12 m bend-angle smoke:
    - Command: `/tmp/opticsim-build/channel_single_curved_demo --n 20 --R 1 --A 0 --T 0 --segments 64 --bend-angle-rad 0.003833333333 --out runs/geant4_channel_single_curved_bend12m_constant --seed 20260517`
    - Result: `n_boundary=60`, `n_reflect=60`, `n_survived=20`, `survival_fraction=1.0`, `max_boundary_per_event=3`, `mean_grazing_angle_rad=2.715e-3`.
  - W/Si table, same 12 m bend:
    - Command: `/tmp/opticsim-build/channel_single_curved_demo --n 200 --segments 64 --bend-angle-rad 0.003833333333 --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid.csv --out runs/geant4_channel_single_curved_bend12m_table --seed 20260517`
    - Result: `n_boundary=200`, `n_absorb=26`, `n_leak=174`, `n_survived=0`, `survival_fraction=0.0`, `mean_grazing_angle_rad=2.575e-3`.
- Important interpretation:
  - The curved-wall Geant4 geometry/process/output path now exists.
  - It exposed a real optics issue: the current 12 m bend single-channel geometry produces local grazing angles around `2.6-2.7e-3 rad`, far above the `~1.5e-4 rad` scale needed for the W/Si table to preserve throughput.
  - This should be handled by segment-convergence and boundary-geometry debugging, not by silently calibrating survival.
  - Segment-count behavior is not yet converged; this remains the next highest-priority optics risk.
- Added integration test:
  - `tests/integration/test_geant4_channel_single_curved_demo.py`
  - Full test suite now: 27 tests OK.
- Updated audit:
  - `analysis/run_project_audit.py` now includes `single_curved_constant` and `single_curved_table`.
  - Final audit: PASS, 19 checks, duration `47.779 s`.
- Updated docs and reports:
  - `README.md`
  - `docs/physics_assumptions.md`
  - `docs/validation_matrix.md`
  - `reports/opticsim_progress_report.pdf`
  - `reports/gpt_pro_review_packet.md`
  - `reports/gpt_pro_review_manifest.json`
- PDF:
  - Now 15 pages.
  - Added "Geant4 Single Curved Channel v0" page.
  - Render-checked single-curved page and final audit-readiness page.
  - `pdfinfo`: 15 pages, generated 2026-05-17 23:23:24 CST.

## 2026-05-17 curved-channel geometry diagnostic scan

- Continued optics-only work after user asked to continue.
- Fixed a concrete geometry bug in `geant4_app/src/channel_single_curved_demo.cc`:
  - Curved wall segment centers were offset by `halfGapMm` only.
  - Correct placement is `halfGapMm + wallThicknessMm / 2`, matching the two-wall geometry convention.
  - Before this fix, the finite wall thickness overlapped into the channel and polluted grazing-angle/bounce diagnostics.
- After the fix:
  - Low bend example `bend_angle_rad=3e-4`, 64 segments:
    - Constant R=1: `mean_grazing_angle_rad=9.609e-5`, `n_reflect=20/20`, `spot_d90_cm=0.462`.
    - W/Si table: `n_survived=199/200`, `survival_fraction=0.995`.
  - 12 m focusing-bend estimate `bend_angle_rad=46 mm / 12000 mm = 3.833e-3`, 64 segments:
    - Constant R=1: `mean_grazing_angle_rad=3.653e-3`, `n_reflect=20/20`, `spot_d90_cm=13.326`.
    - W/Si table: `n_survived=0/200`, `n_absorb=16`, `n_leak=184`, `survival_fraction=0.0`.
- Added automated scan:
  - `analysis/scan_single_curved_geometry.py`
  - Output: `runs/geant4_channel_single_curved_scan/`
  - Artifacts: `single_curved_scan.csv`, `summary.json`, `single_curved_scan.png`.
  - Scan rows: 32 G4 runs.
  - Summary:
    - Best table survival with boundary hit: `0.995` at `bend_angle_rad=3e-4`, `mean_grazing_angle_rad=9.609e-5`.
    - Closest 46mm/12m bend: `bend_angle_rad=3.833e-3`, `mean_grazing_angle_rad=3.653e-3`.
- Interpretation:
  - The current W/Si table can preserve photons only for much smaller bend angles than the simple single-channel `46 mm / 12 m` focusing bend estimate.
  - This is now an explicit optics design tension, not a coding-only issue.
  - Next credible step is to revisit channel curvature/incidence/focusing geometry, then move to 4-ring wall-by-wall only after this tension is understood.
- Updated project audit:
  - Added `single_curved_scan`.
  - Final audit: PASS, 20 checks, duration `58.102 s`.
- Updated docs/reports:
  - `README.md`
  - `docs/physics_assumptions.md`
  - `docs/validation_matrix.md`
  - `reports/opticsim_progress_report.pdf`
  - `reports/gpt_pro_review_packet.md`
  - `reports/gpt_pro_review_manifest.json`
- PDF:
  - Now 16 pages.
  - Added "Single Curved Geometry Scan" page.
  - Render-checked scan page and final audit-readiness page.
  - `pdfinfo`: 16 pages, generated 2026-05-17 23:37:37 CST.

## 2026-05-18 gap scan and four-ring geometry constraint

- Continued optics-only mainline after user asked to keep pushing until the next factual blocker.
- Added formal half-gap scan:
  - Script: `analysis/scan_single_curved_gap.py`.
  - Output: `runs/geant4_channel_single_curved_gap_scan/`.
  - Artifacts: `single_curved_gap_scan.csv`, `summary.json`, `single_curved_gap_scan.png`.
  - Scan: low bend `3.0e-4 rad` and simple 12 m bend `46 mm / 12000 mm = 3.833e-3 rad`; half-gap values `1e-3`, `5e-4`, `2.5e-4`, `1e-4`, `5e-5` mm; 128 segments.
  - Result for 12 m bend:
    - Best W/Si table survival remains `0.0`.
    - Best table case at `half_gap_mm=0.001`: `n_absorb=19`, `n_leak=181`, `n_reflect=0`, `mean_grazing_angle_rad=3.219e-3`.
    - Constant R=1 minimum theta case at `half_gap_mm=5e-5`: `max_boundary_per_event=20`, `mean_grazing_angle_rad=2.990e-3`, `spot_d90_cm=9.834`.
  - Result for low bend:
    - Best W/Si table survival is `0.995` at `half_gap_mm=0.001`, `mean_grazing_angle_rad=9.727e-5`.
    - Shrinking gap adds extra bounces and drops table survival to zero, so gap is not a free tuning knob.
- Added analytic four-ring geometry constraint estimator:
  - Script: `analysis/estimate_channel_geometry_constraints.py`.
  - Output: `runs/channel_geometry_constraints/`.
  - Artifacts: `channel_geometry_constraints.csv`, `summary.json`, `channel_geometry_constraints.png`.
  - Uses `config/cam511_channel_baseline.yaml` and `runs/channel_4ring_calibrated_v2/ring_theta_calibration.json`.
  - If per-bounce small-angle deflection is approximated as `2 theta`, configured ring bends require about:
    - R0: `6.38` bounces vs effective `1`.
    - R1: `8.17` bounces vs effective `2`.
    - R2: `10.51` bounces vs effective `2`.
    - R3: `12.87` bounces vs effective `3`.
  - Max required/effective ratio is `6.38`; max required bounces is `12.87`.
- Updated project files to include the new diagnostics:
  - `analysis/run_project_audit.py` now includes `single_curved_gap_scan` and `channel_geometry_constraints`.
  - `analysis/build_gpt_pro_review_packet.py` now includes the new scripts and summaries.
  - `analysis/freeze_baseline.py` hashes the new diagnostic scripts.
  - `README.md`, `docs/physics_assumptions.md`, `docs/literature_notes.md`, and `docs/validation_matrix.md` now explain the new evidence.
  - `reports/build_progress_pdf.py` now has new pages for gap scan and four-ring geometry constraints.
- Verification after integration:
  - `python3 -m py_compile ...` for new scripts and report builders: PASS.
  - `python3 -m unittest discover -s tests`: 27 tests OK.
  - `cmake --build /tmp/opticsim-build`: PASS.
  - `python3 analysis/run_project_audit.py --out reports/project_audit`: PASS, 22 checks, duration `70.139 s`.
  - `python3 reports/build_progress_pdf.py`: rebuilt `reports/opticsim_progress_report.pdf`.
  - Final `pdfinfo reports/opticsim_progress_report.pdf`: 18 pages, generated 2026-05-18 00:11:10 CST.
  - Render-checked PDF pages 8 and 9 (`Single Curved Gap Scan` and `Four-ring Geometry Constraint`) via `pdftoppm` + `view_image`; plots and text layout are readable.
  - `python3 analysis/build_gpt_pro_review_packet.py`: rebuilt `reports/gpt_pro_review_packet.md` and manifest after final PDF generation.
- Literature/source sanity check:
  - Rechecked 511-CAM arXiv page, OSTI/JATIS soft gamma-ray concentrator page, and Geant4 11.4 `G4XrayReflection` documentation.
  - This supports the boundary that published channel optics uses external multilayer optical properties + IDL ray tracing + MEGAlib/Geant4 detector, while 511 keV W/Si channel optics still needs a custom table-driven Geant4 boundary process.
  - Downloaded OSTI accepted manuscript via `curl -L -o /tmp/soft_gamma_concentrator_2020.pdf https://www.osti.gov/servlets/purl/1716823`.
  - Extracted text with `pdftotext -layout`.
  - Key source clue: the 2020 Shirazi/Bloser lineage paper states the number of reflections varies from 17 to 38 for a parallel beam depending on ring length and radius.
  - This is not the 511-CAM four-ring case directly, but it strongly supports the conclusion that the current 1-3 bounce effective bookkeeping is too shallow for final wall-by-wall channel geometry.
- Current factual conclusion:
  - The current simple segmented single-channel interpretation of the 46 mm / 12 m bend is not physically compatible with the W/Si table.
  - The next credible optics step is to recover the actual Shirazi/IDL channel path and bounce model, not to tune the current simple curved-wall demo or promote it to four-ring wall-by-wall Geant4.

## 2026-05-18 bounce/path reconciliation push

- Continued the optics-only mainline by turning the previous geometry blocker
  into a dedicated diagnostic artifact.
- Added `analysis/reconcile_channel_bounce_path.py`.
- Output directory: `runs/channel_bounce_path_reconciliation/`.
- Artifacts:
  - `summary.json`
  - `channel_bounce_path_reconciliation.csv`
  - `channel_bounce_path_reconciliation.md`
  - `channel_bounce_path_reconciliation.png`
- Diagnostic compares:
  - current effective bookkeeping: `1-3` bounces;
  - calibrated-theta deflection requirement: `6.3805-12.8741` bounces;
  - Shirazi/Bloser lineage clue: `17-38` reflections, used only as a bracket
    and not as a direct 511-CAM parameter.
- Key result:
  - If the 17-38 many-bounce bracket is applied only as a consistency lens,
    the configured ring bends imply local theta from `2.526e-5` to
    `1.129e-4 rad`, below the current calibrated `~1.5e-4 rad` scale.
  - Implied simple parallel-wall half-gap scale is `0.00698-0.15279 um`.
  - This strengthens the conclusion that the missing input is the real
    many-bounce channel path, not detector tuning or a small change to the
    simple single-curved Geant4 demo.
- Integrated the new diagnostic into:
  - `analysis/run_project_audit.py`
  - `analysis/build_gpt_pro_review_packet.py`
  - `analysis/freeze_baseline.py`
  - `reports/build_progress_pdf.py`
  - `README.md`
  - `docs/physics_assumptions.md`
  - `docs/literature_notes.md`
  - `docs/validation_matrix.md`
- Created user-facing record:
  - `records/2026-05-18_bounce_path_reconciliation.md`
- Recreated missing temporary Geant4 build directory:
  - `cmake -S . -B /tmp/opticsim-build -DGeant4_DIR=/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/lib/Geant4-10.2.3`
  - `cmake --build /tmp/opticsim-build`
- Final project audit:
  - `python3 analysis/run_project_audit.py --out reports/project_audit`
  - status `PASS`
  - `23` checks
  - duration `69.321 s`
  - new check `channel_bounce_path_reconciliation` passed.
- Rebuilt `reports/opticsim_progress_report.pdf`:
  - now `19` pages
  - created `2026-05-18 15:10:20 CST`
  - added `Channel Bounce/Path Reconciliation` page
  - final audit page shows `23` checks PASS
  - render-checked page 10 and page 19.
- Regenerated:
  - `reports/gpt_pro_review_packet.md`
  - `reports/gpt_pro_review_manifest.json`
