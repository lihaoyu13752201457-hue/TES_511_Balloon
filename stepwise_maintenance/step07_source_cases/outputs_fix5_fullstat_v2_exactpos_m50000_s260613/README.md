# Step07 fix5 Source Cases

Status: `PASS_FIX5_STEP07_SOURCE_CASES_FIX5_FULLSTAT_V2_EXACTPOS_M50000_S260613_SIGNAL_REPLAYED_NOT_PROMOTION`.

Claim level: FIX5_L1_SOURCE_CASE_RATE_FOLDING_FIX5_FULLSTAT_V2_EXACTPOS_M50000_S260613_SIGNAL_REPLAYED_NOT_FINAL_PROMOTION.

This `fix5_fullstat_v2_exactpos_m50000_s260613` source-case layer uses the current fix5 Step05 detector response, including the fix5 focused-signal replay. Promotion still requires the final fix5 promotion decision artifact.

Authority:
- optics design: `balloon511_f10m_ge111_511line_a1`
- A_eff(511): `20.0848 cm2`
- T_atm ref: `0.739042`
- W2 response: `11.8587` cps/(ph cm^-2 s^-1)
- W2 instrument background: `0.0392162` cps

Checks:
- A reference W2 final rate at `1e-4`: `0.00118587` cps
- B diffuse proxy W2 final rate: `7.4264e-06` cps
- source-case rows: `48`

Outputs:
- response authority: `stepwise_maintenance/step07_source_cases/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/fix5_response_authority.csv`
- source-case rates: `stepwise_maintenance/step07_source_cases/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/source_case_rates.csv`
- summary JSON: `stepwise_maintenance/step07_source_cases/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/source_case_summary.json`

Pending:
- Run Step08 from this source-case output and refresh the promotion decision artifact before any final replacement claim.
- Old new_geo_re prompt/delayed numbers remain blocked as pass/fail gates while benchmark alignment is NOT_ALIGNED.

Limitations:
- B diffuse is a low-stat aperture-flux proxy, not a focal-spot Cosima source;
- broad spectra and off-axis EventLists are not rerun;
- W2 background inherits the selected-event statistics of the chosen Step05 label.
