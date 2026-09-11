# S3 / MASS_511 Background Trajectory Handoff Packet

## Technical Summary

- **Main result:** S3 W2 has `83` final residual events in this audit, total `0.0222344226177 cps`; truth-line crossing of the Step05 side-window disk is `0` events, `0.000%` of rate.
- **Dominant residuals:** ATM511 sidecar `0.0108831480283 cps` (48.9%), prompt e+ `0.00814208480796 cps` (36.6%), prompt n `0.00203584167124 cps` (9.2%), delayed activation `0.00117334811025 cps` (5.3%).
- **S3 vs MASS_511 with matched 4pi ATM511:** S3 W2 20d 3sigma minimum flux is `2.85291e-05 ph cm^-2 s^-1`; MASS_511 is `5.24425e-05`; MASS/S3 ratio `1.838`.
- **Interpretation:** The remaining S3 background is not an optical-path leakage problem under the current Step05 side-window disk definition. It is mainly neutral 511 keV wall/non-window leakage plus internal passive/activation production.

## File Map

1. `README_GPT_PRO.md` - this technical handoff.
2. `PROMPT_FOR_GPT_PRO.md` - ready-to-use prompt for GPT Pro.
3. `s3_background_trajectory_truth_table.csv` - 83 W2 residual rows. Prompt e+/n rows are event-audited; ATM511 rows are retained-summary event IDs; delayed rows use retained source-volume summary rows to keep the packet small.
4. `s3_background_trajectory_summary.json` - aggregate route/component rates and disk definition.
5. `s3_vs_mass511_matched_atm511_performance.json` - compact matched-performance numbers.
6. `geometry_key_differences_s3_vs_mass511.md` - reader-facing geometry diff guide.
7. `model_s3_csi_barrel_flat_geometry.txt` - flattened S3 geometry text.
8. `model_mass511_flat_geometry.txt` - flattened MASS_511 geometry text.
9. `artifact_manifest.json` - provenance, hashes, and source paths.
10. `reproduce_packet.py` - script that regenerates all files above.

## Definitions

- W2 energy window: `510.58`--`511.42` keV.
- Active veto threshold in this packet: `50.0` keV.
- Active veto volumes for S3 replay: `CsI_*`, legacy `BGO/ACTIVE_SHIELD/CEBR3`, and `GeoOpt_S2B_CryoShell_Plastic*`.
- Side-window truth crossing: a straight segment from source/annihilation/decay point to each TES hit intersects the Step05 side-entry disk.

## Residual Routes

- `internal_activation`: `0.00107556910106 cps`, `4.8%`, `11` events.
- `internal_passive_neutron_secondary`: `0.00203584167124 cps`, `9.2%`, `3` events.
- `internal_window_material_activation`: `9.77790091875e-05 cps`, `0.4%`, `1` events.
- `nonwindow_prompt_eplus_annihilation_511`: `0.00814208480796 cps`, `36.6%`, `12` events.
- `wall_or_nonwindow_atm511_line`: `0.0108831480283 cps`, `48.9%`, `56` events.

## Why Current Vetoes Miss These Events

- Plastic scintillator skin: it tags charged deposits. Most surviving e+ and all ATM511 final photons are neutral-511 paths with zero or sub-threshold active deposit.
- BPE: it is passive moderation/shielding, not an active veto. It can reduce neutron flux but cannot tag a neutral 511 photon after an internal/passive interaction.
- Passive W/shielding: it attenuates but also creates/hosts secondary and activation channels. It cannot veto.
- CsI barrel veto: S3 improves coverage, but the residual W2 events have no above-threshold CsI/plastic active deposit.
- Compton/FoV veto: single-pixel 511 events pass by construction; multi-pixel events only fail if their topology is inconsistent with the side-window cone.

## Main Open Questions For GPT Pro

- Is the side-window disk truth definition too narrow for a real optical-path/side-window aperture?
- Which exact non-window paths in the flattened S3 geometry allow atmospheric/prompt annihilation 511 photons to reach TES without CsI deposit?
- Can the Cu64/Cu62 delayed component be reduced by changing copper near `ColdPlate_CP_100mK_intercept`, `ColdPlate_MXC_50mK_SD_anchor`, `Cu_50mK_StillLike_Can_bottom_cap_2mm`, or the window assembly?
- Would a local active collar, lower-threshold segmented skin, or extra non-window gamma catcher reduce the top two components without killing signal?

## Provenance Caveats

- This is a compact handoff packet, not a promotion artifact.
- The default packet builder does not stream the 850 MB ATM511 SIM or 760 MB delayed SIM. It uses retained summaries for those rows and preserves source paths for optional targeted re-audit.
- Delayed normalization is inherited from the retained S3 Step05 chain with NUBASE ground-state correction and exact-position M=50000 source provenance.
- No SIM.GZ files are copied into this packet; retained SIM paths are listed for targeted follow-up audits.
