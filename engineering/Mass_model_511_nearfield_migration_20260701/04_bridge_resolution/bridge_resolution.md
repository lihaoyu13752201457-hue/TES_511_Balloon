# Bridge Resolution

generated_at_utc: `2026-07-07T15:02:28.172269+00:00`
status: `OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`

The previous `BLOCKED_OPTICS_BRIDGE` belonged to the old independent OF1 optics-local branch. In this new branch, the candidate is a detector MEGAlib geometry replacement:

- new detector candidate: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- no independent optics local geometry is introduced in this migration package
- source cards point directly at the detector geometry
- detector prompt/buildup/delayed transport can proceed without an optics-to-detector transfer calculation

Non-claims:
- This does not promote any OF1 optics-background result.
- This does not overwrite the old nearfield engineering final status.
- This does not make a no-effect claim for the Mass_model_511 geometry.
