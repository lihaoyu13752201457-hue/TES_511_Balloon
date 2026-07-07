# Mass_model_511 P1/P2/P3 Replay - 2026-07-03

Status: `PASS_MASS_MODEL_511_P1_P2_P3_REPLAY_NOT_PAPER_APPLIED`

This replay is specific to the current Mass_model_511 geometry branch. It does
not modify manuscript `.tex` files and does not replace the fix5 paper authority
unless the replacement review is accepted separately.

## P1 Line Width

Current Mass_model_511 W2 authority used here:
`B=0.048073549 cps`,
`S(F0=1e-4)=0.0011847574 cps`,
`Z20d=7.03837`,
`F3=4.262352e-05 ph cm^-2 s^-1`.

Mass_model_511 final-selected sideband continuum density:
`0.000136505 cps/keV`.

Representative optimized-window estimates:
- source FWHM 1.3 keV, bkg FWHM 2.43 keV: opt half-window 0.93 keV, F3=3.770e-05 ph cm^-2 s^-1
- source FWHM 2.4 keV, bkg FWHM 2.43 keV: opt half-window 3.28 keV, F3=4.294e-05 ph cm^-2 s^-1
- source FWHM 5.4 keV, bkg FWHM 2.43 keV: opt half-window 7.10 keV, F3=4.344e-05 ph cm^-2 s^-1

## P2 Atmospheric 511-keV Line

Transport source: `runs/Mass_model_511_nearfield_migration_20260701/p2_atm511_unit_Mass_model_511_fullstat_v1/Atm511LowerUnit3M_MassModel511.source`

Simulation output: `runs/Mass_model_511_nearfield_migration_20260701/p2_atm511_unit_Mass_model_511_fullstat_v1/Atm511LowerUnit3M_MassModel511.inc1.id1.sim.gz`

W2 final unit transfer:
`0.381079 cps / (ph cm^-2 s^-1)`,
from `101` final events.

Harris Rc~11-13 GV scenario:
`F_atm=0.0233016 ph cm^-2 s^-1`,
added background `0.00887975 cps`,
new `F3=4.63933e-05 ph cm^-2 s^-1`.

## P3 Geometry

No new transport is required. The Mass_model_511 Step06--Step08 current-geometry
products keep the same framing boundary: use the reference calculation as a
northern/near-zenith transient or compact-source sensitivity case; Galactic
center observations at 34 deg N remain a separate low-elevation/airmass case.

## Files

- `p1_mass_model_511_linewidth_sensitivity_summary.json`
- `p1_mass_model_511_fixed_w2_linewidth_scan.csv`
- `p1_mass_model_511_optimized_window_linewidth_scan.csv`
- `p1_mass_model_511_spectra_480_550_by_stream_stage.csv`
- `p2_mass_model_511_atm511_transfer_summary.json`
- `p2_mass_model_511_atm511_flux_scenarios.csv`
