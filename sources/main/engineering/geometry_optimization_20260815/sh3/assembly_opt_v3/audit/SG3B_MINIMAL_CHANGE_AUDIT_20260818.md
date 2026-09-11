# OptV3 vs simulated SG3B minimal-change audit

Status: `REVIEW_REQUIRED__NOT_OPT_V3_PRODUCTION_AUTHORITY`

## Verdict

No unclassified geometry deletion was found, and the inherited placement
evidence is strong. Nevertheless OptV3 is **not yet an equal-statistics
production authority** because its diagnostic detector map and several
activation-relevant design choices are not closed.

## Closed geometry evidence

- SG3B/OptV3 declared volumes: 237 / 219;
  common: 168.
- Of the 168 common declared volumes,
  38 have classified attribute changes:
  37 TES/Si/Cu core/support volumes share the required
  `(-35.55, 0, +2.40) cm` chimney translation, and
  1 NF2 top mount changes shape to provide the optical
  cutout. Unexpected common-volume attribute drift: 0.
- SG3B/OptV3 copy placements: 3120 / 2496;
  common: 2496.
- All 2496 common copy placement blocks are byte-identical;
  drift count: 0.
- The 624 SG3B-only copies are all old W multihole
  collimator copies.
- All 69 SG3B-only declared volumes are classified; no
  unknown deletion remains.

Classified SG3B-only declared volumes:

- `near_tes_bi_al_readout_and_cable_proxies`: 10 declared volumes
- `old_four_branch_cold_finger_and_clamps`: 12 declared volumes
- `old_outer_active_and_mechanical_shield`: 9 declared volumes
- `old_outer_plastic_and_bpe`: 6 declared volumes
- `old_w_bottom_and_multihole_collimator`: 5 declared volumes
- `replaced_side_window_shell_and_foil_stack`: 27 declared volumes

## Production blockers

1. **retained_passive_lineage_scorers_missing** — 56 SG3B diagnostic scorers point to geometry still retained in OptV3 but are absent from the OptV3 detector map. Required: restore a matched diagnostic detector map, or explicitly validate a lean-map catalog/lineage contract before production.
2. **readout_and_cable_mass_not_replaced** — SQUID_uMUX_Box_Al_relocated_offbeam_minimal and five SG3B_Al_Bundle_* volumes are absent, with no SH3 replacement volumes. Required: restore, reroute, or explicitly exclude these activation-relevant mass proxies.
3. **bi_and_plastic_design_boundary_unconfirmed** — the SG3B Bi half-cylinder and outer plastic positron-veto geometry are absent from OptV3; the chimney has BGO but no passive Bi or plastic scorer. Required: user must confirm exclusion or authorize chimney-compatible replacements.
4. **new_bgo_response_mapping_not_closed** — OptV3 replaces the SG3B active-shield names/topology with SH3_BGO40_SideShield, SH3_BGO40_FrontOpticalAnnulus, and SH3_BGO40_RearColdPortAnnulus, but no mature common-response mapping receipt yet binds those names to the group-summed veto contract. Required: freeze the three-volume BGO map and validate that the downstream 50 keV common-group veto remains observable despite native detector thresholds before background production.
5. **new_passive_mass_activation_lineage_not_closed** — OptV3 introduces 46 non-vacuum, non-BGO passive material volumes (30 Al, 11 Cu, 4 W, and 1 Be), including chimney thermal shells whose stage ownership is not yet authoritative. Required: assign volume/material/thermal-stage/activation-lineage ownership and ensure the compact catalog can retain those paths before BUILDUP.
6. **source_surface_contract_not_matched** — SG3B uses 'SurroundingSphere 60 5 0 9 60' while OptV3 currently uses 'SurroundingSphere 95 0 0 8 95'. Required: validate the smallest enclosing source surface and regenerate corrected source cards/TT normalization; equal raw histories alone are not equal exposure.
7. **w_frame_full_envelope_clearance_not_closed** — the four-bar W frame has an inner square half-width of exactly 2.70 cm, tangent to the declared r=2.70 cm optical circle and therefore providing zero analytic/alignment margin. Required: before background production, run the frozen 37,194-ray full-envelope signal transport and record a dedicated W-intercept/aperture receipt; enlarge the opening if any optical ray intersects W or the accepted mechanical tolerance requires positive margin.

The detector-map comparison is especially important: SG3B has
125 sensitive definitions and OptV3 has 9.
Of the SG3B definitions, 62 point to
geometry that still exists in OptV3; 56 of those
retained-volume diagnostic scorers are absent from the OptV3 detector map.

## Authority boundary

This audit read only the compact `.geo`, `.det`, manifests, and receipts. It
did not scan SIM payloads and did not run transport. The detailed machine
record is `sg3b_minimal_change_audit.json`.
