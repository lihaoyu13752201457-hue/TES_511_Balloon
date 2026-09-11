# Geo-opt S1/BPE/W5 Neutron and Plastic-Skin Audit

Status: `PASS_POSTPROCESS_AUDIT_NOT_GEOMETRY_PROMOTION`

Scope:
- No geometry or Cosima transport was rerun.
- Activation comparison uses ground-state-corrected day-15 activity CSVs.
- Plastic on/off uses the same geo-opt SIM files; only the Step05 active-veto volume definition is changed.

## 1. BPE / shield-stack neutron activation question

- Mass_model_511 fixed total activity: `141.833438 Bq`.
- Geo-opt fixed total activity: `106.482268 Bq` (-24.924%).
- Geo-opt internal activity excluding added GeoOpt layers: `105.564815 Bq` vs Mass `141.833438 Bq` (-25.571%).
- CsI activity: geo `63.0197707 Bq` vs Mass `89.4649266 Bq` (-29.559%).
- Added GeoOpt layer activity itself: `0.917453416 Bq`.

Interpretation: this supports that the current outer shield stack is reducing internal activation versus Mass_model_511. It is not a pure BPE-only causal isolation, because the geometry also changed by adding plastic and a W bottom baffle. A strict BPE-only claim would require an otherwise-identical no-BPE A/B transport.

Neutron energy-depth audit:
- Geo neutron weighted RPIP points: `31016`; internal `30769.5`; CsI `23927.5`.
- Mass neutron weighted RPIP points: `40687.5`; internal `40687.5`; CsI `32453.625`.
- Plot: `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/figures/neutron_energy_depth_hexbin.png`.

## 2. Plastic-skin active veto question

- W2 final background with plastic active: `0.0353806162 cps`.
- W2 final background with plastic disabled in veto accounting: `0.0484939025 cps`.
- W2 on-off delta: `-0.0131132863 cps` (-27.041%).
- Broad 480-550 final background with plastic active: `0.0669927528 cps`.
- Broad 480-550 final background with plastic disabled: `0.0848572726 cps`.
- Broad on-off delta: `-0.0178645197 cps` (-21.052%).

Does it catch positrons?
- Prompt e+ generated events parsed: `1949816`.
- Events with any GeoOpt plastic hit: `345248` (17.707%).
- Events with `sec=e+` ionization hit in plastic: `331474` (17%).
- Events with `sec=e+` plastic deposit >= 50 keV: `141634` (7.264%).
- In W2 prompt e+ TES-window events, events vetoed only when plastic is active: `19`; rate `0.0129017275 cps`.

Important caveat: plastic off here means 'do not count plastic energy as veto'. The plastic material is still present in the transport, so attenuation and scattering by the layer are unchanged.

Tables:
- `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/activation_category_comparison_groundstate_fixed.csv`
- `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/activation_top_volume_comparison_groundstate_fixed.csv`
- `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/neutron_energy_depth_binned.csv`
- `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_direct_rate_comparison.csv`
- `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_prompt_by_tag_comparison.csv`
- `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_timeline_rate_comparison.csv`
