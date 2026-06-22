# Optics B-FULL Temporary Memory

Objective: replace only the `new_geo_re` optical focusing handoff with the latest B-FULL Laue model, verify focused spot fits through the Be window, run optics-related smoke transport, and leave non-optics background chain untouched.

Constraints:
- Do not change Step02/03/05 prompt, delayed, veto, time-axis, or significance physics except for validators/docs that reference the optical handoff.
- Keep the detector mass model authority at `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/`.
- Current Be window authority: radius `1.898 cm`, science injection plane `z=16.051 cm`.

Durable decisions:
- Nominal optical model is B-FULL with external per-ring XOP/CRYSTAL rocking-curve map.
- Online Darwin-Hamilton B-FULL run is retained as a closure cross-check.
- The Laue lens hardware mass is not yet inserted into `new_geo_re`; that is a later full-chain background/activation task.

Current artifacts:
- B-FULL online run: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_online_20k/`.
- B-FULL XOP-map run: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_20k/`.
- Step04 audit script now targets B-FULL: `stepwise_maintenance/step04_opticsim/code/build_step04_opticsim_audit.py`.
- Step09 bridge now reads B-FULL XOP-map tracked `focal_crossings.csv` rows (`source_tag=laue_bfull_diffracted`, within Be), not analytic `phase_space.csv`.
- Follow-up checklist: `stepwise_maintenance/step04_opticsim/BFULL_OPTICS_REPLACEMENT_FOLLOWUP.md`.
- 11-section backend integration report: `stepwise_maintenance/OPTICS_BFULL_BACKEND_INTEGRATION_20260601_REPORT.html`.

Verified:
- B-FULL 20k online and XOP-map runs completed with Geant4 11.4 using a clean Geant4 data environment.
- Step04 audit status: `PASS_BFULL_XOPMAP_EVENTLIST_READY`.
- Step09 tracked EventList rows: `4968`; energy range `480-550 keV`; max injected radius `1.4291 cm`, within the 1.898 cm Be window.
- Step09 Cosima smoke: `PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED`, `1000` stored events.
- Step08 focused-spot spatial proxy rebuilt from the 511-keV EventList subset for 511-line science: `995` rows, `r95≈0.2052 cm`, best robust cut `spot_r90≈0.1718 cm`, background `0.01632 cps`, `Z20d≈22.10`.
- Full validator status: `python3 code/tools/validate_new_geo_re.py` -> `PASS`.

Next concrete step:
- Finish git save as `balloon511_0601_CsI` and report remaining full-chain new_geo_re rerun checklist.
