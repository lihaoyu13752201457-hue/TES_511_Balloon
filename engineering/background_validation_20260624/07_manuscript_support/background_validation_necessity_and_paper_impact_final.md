# Background Validation Necessity and Paper Impact - Final

Status: `PASS_LIMITED_SUPPORT_WITH_MATCHED_RUNS_BLOCKED`.

## 1. Current Paper Claim Boundary

The current engineering pass supports the fix5 normalization, eplus provenance, delayed convergence screen, and a material-only BGO same-envelope geometry. It does not support a CsI-vs-BGO performance conclusion because matched production runs are blocked by the resource guard.

Allowed claims:
- fix5 prompt source normalization and selected-rate reconstruction are audited against existing Step05 authority
- final W2 prompt eplus survivors are traced to annihilation-photon lineage in existing SIM records
- delayed selected-rate PI-02 pooled uncertainty meets the 10% minimum convergence screen
- a material-only BGO same-envelope geometry is available and overlap-checked

Disallowed claims:
- BGO improves or worsens CsI background
- matched CsI/BGO prompt, delayed, or signal rates are known
- material difference is statistically resolved

## 2. Veto Authority

The fixed Step05 active-veto authority for this harness is `shield_total_keV < 50 keV` with a `1 us` coincidence window. No 40/60/90 keV CsI threshold tests were run or used. BGO derivation preserves detector and volume names plus selection plumbing; material comparison remains blocked until matched runs use the same Step05 selection code.

## 3. Prompt Normalization Audit

Prompt normalization status is `PASS`. The reconstructed final W2 prompt rate is `0.0366410230297` cps with `sum_w2=2.48623072039e-05`. The G1 audit verifies 60 cm source radius consistency, `pi R^2` area handling, source-card flux closure, unique seeds, split/replica completeness, and independent selected-rate reconstruction against Step05.

## 4. eplus Survivor Physical Source

The final W2 prompt `eplus` contribution is `0.0318897456148` cps. Existing SIM `IA`, `CC HIT`, and `HTsim` records classify `1.000` of selected eplus survivors into A-C. In this run all 47 survivors classify as class A, aperture-coupled annihilation-photon lineage.

| class | process summary | events | rate cps |
|---|---|---:|---:|
| A | gamma/phot/annihil/e+ | 25 | 0.0169626306462 |
| A | gamma/compt/annihil/e+ | 20 | 0.0135701045169 |
| A | e-/eIoni/compt/gamma | 2 | 0.00135701045169 |

## 5. Delayed Convergence and Leading Isotope/Volume

Delayed convergence status is `DELAYED_CONVERGED`. Four independent exact-position production-position samplings give 103 pooled selected W2 events, selected rate `0.00221278212897` cps, sigma `0.000218031901787` cps, and relative uncertainty `0.0985329`.

| isotope | events | rate cps | fraction |
|---|---:|---:|---:|
| Cu-64 | 85 | 0.00730424978748 | 0.825 |
| Cu-62 | 16 | 0.00137467483353 | 0.155 |
| Na-24 | 1 | 8.59901732941e-05 | 0.010 |
| W-187 | 1 | 8.59901732941e-05 | 0.010 |

Top isotope/volume/production-family decomposition:

| isotope | source volume | family | events | rate cps |
|---|---|---|---:|---:|
| Cu-64 | ColdPlate_MXC_50mK_SD_anchor | n | 38 | 0.00326554486044 |
| Cu-64 | Cu_SubstrateSupport_SolidDisk_L0_deepest | n | 13 | 0.00111670431365 |
| Cu-64 | Cu_50mK_StillLike_Can_bottom_cap_2mm | n | 11 | 0.000945531210039 |
| Cu-62 | ColdPlate_MXC_50mK_SD_anchor | n | 11 | 0.000945174138045 |
| Cu-64 | ColdPlate_CP_100mK_intercept | n | 6 | 0.00051586377067 |
| Cu-64 | Window | n | 6 | 0.000515486387583 |
| Cu-64 | Cu_50mK_StillLike_Can_side_wall_above_side_port | n | 4 | 0.000343565415131 |
| Cu-64 | ColdPlate_Still_0p7K | n | 3 | 0.000257820462886 |

## 6. CsI-BGO Comparison Status

The BGO same-envelope geometry status is `PASS_BGO_SAME_ENVELOPE_GEOMETRY`. It changes `24` active-shield material lines from CsI to BGO while preserving geometry shape, position, mother, detector references, source radius, and selection plumbing. The BGO material authority is MEGAlib `BGO`, density `7.1` g/cm3, composition `Bi 4, Ge 3, O 12`.

Geometry diff status: `PASS` with `0` non-whitelisted diffs. Overlap status: `PASS`.

Matched CsI/BGO transport status is `BLOCKED_RESOURCE_APPROVAL`. Therefore no prompt, delayed, signal, total-background, ratio, uncertainty-on-difference, or material-preference comparison is available yet.

## 7. Methods/Results/Discussion Help

Methods can cite the validated source normalization, fixed 50 keV/1 us veto authority, delayed convergence treatment, and material-only BGO derivation procedure. Results can cite fix5 prompt/delayed validation numbers and the blocked status of material comparison. Discussion should describe BGO as an engineering validation path prepared for future matched production, not as an evaluated design improvement.

## 8. Candidate English Insertion

The background model was subjected to a separate engineering validation pass. The prompt source normalization was re-audited from the far-field source cards through the selected-event rate reconstruction, and the dominant prompt positron survivors in the 511 keV window were traced in the existing simulation records to annihilation-photon lineages. For delayed activation, four independent exact-position production-position samplings gave 103 pooled selected W2 events with a relative Monte Carlo uncertainty of about 9.9%. A material-only BGO same-envelope geometry was also derived and passed static geometry and overlap checks, but matched CsI/BGO production runs were not executed in this pass because they exceed the predefined resource guard.

## 9. Claims Not Supported

- Do not claim a BGO/CsI background ratio or material preference.
- Do not change headline sensitivity numbers from this document alone.
- Do not cite targeted trace or matched-run results, because none were run here.
- Do not describe non-significant or unrun material comparisons as design conclusions.

## 10. Provenance Table

| item | path |
|---|---|
| g1 | `01_prompt_source_audit/prompt_normalization_audit.json` |
| g2 | `02_prompt_eplus_provenance/eplus_survivor_provenance.json` |
| g2_process | `02_prompt_eplus_provenance/eplus_survivor_process_summary.csv` |
| g3 | `03_delayed_convergence/delayed_selected_rate_convergence.json` |
| g3_isotopes | `03_delayed_convergence/delayed_selected_isotope_summary.csv` |
| g3_decomposition | `03_delayed_convergence/delayed_selected_decomposition.csv` |
| g4 | `04_bgo_variant/bgo_geometry_manifest.json` |
| g5 | `05_matched_runs_resource_guard/summary.json` |

## Resource-Blocked Follow-Up

Affected claim: No CsI/BGO material-comparison rate, ratio, uncertainty, or design preference can be claimed until matched CsI/BGO transport and identical Step05 selection are run.

Minimal next action: Approve and run the staged P0 syntax/geometry smoke batch, then review P0 before any P1/P2 escalation.
