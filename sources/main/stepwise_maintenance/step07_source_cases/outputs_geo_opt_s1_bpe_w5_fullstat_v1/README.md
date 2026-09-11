# Step07 geo-opt S1/BPE/W5 Source Cases

Status: `PASS_GEO_OPT_S1_BPE_W5_STEP07_SOURCE_CASES_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_PROMOTION`.

Claim level: GEO_OPT_S1_BPE_W5_L1_SOURCE_CASE_RATE_FOLDING_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_PROMOTION.

This `geo_opt_s1_bpe_w5_fullstat_v1` source-case layer uses the geo-opt Step05 detector response, including the geo-opt focused-signal transport manifest. It is not a promotion or replacement decision.

Authority:
- optics design: `balloon511_f10m_ge111_511line_a1`
- A_eff(511): `20.0848 cm2`
- T_atm ref: `0.739042`
- W2 response: `11.8464` cps/(ph cm^-2 s^-1)
- W2 instrument background: `0.0353806` cps

Checks:
- A reference W2 final rate at `1e-4`: `0.00118464` cps
- B diffuse proxy W2 final rate: `7.41865e-06` cps
- source-case rows: `48`

Outputs:
- response authority: `stepwise_maintenance/step07_source_cases/outputs_geo_opt_s1_bpe_w5_fullstat_v1/geo_opt_s1_bpe_w5_response_authority.csv`
- source-case rates: `stepwise_maintenance/step07_source_cases/outputs_geo_opt_s1_bpe_w5_fullstat_v1/source_case_rates.csv`
- summary JSON: `stepwise_maintenance/step07_source_cases/outputs_geo_opt_s1_bpe_w5_fullstat_v1/source_case_summary.json`

Method caveats:
- Step07 is a rate-level source-case fold from the geo-opt Step05 response; it does not rerun prompt, delayed, or focused Cosima transport.
- It inherits the Step05 bounded high-rate Poisson timeline approximation through the selected geo-opt response summary.
- The focused-signal provenance is the geo-opt signal_transport_manifest.json header, not the fix5 or Mass_model_511 Step09 summary.

Pending:
- Run Step08 from this source-case output before quoting final mission detection potential.
- Compare against Mass_model_511/fix5 with the same selection and active-veto assumptions before making a geometry decision.

Limitations:
- B diffuse is a low-stat aperture-flux proxy, not a focal-spot Cosima source;
- broad spectra and off-axis EventLists are not rerun;
- W2 background inherits the selected-event statistics of the chosen Step05 label.
