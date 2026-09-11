# Validation Matrix

| Module | Check | Current status |
| --- | --- | --- |
| Channel vector math | Specular reflection preserves angle and unit length | Unit test |
| Channel R/A/T table | Probabilities are non-negative and sum to one | Unit test |
| Channel two-wall toy | `R=1` exits after analytic bounce count; `A=1` absorbs on first wall | Integration test |
| 511-CAM channel baseline | Throughput near 0.80, effective area near 50.89 cm2, d90 focal spot near 3.6 cm | Integration test and CLI output |
| W/Si physical reflectivity candidate | xraydb multilayer table is normalized and angle-sensitive | Unit test and generated CSV |
| W/Si independent Parratt cross-check | Manual s-polarization Parratt recursion matches the generated xraydb multilayer W/Si table on the 511 keV theta grid | Unit test and cross-check run output |
| Channel table-driven mode | Constant `R=1` survives and constant `A=1` absorbs | Integration test |
| Four-ring channel diagnostic | Per-ring summaries cover all four rings and calibrated per-ring angles give near-target 80% survival | Integration test and run output |
| Detector-only TES/BGO prototype | Reads optics `phase_space.csv`, writes standard `hits.csv` and `event_summary.csv`, and reproduces configured 65% stack efficiency / 390 eV FWHM / 93% line-window benchmark | Unit/integration test and run output |
| Staged IO contract | Validates `phase_space`, `optics_history`, detector `hits`, `event_summary`, and detector crosslinks so optics and TES/BGO can remain separate simulations | Unit test and full-run validation output |
| Geant4 detector-only scaffold | Reads optics `phase_space.csv`, builds minimal Bi TES + BGO geometry, records raw Geant4 edep, and writes contract-compatible `hits.csv` / `event_summary.csv` | CMake build, integration test, 1000-event smoke, and contract validation |
| Geant4 Laue multiring Darwin scaffold | Five-ring Ge(111) table-driven Laue optics uses Zachariasen/Darwin mosaic diffraction probabilities, writes diffracted/transmitted phase space, full optics history, per-ring summaries, and WRL visualization | CMake build, integration test, 100000-event run, and contract validation |
| Laue Darwin benchmark | Cu/Au published Barriere et al. 2009 cases are reproduced within 0.03 absolute tolerance for peak diffraction efficiency and reflectivity | Unit test and `runs/laue_darwin_benchmark` |
| Laue Ge(111) Kohnle 1998 benchmark | Direct Ge(111) APS thesis endpoints for 3 mm, 3 arcsec mosaic crystals are reproduced within 0.02 absolute tolerance at 200 and 500 keV | `runs/laue_kohnle1998_ge111_benchmark/summary.json` |
| Laue Bragg vector audit | Every tile in the five-ring Ge(111) configuration satisfies Bragg angle, deflection, and non-overlap geometry checks | `runs/laue_bragg_geometry_audit/summary.json` |
| Laue Darwin sensitivity scan | Mosaicity/thickness uncertainty is scanned for Ge(111) 480-550 keV to quantify model dependence before final material-specific validation | `runs/laue_darwin_sensitivity/summary.json` |
| Laue independent PyTTE check | PyTTE 1.0 Takagi-Taupin perfect-crystal Ge(111) Laue scan at 500/511 keV gives peak diffracted branch above the mosaic Darwin branch and near-conserved forward+diffracted flux | `runs/laue_pytte_ge111_check/summary.json` |
| Geant4 channel 4-ring effective scaffold | Ring-calibrated effective boundary process reproduces target 4-ring throughput/Aeff/spot scale and writes optics contract tables | CMake build, integration test, 20000-event run, and contract validation |
| Geant4 channel 4-ring multi-bounce scaffold | Four 511-CAM rings use W/Si table lookup per bounce, write per-bounce `optics_history.csv`, reproduce calibrated 80%/50.89 cm2/3.6 cm scale, and preserve stricter `paper_bend + paper_once` and `paper_bend + paper_once + si_length` diagnostics showing the remaining path/open-area/absorption gap | CMake build, integration test, 100000-event calibrated run, 20000-event diagnostic runs, and contract validation |
| Channel physics-confidence audit | Dense W/Si table removes coarse critical-angle interpolation, critical-angle scale is checked, and the remaining calibrated/non-wall-by-wall assumptions are explicitly flagged | `records/2026-05-20_channel_physics_confidence_audit.html` and `runs/channel/physics_confidence_audit/summary.json` |
| Laue physics-confidence audit | Bragg geometry, Darwin/Zachariasen benchmark status, Kohnle Ge(111) endpoint, PyTTE cross-check, and remaining non-100% material/alignment gaps are explicitly graded | `records/2026-05-20_laue_physics_confidence_audit.html` and `runs/laue_physics_confidence_audit/summary.json` |
| Laue Bragg geometry | 511 keV Ge(111) wavelength/radius/focal-length consistency | Unit test |
| Laue toy focusing | `p_diff=1,p_abs=0` sends all photons to focal spot | Integration test |
| Geant4 channel process nucleus | `GammaChannelReflection.cc` compiles and links as `libgamma_optics_geant4.a` against local Geant4 | Compile/build check |
| Geant4 two-wall process demo | `R=1` reflects twice and exits; `A=1` absorbs; `T=1` leaks | Executable smoke test |
| Geant4 two-wall table-driven channel demo | `GammaChannelReflection` reads the W/Si CSV reflectivity table, logs per-boundary R/A/T and action rows, and reproduces the expected two-bounce survival scale | Executable integration test and audit run |
| Geant4 single curved channel v0 | Segmented curved-wall volumes use the same boundary process and write `phase_space.csv` plus per-boundary `optics_history.csv`; 12 m bend case exposes too-large local grazing angle | Executable integration test and audit run |
| Single curved geometry scan | Sweeps bend angle and segment count to quantify the tradeoff between W/Si survival and the 46 mm / 12 m focusing bend estimate | `runs/geant4_channel_single_curved_scan/summary.json` and scan plot |
| Single curved gap scan | Sweeps half-gap at low bend and 46 mm / 12 m bend; confirms shrinking gap does not rescue W/Si survival for the simple 12 m curved-channel interpretation | `runs/geant4_channel_single_curved_gap_scan/summary.json` and scan plot |
| Four-ring geometry constraint estimate | Compares configured focusing bends with calibrated theta and effective bounce bookkeeping; estimates that 6-13 small-angle reflections are needed if deflection accumulates as `2Ntheta` | `runs/channel_geometry_constraints/summary.json` and constraint plot |
| Channel bounce/path reconciliation | Brackets the current 1-3 effective bounces and 6-13 calibrated-theta estimate against the Shirazi/Bloser 17-38-reflection lineage clue | `runs/channel_bounce_path_reconciliation/summary.json` and reconciliation plot |
| Project-level review packet | Rebuilds the progress PDF, runs the project audit, and writes a GPT Pro review packet with key artifact hashes | `reports/project_audit/audit_report.md` and `reports/gpt_pro_review_packet.md` |

Next validation steps:

- Resolve the single-channel tension exposed by the scan: W/Si-surviving bends are far smaller than the simple 46 mm / 12 m focusing bend estimate.
- Use the gap scan, bounce-count estimate, and bounce/path reconciliation to recover the actual Shirazi/IDL channel geometry rather than promoting the current simple curved-channel interpretation to 4-ring Geant4.
- Treat `channel_4ring_multibounce_demo` as the current Channel handoff scaffold, using `si_length` path absorption only as a conservative diagnostic, then replace its parameterized path with full wall-by-wall channel geometry once the original IDL/path model is recovered.
- Keep detector-only scaffolds as staged-interface regressions; do not prioritize TES/BGO mass-model refinement until optics is stable.
- Extend the new Kohnle 1998 Ge(111) endpoint check with digitized figures or a full table if publication-level material-specific uncertainties are required.
- Add independent optical-constant/table provenance beyond Chantler/xraydb if publication claims require it.
