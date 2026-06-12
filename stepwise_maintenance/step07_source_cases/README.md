# Step07 Astrophysical Source Cases

Status: `PASS`.

This step adds A/B/C 511-keV source cases above the validated `new_geo_re` detector/background chain. The mono point-source science response is the full Step09 focused EventList detector transport. It does not change geometry, Step02/03 transport, Step05 veto logic, or add optics-mass background production.

## Scope

- Claim level: `L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING`.
- Optics policy: B-FULL Step04/Step09 focused EventList detector response is the science authority.
- The mono source card is the Step09 EventList source; broad spectra remain rate-folding cases until energy-dependent EventLists are run.
- Diffuse B is aperture-integrated and intentionally not emitted as a focal-spot Cosima source.
- Step08 must still do time-dependent significance and accidental-veto folding.

## Authority Numbers

- `A_opt_cm2 = 15.2993`.
- optics design: `balloon511_f9m_ge111_511line`.
- W1 analysis window: `500.994-521.006` keV.
- W2 line window: `510.58-511.42` keV.
- `T_atm_ref = 0.739042`.
- `plane_rate_per_flux = 11.3068` cps/(ph cm-2 s-1).
- `science_final_response = 9.00989` cps/(ph cm-2 s-1).
- `instrument_background_final = 0.783047` cps.

## Closure Checks

- A on-axis mono final closure rel error: `0`.
- A on-axis mono plane-rate closure rel error: `0`.
- B default diffuse final rate: `6.430034e-06` cps.
- B default diffuse / instrument background: `8.211556e-06`.
- V404 redshift narrow proxy response: `0` after tiny-response clamp `1.000000e-100`.
- V404 redshift narrow max final rate: `0` cps.
- FoV proxy radius: `7.24982` arcmin.

## Outputs

- `source_cases_yaml`: `stepwise_maintenance/step07_source_cases/outputs/configs/source_cases_511_ABC.yaml`
- `literature_anchors_yaml`: `stepwise_maintenance/step07_source_cases/outputs/configs/literature_flux_anchors.yaml`
- `optics_response_yaml`: `stepwise_maintenance/step07_source_cases/outputs/configs/optics_response_current_scaffold.yaml`
- `source_spectrum_summary`: `stepwise_maintenance/step07_source_cases/outputs/source_spectrum_summary.csv`
- `diffuse_aperture_foreground`: `stepwise_maintenance/step07_source_cases/outputs/diffuse_aperture_foreground.csv`
- `source_case_rates`: `stepwise_maintenance/step07_source_cases/outputs/source_case_rates.csv`
- `point_vs_diffuse`: `stepwise_maintenance/step07_source_cases/outputs/point_vs_diffuse_discrimination.csv`
- `cosima_source_manifest`: `stepwise_maintenance/step07_source_cases/outputs/cosima_source_manifest.csv`
- `readme`: `stepwise_maintenance/step07_source_cases/README.md`
- figures: `stepwise_maintenance/step07_source_cases/outputs/figures/`

## v3p5 Center-Finger 1/10 Output

Status: `PASS_V3P5_STEP07_SOURCE_CASES_1OF10`.

Output:
`stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_1of10/README.md`.

This branch product uses the v3p5 Step05 focused EventList detector response
and v3p5 Step06 mission-axis authority. It writes A point-source scans, a
Route-B aperture-flux proxy, and C transient benchmark rows for both broad and
W2 selections. It does not rerun diffuse/off-axis EventList transport.

Key v3p5 checks:

- W2 response: `11.8117 cps/(ph cm^-2 s^-1)`.
- W2 instrument background: `0.0157833 cps`.
- A reference W2 final rate at `1e-4`: `0.00118117 cps`.
- Source-case rows: `48`.

## Rebuild

```bash
python3 stepwise_maintenance/step07_source_cases/code/build_step07_source_cases.py
python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py
```
