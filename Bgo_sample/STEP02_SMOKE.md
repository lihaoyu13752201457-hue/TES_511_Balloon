# Bgo_sample Step02 Smoke Transport

Status: `PASS_BGO_SAMPLE_STEP02_SMOKE_TRANSPORT`.

Scope: prompt and activation-build-up smoke transport only. This is not an all-particle Step02 production, not a delayed source, and not a Step05--Step08 BGO sensitivity result.

Source and geometry:
- source cards: `config/megalib_sources_fullsphere20_bgo_sample_tilt45`
- geometry setup: `Bgo_sample/Bgo_sample.geo.setup`
- far-field radius: `60.0 cm`
- BGO threshold: `70.0 keV`
- attenuation check: `PASS` with max relative difference `0.07311828916996332`

Smoke runs:
- instant: `2/2` jobs passed, `512` generated particles
- buildup: `2/2` jobs passed, `512` generated particles
- selected particles: `gamma, p`

Boundary:
- This closes BGO source-card migration and prompt/buildup Cosima transport connectivity only.
- Full BGO Step02 requires all particles and production statistics.
- BGO delayed source, delayed transport, Step05 response, Step06/07/08 significance, and BGO-vs-CsI comparison remain not run for this Bgo_sample package.

Outputs:
- summary JSON: `Bgo_sample/step02_smoke_summary.json`
- instant run: `runs/step02_bgo_sample_smoke_instant`
- buildup run: `runs/step02_bgo_sample_smoke_buildup`
