# Bgo_sample Step02 Smoke Transport

Status: `PASS_BGO_SAMPLE_STEP02_ALLPARTICLE_SMOKE_TRANSPORT`.

Scope: prompt and activation-build-up smoke transport only. This is an all-particle source-card connectivity check at tiny statistics, not a full Step02 production, not a delayed source, and not a Step05--Step08 BGO sensitivity result.

Source and geometry:
- source cards: `config/megalib_sources_fullsphere20_bgo_sample_tilt45`
- geometry setup: `Bgo_sample/Bgo_sample.geo.setup`
- far-field radius: `60.0 cm`
- BGO threshold: `70.0 keV`
- attenuation check: `PASS` with max relative difference `0.07311828916996332`

Smoke runs:
- pair instant: `2/2` jobs passed, `512` generated particles
- pair buildup: `2/2` jobs passed, `512` generated particles
- all-particle instant: `8/8` jobs passed, `596` generated particles
- all-particle buildup: `8/8` jobs passed, `596` generated particles
- all-particle selected particles: `alpha, eminus, eplus, gamma, muminus, muplus, n, p`

Boundary:
- This closes BGO source-card migration and prompt/buildup Cosima transport connectivity for all eight source-card particle classes.
- Full BGO Step02 still requires production statistics, not this 596-event smoke scale.
- Supersession note: full-stat v2 exact-position BGO delayed transport, Step05 detector response, Step06--Step08 mission-time significance, and the BGO-vs-CsI exact-position material-control comparison have since passed for the production `bgo_sample_fullstat_v2_exactpos` label. This file is retained only as the all-particle prompt/buildup smoke-connectivity record.

Outputs:
- summary JSON: `Bgo_sample/step02_smoke_summary.json`
- pair instant run: `runs/step02_bgo_sample_smoke_instant`
- pair buildup run: `runs/step02_bgo_sample_smoke_buildup`
- all-particle instant run: `runs/step02_bgo_sample_allparticle_smoke_instant`
- all-particle buildup run: `runs/step02_bgo_sample_allparticle_smoke_buildup`
