# WP05 Native Activation Oracle Summary

status: `EXPLAINED_MODEL_DIFFERENCE`

- native store serialization comparison: `PASS`
- total relative delta: `0.000000000000000000000000000000000000000000000000000000000000000000000000000098448454577703340818425133503837184887633368451314571641376161041915174014738154`
- ActivationSources probe: `PASS`
- synthetic Activator probe: `PASS`
- tag-aware native Activator oracle: `EXPLAINED_MODEL_DIFFERENCE`

Boundary:
- A single all-tag native Activator is not used because the installed merge path divides by total loaded `TT`.
- The tag-aware native oracle resolves that merge issue, but selected-rate promotion still requires pilot/full transport and Step05 ingestion.
