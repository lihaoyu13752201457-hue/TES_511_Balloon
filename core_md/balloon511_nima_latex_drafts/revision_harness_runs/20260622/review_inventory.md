# Balloon511 NIM A revision harness Phase 0 review inventory

Source files read first:

- `core_md/balloon511_nima_latex_drafts/balloon511_nima_revision_harness_20260622.md`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_review_en_20260622.md`

Coverage rule: every external-review item in the Phase 0 scope is mapped to at least one authoritative Section 3 ID, or explicitly omitted/rejected with a one-line reason.

Coverage verdict: `COVERAGE_OK = true`

## Major concerns C1-C10

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| C1 Observation geometry, atmosphere, and on-source exposure | W1, B1 | W1 handles wording/exposure scoping now; B1 carries trajectory, slant-column, and duty-cycle work. |
| C2 Hard energy window and realistic 511 keV source profiles | W2, B2 | W2 restricts the headline to unresolved-line sensitivity and states smearing convention; B2 carries broad-line and offset cases. |
| C3 Incomplete physical background budget | W3, B3, B3d | W3 strengthens proxy/scope limitations; B3 carries full-payload/lens-support background; B3d carries diffuse sky fields. |
| C4 EXPACS/PARMA use and source normalization | B4, C1cite, N3, N4 | B4 carries units-complete source weighting and validation; C1cite adds PARMA4.0; N3/N4 fix effective-area and photon-flux units. |
| C5 TES response, timing, and CsI veto assumptions | W6, B5 | W6 adds the idealized-response caveat now; B5 carries the full detector-effects model. |
| C6 Activation statistics and validation | N6, B6, B6d, BCsI | N6 removes false precision now; B6 carries selected-rate convergence; B6d carries isotope/material decomposition; BCsI records the shield trade-study omission. |
| C7 Compton/FoV reconstruction validation | W4, B7, F4 | W4 defines baseline classes now; B7 carries reconstruction validation; F4 removes the toy diagram from the main text. |
| C8 Statistical significance and background uncertainty | W5, B8 | W5 keeps S/sqrt(B) diagnostic-only and adds systematic caveat; B8 carries profile likelihood and nuisance parameters. |
| C9 Geant4/MEGAlib configuration documentation | B9, C1cite | B9 carries the simulation-configuration table; C1cite adds the modern Geant4 reference. |
| C10 Numerical inconsistencies, precision, internal/debug language, layout | N1, N2, N3, N4, N5, N6, N7, D1, D2, D3, D4, F1, F2, F3, F5 | Numerical bugs map to N-items; internal language maps to D-items; PDF/table presentation maps to F-items. |

## C10 numbered bugs and internal-language examples

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| C10.1 20-d background count `1.09e5` inconsistent with rate and Z | N1 | Recompute count from paper rate and keep count/Z/threshold consistent. |
| C10.2 Zero-event 95% upper rate should be `6.38e-5 s^-1` | N2 | Correct interval and propagate derived percentage. |
| C10.3 `S/F0` has area units | N3 | Report as selected effective area. |
| C10.4 Photon flux thresholds need `ph cm^-2 s^-1` | N4 | Fix photon-flux units while leaving particle fluxes as particle fluxes. |
| C10.5 Markdown `\inW_{511}` spacing | N7 | Export artifact; fix exporter, not manuscript source. |
| C10.6 Excessive significant figures | N5, N6 | N5 covers broad precision reduction; N6 covers delayed-rate precision and traceable uncertainty rule. |
| C10 language: `current sampled-position chain` | D2 | Debug/narrative phrasing purge. |
| C10 language: `full-statistics` | D2, D4 | Rephrase and verify by debug grep. |
| C10 language: `seed 260613` | D3, D4 | Move seed/run-level details out of main prose and verify by grep. |
| C10 language: `PASS` | D3, D4 | Move source-card inventory checks out of main prose and verify by grep. |
| C10 language: `source text flux closure` | D2, D3, D4 | Treat as run-level/debug closure wording, not main-text physics language. |
| C10 language: `smoke test` | D2, D4 | Rephrase and verify by grep. |
| C10 language: `side component closed` | D2, D4 | Rephrase debug closure language and verify by grep. |
| C10 language: `manuscript-facing compression` | D2 | Rephrase debug/manuscript workflow wording. |
| C10 language: `archived spatial boundary calculations` | D2, D3 | Move run-level provenance detail out of main prose. |
| C10 language: `headline hard-window result` | D2, W2, W5 | Rephrase and scope the statistical/window claim. |

## Section 5.1 must-fix list

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| 5.1.1 Source-flux convention and event weights | B4, N3, N4 | B4 carries full units/weight derivation and validation; N3/N4 fix immediate unit mistakes. |
| 5.1.2 Prompt atmospheric model | B4, B3d, C1cite | B4 covers EXPACS/PARMA handling; B3d covers diffuse fields; C1cite covers PARMA4.0 citation. |
| 5.1.3 Target-specific mission fold | W1, B1 | W1 scopes current result as net exposure; B1 carries representative trajectory/visibility work. |
| 5.1.4 Geometry and mass closure | W3, B3 | W3 states detector/cryostat proxy limits; B3 carries full-payload/lens-support model. |
| 5.1.5 Full simulation configuration | B9 | Author-held configuration table/backlog item. |
| 5.1.6 Lens response and normalization | Bfig, B4 | Bfig covers A_eff/PSF/encircled-energy redraws; B4 covers source/normalization validation. |
| 5.1.7 TES detector-effects engine | W2, W6, B5 | W2 states smearing convention; W6 caveats idealized response; B5 carries full response engine. |
| 5.1.8 Veto timing and live factor | B5, B8, B9 | Detector/veto model, likelihood treatment, and configuration metadata are backlog work. |
| 5.1.9 Activation history and decay physics | B6, B6d, B9 | Delayed convergence, decomposition/validation, and configuration metadata cover this. |
| 5.1.10 Position-sampling convergence | B6 | Selected-rate convergence over M and seeds. |
| 5.1.11 Reconstruction validation | W4, B7 | W4 defines baseline categories now; B7 carries validation. |
| 5.1.12 Sensitivity likelihood and uncertainty budget | W5, B8 | W5 keeps S/sqrt(B) diagnostic-only; B8 carries likelihood/nuisance work. |

## Section 5.2 formula-level corrections

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| `E_TES^(c) \inW_511` spacing | N7 | Export artifact, not `.tex` correction. |
| Report `S/F0` in cm^2 as selected effective area | N3 | Direct Phase 1 unit fix. |
| Use `P_k` rather than `R_k` for radionuclide production rate | B4 | Folded into units-complete source/activation notation backlog. |
| State time units explicitly in exponentials | B4 | Folded into units-complete source-weight and normalization documentation. |
| State two-hit Compton-equation assumptions | W4, B7 | W4 defines baseline assumptions; B7 carries validation. |
| Define multi-hit residual index range and incoming direction treatment | W4, B7 | W4 handles immediate definition; B7 carries validation. |
| Add weighted MC variance, not just source-card closure | B4, B6 | Source weighting and delayed selected-rate convergence backlog. |
| Correct zero-event Poisson interval | N2 | Direct Phase 1 numerical fix. |

## Section 5.3 should-improve list

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| Show selected prompt/delayed/signal spectra over 450-570 keV with 511 keV inset | Bfig, B6d | Physics redraw/decomposition backlog. |
| Decompose selected prompt background by incident species and physical origin | B3, Bfig | Full-payload prompt-background and physics redraw backlog. |
| Decompose selected delayed background by isotope/material/production particle/decay mode/rate | B6d | Dedicated delayed decomposition backlog. |
| Scan CsI threshold, veto gate, W sleeve, shielding, TES resolution, multiplicity, and window width | B2, B5, B7, BCsI, Bfig | Distributed across line-width, detector-effects, reconstruction, shield trade, and redraw backlog items. |
| Compare CsI with alternative shield materials because iodine activation dominates | BCsI | Explicitly judged OMIT as a separate study, with one sentence noting iodine dominance/future work. |
| Add simple benchmarks for attenuation, bare-array efficiency, crossing rates, and source spectra | B4, B9 | Normalization validation and configuration documentation backlog. |
| Separate optimization samples from final sensitivity samples | B4, B8 | Validation/statistical-method backlog. |

## Section 6 figure and table notes

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| Global PDF layout: tables after references, blank space, long captions, hyperlink boxes | F1, F2, F3, F5 | Float placement, caption/restyle, table relocation/merge items. |
| Figure 1 workflow: keep but redraw, distinguish paths, add outputs | F2, Bfig, B8 | Phase 1 restyle plus backlog physics/likelihood outputs. |
| Tables 1 and 2: remove from main or merge | F3 | Direct Phase 1 table action. |
| Figure 2 mass model: redraw with readable labels, dimensions, materials | F2, Bfig, B3 | Format restyle now; full component/mass closure in backlog. |
| Table 3 detector parameters: keep and expand | W6, B5, B9 | Response caveat now; detector model/config values are backlog/author-held. |
| Figures 3 and 4: merge/replace emphasis, `x_fp`, `y_fp`, A_eff/PSF/off-axis, replace data-constrained | F2, Bfig | Immediate label/restyle action plus physics redraw backlog. |
| Figure 5 EXPACS/PARMA fluxes: redraw, units, 511 inset | F2, B4, Bfig | Restyle now; normalization/physics redraw backlog. |
| Figure 6 production-position distribution: move most to appendix, add units, show selected delayed spectra/decomposition | F2, B6d, Bfig | Restyle plus delayed decomposition/redraw backlog. |
| Figure 7 exact-position sampling claim too strong | D1, B6, Bfig | Rename exact-position now; selected-rate convergence/comparison is backlog. |
| Figure 8 selection and mission diagnostics: split, add MC errors, avoid misleading counts, fix FoV-pass wording | F2, W4, Bfig | Formatting and baseline wording now; cut-flow/mission redraw backlog. |
| Figure 9 Compton/FoV example: remove from main paper | F4, B7 | Remove toy diagram now; validation/replacement is backlog. |
| Table 4: compress and replace prose with source/model/exposure/effective sample/normalization uncertainty | F2, B4, B9 | Format/compression plus normalization/config documentation. |
| Tables 5 and 6: merge into one results table | F5 | Phase 1 SOFTEN table action. |
| Table 7: rename/move to supplement; real convergence table needs M, seed, decays, selected events, uncertainty | D3, F3, B6 | Move run-level checks now; selected-rate convergence backlog. |

## Section 7 references and context gaps

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| Ref 1 Jean 2006 | C1cite, B2 | Cheap citation now; broad/narrow line context also supports B2. |
| Ref 2 Siegert 2019 | C1cite, B2 | Cheap citation now; centroid/line-width context also supports B2. |
| Ref 3 De Cesare 2011 | C1cite | Cheap citation item. |
| Ref 4 Roques 2015 | C1cite | Cheap citation item. |
| Ref 5 Sato 2016 PARMA4.0 | C1cite, B4 | Cheap citation now; EXPACS/PARMA normalization backlog. |
| Ref 6 Gallego 2025 COSI balloon background | C1cite, B3, B9 | Cheap citation now; payload/config validation context. |
| Ref 7 Ciabattoni 2025 COSI anticoincidence | C1cite, B5 | Cheap citation now; scintillator/veto validation context. |
| Ref 8 Beechert 2022 COSI calibration | C1cite, B5, B7 | Cheap citation now; detector/reconstruction validation context. |
| Ref 9 Sleator 2019 COSI simulation benchmarking | C1cite, B7 | Cheap citation now; reconstruction/simulation validation context. |
| Ref 10 Odaka 2018 activation validation | B6, B6d | Activation-history and selected delayed validation backlog. |
| Ref 11 Cumani 2019 environmental inventories | B3, B4, B9 | Environmental inventory/source/configuration backlog context. |
| Ref 12 Cowan 2011 likelihood | C1cite, B8, W5 | Cheap citation now; profile-likelihood backlog and diagnostic caveat. |
| Ref 13 Yoneda 2025 final reference | C1cite | Cheap citation/update item. |
| Ref 14 Gallego 2026 COSI preflight | C1cite, B3, B9 | Cheap COSI-context citation/update plus payload/config validation context. |
| Current refs: Gehrels cannot be sole modern shield/background basis | C1cite, B8 | Add modern statistical/context citations; likelihood backlog replaces sole reliance. |
| Current refs: Gottardi TES review is not enough for 511 keV response | W6, B5 | Response caveat now; full detector-effects model is backlog. |
| Current refs: Zhang arXiv should not be main Ta absorber evidence | W6, B5 | Same detector-response coverage. |
| Current refs: NASA/HEASARC pages should be replaced by peer-reviewed instrument papers | C1cite | Covered by cheap citation update. |
| Current refs: Laue-lens arXiv refs should be supplemented with peer-reviewed prototype publications | C1cite, Bfig | Citation/context update plus lens-response figure backlog. |

## Section 8 prioritized revision checklist

| Review item | Section 3 ID(s) | Coverage note |
|---|---|---|
| P0.1 Correct `1.09e5` count error and zero-event Poisson upper limit | N1, N2 | Direct Phase 1 numerical fixes. |
| P0.2 Define source-flux reference plane and rewrite normalization derivation with units | B4, N3, N4 | Unit fixes now; full derivation backlog. |
| P0.3 Replace synthetic mission claim with trajectory/visibility/slant-atmosphere fold | W1, B1 | Scope wording now; trajectory fold backlog. |
| P0.4 Restrict headline to unresolved-line sensitivity and calculate line-width cases | W2, B2 | Restrict now; cases backlog. |
| P0.5 Include full-payload and optics-support prompt background, or reframe as subassembly | W3, B3 | Scope limitation now; full-payload model backlog. |
| P0.6 Provide Geant4/MEGAlib versions, physics list, decay settings, cuts, custom-code docs | B9, C1cite | Config table backlog plus Geant4 citation. |
| P0.7 Increase delayed-decay statistics and selected-rate convergence across M/seeds | B6, N6 | Precision fixed now; convergence backlog. |
| P0.8 Replace ideal TES/CsI response or quantify response envelope | W6, B5 | Caveat now; full response model backlog. |
| P0.9 Define and validate multi-hit reconstruction baseline | W4, B7 | Define now; validation backlog. |
| P0.10 Replace S/sqrt(B) headline with likelihood and nuisance parameters | W5, B8 | Diagnostic caveat now; likelihood backlog. |
| P1.11 Add A_eff(E), PSF, encircled energy, off-axis response, lens tolerances | Bfig | Physics redraw backlog. |
| P1.12 Present selected prompt/delayed spectra and physical/isotopic decompositions | Bfig, B6d | Redraw and delayed decomposition backlog. |
| P1.13 Add threshold, veto-window, shielding, energy-resolution, and line-window scans | B2, B5, B7, BCsI, Bfig | Covered across line, detector, reconstruction, shield, and redraw backlog. |
| P1.14 Compare CsI with at least one alternative shield material | BCsI | Explicitly judged OMIT as separate study, with future-work note. |
| P1.15 Validate source normalization, attenuation, detector efficiency, and radioactive spectra | B4, B6, B9 | Normalization/config/delayed validation backlog. |
| P1.16 Define in-flight background estimation strategy | W5, B8 | Qualitative strategy now; likelihood/nuisance backlog. |
| P1.17 Supply statistical and engineering uncertainty budget | B8, B9, W6 | Likelihood/config backlog plus response caveat. |
| P2.18 Replace internal/debug terminology throughout | D1, D2, D3, D4 | Direct Phase 1 debug-language purge. |
| P2.19 Merge/remove Tables 1, 2, 5, 6, 7 and move run-level validation | F3, F5, D3 | Direct Phase 1 table/run-level actions. |
| P2.20 Redraw Figures 2-9 with readable labels, physical quantities, uncertainty bars | F2, F4, Bfig | Phase 1 restyle/removal plus redraw backlog. |
| P2.21 Fix float placement before references | F1 | Direct Phase 1 float-placement item. |
| P2.22 Reduce numerical precision | N5, N6 | Direct Phase 1 precision items. |
| P2.23 Update bibliography | C1cite | Direct Phase 1 citation item. |
| P2.24 Consider revising title | W7 | Phase 1 SOFTEN title item under default scope decision. |
