# Geo-opt S1/BPE/W5 Atmospheric 511 4pi Sidecar Replay

Status: `PASS_GEO_OPT_S1_BPE_W5_ATM511_4PI_SIDECAR_REPLAY`

Scope: EXPACS-like semi-empirical atmospheric e+e- annihilation 511-keV line sidecar for the current geo-opt S1/BPE/W5 geometry. This replaces the 2026-07-07 lower-hemisphere-only atm511 replay in downstream geo-opt conclusions.

## Source Model

- Environment: lat `34` deg, lon `100` deg, alt `38.75` km, Rc `11` GV, depth `3.46147` g cm^-2.
- Nominal 4pi line flux: `0.0515558541132` ph cm^-2 s^-1.
- Up/down split: up `0.0431027869674`, down `0.00845306714584`, r_down `0.196114`.
- Flux closure error: `-2.050e-13` ph cm^-2 s^-1.

## Transport Result

- Generated events: `3000000`
- Observation time: `5146.38 s`
- W2 raw/active/final events: `114` / `114` / `107`
- W2 final nominal atm511 rate: `0.0207913135058` cps
- W2 final transfer per 4pi flux: `0.403277452453` cps / (ph cm^-2 s^-1)
- Sidecar-included W2 background: `0.0561719296626` cps
- Sidecar-included W2 F3(20d): `4.62986036016e-05` ph cm^-2 s^-1

## Files

- Source: `runs/geometry_optimization_20260704/p2_atm511_sidecar_s1_nominal_geo_opt_s1_bpe_w5_20260708/Atm511SidecarS1Nominal3M_GeoOptS1BpeW5.source`
- SIM: `runs/geometry_optimization_20260704/p2_atm511_sidecar_s1_nominal_geo_opt_s1_bpe_w5_20260708/Atm511SidecarS1Nominal3M_GeoOptS1BpeW5.inc1.id1.sim.gz`
- Summary: `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json`
- Bin fluxes: `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/atm511_sidecar_s1_nominal_bin_fluxes.csv`
- Source scenarios: `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/atm511_sidecar_systematic_scenarios.csv`
