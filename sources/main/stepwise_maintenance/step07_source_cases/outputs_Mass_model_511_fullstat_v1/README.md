# Step07 Mass_model_511 Source Cases

Status: `PASS_MASS_MODEL_511_STEP07_SOURCE_CASES_MASS_MODEL_511_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_REPLACEMENT`.

Claim level: MASS_MODEL_511_L1_SOURCE_CASE_RATE_FOLDING_MASS_MODEL_511_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_REPLACEMENT.

This `Mass_model_511_fullstat_v1` source-case layer uses the current-geometry Mass_model_511 Step05 detector response, including the Mass_model_511 focused-signal replay. It is not a no-effect/replacement decision.

Authority:
- optics design: `balloon511_f10m_ge111_511line_a1`
- A_eff(511): `20.0848 cm2`
- T_atm ref: `0.739042`
- W2 response: `11.8476` cps/(ph cm^-2 s^-1)
- W2 instrument background: `0.0480735` cps

Checks:
- A reference W2 final rate at `1e-4`: `0.00118476` cps
- B diffuse proxy W2 final rate: `7.4194e-06` cps
- source-case rows: `48`

Outputs:
- response authority: `stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/Mass_model_511_response_authority.csv`
- source-case rates: `stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/source_case_rates.csv`
- summary JSON: `stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/source_case_summary.json`

Pending:
- Run Step08 from this source-case output before quoting a final 20-day threshold.
- No no-material-effect/replacement decision against fix5 is made by this source-case fold.

Limitations:
- B diffuse is a low-stat aperture-flux proxy, not a focal-spot Cosima source;
- broad spectra and off-axis EventLists are not rerun;
- W2 background inherits the selected-event statistics of the chosen Step05 label.
