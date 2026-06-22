# Step07 v3p5 Center-Finger Source Cases

Status: `PASS_V3P5_STEP07_SOURCE_CASES_FULLSTAT_V2_EXACTPOS_M20000_S260613`.

Claim level: V3P5_L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING_FULLSTAT_V2_EXACTPOS_M20000_S260613.

This `fullstat_v2_exactpos_m20000_s260613` source-case layer uses the v3p5 Step05 focused EventList detector response and does not change geometry, Step02 transport, or Step05 selection.

Authority:
- optics design: `balloon511_f10m_ge111_511line_a1`
- A_eff(511): `20.0848 cm2`
- T_atm ref: `0.739042`
- W2 response: `11.8117` cps/(ph cm^-2 s^-1)
- W2 instrument background: `0.0627261` cps

Checks:
- A reference W2 final rate at `1e-4`: `0.00118117` cps
- B diffuse proxy W2 final rate: `7.39691e-06` cps
- source-case rows: `48`

Outputs:
- response authority: `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/v3p5_response_authority.csv`
- source-case rates: `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/source_case_rates.csv`
- summary JSON: `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/source_case_summary.json`

Limitations:
- B diffuse is a low-stat aperture-flux proxy, not a focal-spot Cosima source;
- broad spectra and off-axis EventLists are not rerun;
- W2 background inherits the selected-event statistics of the chosen Step05 label.
