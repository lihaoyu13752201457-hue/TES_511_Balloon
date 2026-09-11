# Prompt-511 Old-Like CsI/Material Topology Candidate

Status: load/overlap-ready geometry scaffold; not a promoted MC result.

Purpose:

- Restore an old-like active/material column inside the thin-Al side-wall leakage radius using CsI as the primary material.
- Preserve the current side signal port; this candidate leaves a keepout of phi 165..195 deg and z -7.9..-2.5 cm, wider than the current outer side-port gap.
- Avoid ROI, spot-r90, or analysis-window suppression. The geometry must stand on material topology.
- Keep W out of the default candidate because W-only diagnostics carry activation and neutron-prompt risk.

Generated files:

- geometry setup: `outputs/reports/prompt511_oldlike_topology_20260620/geometry_oldlike_topology/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_oldlike_csi_material_topology.geo.setup`
- geometry file: `outputs/reports/prompt511_oldlike_topology_20260620/geometry_oldlike_topology/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_oldlike_csi_material_topology.geo`
- detector map: `outputs/reports/prompt511_oldlike_topology_20260620/geometry_oldlike_topology/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_oldlike_csi_material_topology.det`
- migrated source cards: `outputs/reports/prompt511_oldlike_topology_20260620/source_cards_oldlike_topology`
- overlap source: `outputs/reports/prompt511_oldlike_topology_20260620/overlap_oldlike_topology.source`

Geometry change:

- added active CsI envelope: r `11.6..12.86 cm`.
- added thin Al skins: inner r `11.56..11.58 cm`, outer r `12.88..12.89 cm`.
- side lower/full continuity: z `-13.55..-7.9 cm`.
- side signal keepout: phi `165..195 deg`, z `-7.9..-2.5 cm`.
- upper service continuity: z `2..28 cm`, phi `5..355 deg` with a +x notch.
- estimated added CsI mass: `17.6318 kg`.
- estimated added Al mass: `0.246769 kg`.

Selected-current-event ray proxy:

- intercepted selected events: `75/80`.
- intercepted selected rate: `0.0509416 cps`.
- missed selected rate: `0.00339611 cps`.
- path length stats: `{"max_cm": 3.579802301929134, "median_cm": 1.5540578512786716, "min_cm": 1.2602335892883467, "p10_cm": 1.2741174006230933, "rate_weighted_mean_cm": 1.6970711932669003}`.

Claim boundary:

- This scaffold only says the geometry is generated and source cards point at it.
- The straight-line ray proxy is not an MC prompt rate and does not include CsI self-activity, Compton refill, neutron/muon prompt, delayed activation, or signal transport.
- Promotion would require focused-signal preservation, prompt e+/n/mu+ smokes with native CsI detector entries, then separate activation/isotope accounting.
