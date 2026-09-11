# Farfield Geometry Audit

- status: `PASS`
- radius unique: `True`
- radius cm: `60.0`
- area from pi R^2: `11309.733552923255`
- normalization area: `11309.733552923255`
- area relative diff: `0.0`
- MEGAlib evidence: `MCSource.cc` contains the spherical start-area `pi R^2` formula and multiplies far-field flux by start-area average area.
- Runner evidence: `run_equiv2602_pipeline_NEW_GEO.py` computes `area_cm2 = pi * R^2` and `prompt_time_s = gamma_events / (gamma_flux * area_cm2)`.
