# v3p5 Center-Finger 1/10 Transport Closure

Status: `PASS_V3P5_1OF10_TRANSPORT_CLOSURE`.

Claim level: low-stat v3p5 closure through Step00/02/05/06/07/08/09; not paper-facing statistics.

This report joins the current v3p5 geometry, atmospheric background transport, delayed transport, focused optics EventList transport, Step05 L1 selection, Step06 mission-axis fold, Step07 source-case ledger, and Step08 time-dependent significance into one low-statistics closure record. It intentionally does not claim paper-facing statistics.

## Geometry

- setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Step00/proxy/overlap: `STEP00_PASS` / `PROXY_PASS` / `PASS`
- source mass: `91.0127 kg`; active CsI mass: `62.8337 kg`
- detector core: `2256` TES pixel copies
- side-window elevation: `45 deg`
- far-field/setup sphere: `60 cm`
- W side collimator: `2 cm`, x range `[-18.0, -16.0]`

## Step02 Background

- status: `PASS_1OF10_TRANSPORT_CLOSURE`
- instant: `19/19` jobs passed, `1190129` generated particles
- buildup: `19/19` jobs passed, `1190129` generated particles
- fixed delayed source: `786` blocks, `86.382997 Bq`
- delayed transport: `SE=100000`, `ID=100000`, `TE=1140.44737 s`
- summary: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_summary.json`

## Step05 L1 Detector Response

- status: `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1`
- claim level: L1 side-entry Compton/FoV + common Poisson time-axis; direct physical reference-flux scaling added; 1/10 statistics
- broad 480-550 side-Compton/FoV direct rates: prompt `0 s^-1`, delayed `0.0727785 s^-1`, focused signal `0.797172` per unit EventList injection rate
- W2 510.58-511.42 side-Compton/FoV direct rates: prompt `0 s^-1`, delayed `0.0157833 s^-1`, focused signal `0.795747` per unit EventList injection rate
- physical normalization: A_eff `20.0848 cm2`, T_atm `0.739042`, reference injection rate `0.00148435 s^-1` at `1e-4 ph cm^-2 s^-1`
- W2 common-time-axis side-Compton/FoV rate: `0.800563 s^-1` under unit EventList injection-rate normalization
- summary: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_l1/step05_v3p5_centerfinger_l1_response_summary.json`

## Step06 Mission Time Axis

- status: `PASS_V3P5_STEP06_TIME_AXIS_1OF10`
- claim level: V3P5_L1_MISSION_RATE_FOLD_1OF10_NO_NEW_TRANSPORT
- W2 day-15 background/signal: `0.0157833` / `0.00118117` cps
- W2 mission-mean background/signal: `0.0155714` / `0.00117281` cps
- delayed activity scale range: `0.817308` to `1.05152`
- summary: `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_1of10/step06_v3p5_centerfinger_1of10_summary.json`

## Step07 Source Cases

- status: `PASS_V3P5_STEP07_SOURCE_CASES_1OF10`
- claim level: V3P5_L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING_1OF10
- source-case rows: `48`
- W2 response/background: `11.8117` cps/(ph cm^-2 s^-1) / `0.0157833` cps
- A reference W2 final rate: `0.00118117` cps
- summary: `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_1of10/source_case_summary.json`

## Step08 Time-Dependent Significance

- status: `PASS_V3P5_STEP08_TIME_DEPENDENT_1OF10`
- claim level: V3P5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_1OF10
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=12.3501`
- T3/T5: `0.942791` / `2.67299` day
- 20-day 3-sigma flux: `2.42912e-05 ph cm^-2 s^-1`
- accidental loss range: `0.000726453` to `0.000793153`
- low-stat selected W2 background events: `18`
- summary: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_time_dependent_summary.json`

## Step08 L1 Direct Significance

- status: `PASS_V3P5_STEP08_L1_DIRECT_EXPECTATION_1OF10`
- claim level: L1 direct constant-rate expectation from v3p5 Step05 physical reference-flux rates; not a full Step06 mission-axis fold
- headline window: `w2_510p58_511p42`
- background/signal: `0.0157833` / `0.00118117` cps at `1e-4 ph cm^-2 s^-1`
- direct 20-day Z: `12.359`; constant-rate T3: `1.17843 day`; 20-day 3-sigma flux: `2.42738e-05 ph cm^-2 s^-1`
- low-stat selected background events: `18`
- summary: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_l1_significance_summary.json`
- warning: headline W2 background is based on fewer than 50 selected background events

## Step09 Focused Signal

- status: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`
- profile: `f10m_a1_v3p5`
- EventList rows/full transported events: `37194` / `37194`
- EventList radii: `r90=1.02679 cm`, `r95=1.10335 cm`, `rmax=1.55356 cm`
- Be radius: `1.898 cm`
- full SIM: `runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz`
- summary: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json`

## Remaining v3p5 Work

- Higher-statistics production beyond this 1/10 checkpoint
- Exact-position delayed-source sampling replacing axisymmetric RadialProfileBeam compression
- Selection-consistent spatial/profile likelihood and spatial cuts for v3p5
- Diffuse/off-axis EventList treatment beyond the current aperture-flux proxy
