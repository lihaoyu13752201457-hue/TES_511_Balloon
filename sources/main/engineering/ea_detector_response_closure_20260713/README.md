# EA O8 detector-energy-response closure (2026-07-13)

Status: `PASS_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE`

This package applies the manuscript's 420 eV FWHM TES response at the pixel-readout level without modifying retained O8 transport products. Each aggregated TES-pixel deposit receives an independent Gaussian response with sigma = 0.17836 keV, measured hits below 0.3 keV are removed, and the retained W2, 50-keV active-veto, and side-entry Compton/FoV selection is rerun with the measured hit energies.

## Primary W2 result

- Response seed: `26071301`.
- Day-15 selected background: `0.00584951847335` cps (prompt `0.00339303151412`, neutron-delayed `0.00090122560728`, atmospheric-511 `0.00155526135195`).
- Reference-flux signal: `0.00111348117126` cps.
- Folded 20 d counting significance: `18.56329`.
- Folded 20 d 3-sigma flux threshold: `1.6160928e-05` ph cm^-2 s^-1.
- Conservative counting threshold: `4.6132015e-05` ph cm^-2 s^-1.
- Response-convolved Mass_model_511 reference threshold: `4.4425574e-05` ph cm^-2 s^-1.

## Validation

- The response-off replay reproduces every retained Step05/atmospheric cut-flow count and rate exactly: `PASS_EXACT_UNSMEARED_REPRODUCTION`.
- The reference response-off replay reproduces the retained Mass_model_511 Step05 and Step08 authorities: `PASS_EXACT_REFERENCE_STEP08_REPRODUCTION`.
- Detector-response seed convergence: `PASS_RESPONSE_SEED_ENSEMBLE` across `64` deterministic replicas.
- The response ensemble is a numerical integration audit; it is not added as a separate physical systematic uncertainty.

## Authorities

- Retained event catalogue: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step05/work/event_catalog.pkl`.
- Retained Mass_model_511 reference catalogue: `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/work/event_catalog.pkl`.
- Retained atmospheric SIM: `runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712/Atm511SidecarS3dO8_3M.inc1.id1.sim.gz`.
- Machine-readable closure: `engineering/ea_detector_response_closure_20260713/data/o8_energy_response_closure_summary.json`.
- Response replicas: `engineering/ea_detector_response_closure_20260713/data/o8_energy_response_replicas.csv`.
- W2 mission timeline: `engineering/ea_detector_response_closure_20260713/outputs/w2_energy_response_timeline.csv`.
