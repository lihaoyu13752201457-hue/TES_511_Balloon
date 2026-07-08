# Remaining backlog after Phase 1

Scope decision recorded for this run: **(b) Reframe to reference-exposure statistical sensitivity for an unresolved line**.

This means the current manuscript may report a detector-coupled selected-rate estimate for the reference mass model, but it must not claim final flight sensitivity, full-payload background closure, broad-line performance, or publication-level likelihood treatment. The items below are the remaining non-Phase-1 work from harness Section 3E.

Companion engineering queue: `project_internal_fix_queue.md` lists the project-side fixes that cannot be closed by manuscript wording alone.

## Ranked backlog

| ID | Review concern | Priority | Judgment | Status | Next action |
|---|---|---:|---|---|---|
| B6 | C6 delayed activation statistics | P0 | HONOR | BACKLOG | Run higher delayed-decay statistics, multiple production-position samplings, and weighted variance/convergence checks at the selected-rate level. |
| B3 | C3 physical background budget | P0/P1 | HONOR | BACKLOG | Add full-payload, lens-support, gondola/bench, and prompt optics self-background model or keep those explicitly scoped out. |
| B8 | C8 significance/statistics | P1 | HONOR | BACKLOG | Replace diagnostic `S/sqrt(B)` with spatial-spectral likelihood including prompt/delayed nuisance parameters and systematics. |
| B1 | C1 observation geometry | P1 | SOFTEN | BACKLOG | Add representative trajectory, visibility/duty-cycle, and slant-column atmospheric transmission rather than a full mission-operations budget. |
| B4 | C4 source normalization | P1 | SOFTEN | BACKLOG | Write units-complete source-weight derivation, source-plane projected-area treatment, and compact validation/benchmark notes. |
| B9 | C9 simulation configuration | P1 | HONOR | BACKLOG | Add an author-filled configuration table: Geant4/MEGAlib versions, physics list, cuts, decay data, seed policy, and custom hooks. |
| B6d | C6 delayed decomposition | P1 | HONOR | BACKLOG | Decompose selected delayed background by isotope, material, production particle, decay mode, and selected rate. |
| B2 | C2 line width/source profile | P1/OPT | SOFTEN | BACKLOG | Add at least representative broad-line and centroid-offset cases; full 1.3/2.43/5.4 keV grid is optional under scope (b). |
| B5 | C5 detector-effects engine | OPT | OMIT | SCOPED FUTURE WORK | Keep the Gaussian response envelope caveat; a full detector-effects model is a separate TES characterization project. |
| B7 | C7 reconstruction validation | OPT | SOFTEN | BACKLOG | Cross-check the retained multi-hit subset with Revan/Mimrec or an equivalent reconstruction validation when moving beyond the selected-rate estimate. |
| B3d | C3 diffuse celestial fields | OPT | OMIT | SCOPED OUT | Keep diffuse sky/foregrounds out of the instrumental-background estimate and mention as a later astrophysical foreground layer. |
| BCsI | C6 shield-material trade | OPT | OMIT | SCOPED FUTURE WORK | Note iodine activation as a motivation for future shield-material trade studies; do not add a CsI alternative-material study to this paper phase. |
| Bfig | Section 6 figure redesign | P1/P2 | SOFTEN | BACKLOG | Redraw physics figures with vector labels, `A_eff(E)`, PSF/encircled-energy, selected spectra, cut-flow split, and MC error bars. |

## Response-to-reviewer draft language

**B6 delayed statistics.** We agree that the delayed selected-rate precision is not yet sufficient for a final activation claim. The revised manuscript now reports the delayed component with an explicitly statistical scale from the selected delayed event count and states that source-sampling and model systematics are not included. Higher-statistics delayed replays, multiple production-position samplings, and selected-rate convergence tests remain required before a flight-performance claim.

**B3 full payload and lens supports.** The revised manuscript no longer presents the result as a full-payload background closure. It identifies the detector/cryostat model as an engineering proxy and explicitly excludes full gondola, optical bench, lens support, electronics, pressure vessels, diffuse sky fields, and prompt optics self-background from the primary budget. A full-payload and lens-support model is therefore a required follow-up for flight-background claims.

**B8 likelihood and systematics.** We agree that the counting metric is not a publication-level discovery likelihood. The revised text now labels `S/sqrt(B)` as a diagnostic selected-rate metric and states that a spatial-spectral likelihood with nuisance parameters is needed for final sensitivity. The likelihood implementation and systematic uncertainty budget remain future work.

**B1 trajectory and exposure.** The result is now framed as a reference-exposure estimate under a synthetic 20 d rate fold and continuous on-source exposure. A representative trajectory, target visibility, duty cycle, and slant-column transmission should be added before interpreting the threshold as a mission-performance forecast.

**B4 source normalization.** The Phase 1 revision corrects photon-flux units and the selected-effective-area statement. A full source-normalization derivation with projected-area conventions, EXPACS/PARMA I/O archival notes, and analytic benchmarks should be added in the next methods pass.

**B9 simulation configuration.** The manuscript needs a reproducibility table for Geant4/MEGAlib versions, physics lists, cuts, decay data, seed policy, and custom hooks. This should be author-filled from the actual run environment; no values should be invented from memory.

**B6d delayed decomposition.** The revised paper notes that delayed activation is spatially and materially structured. A stronger version should include selected delayed decomposition by isotope, material, production particle, and decay mode, with dominant channels validated against the source inventory and transport output.

**B2 broad-line cases.** The main result is now explicitly limited to an unresolved line. Representative broad-line and centroid-offset cases would be useful for astrophysical interpretation, but the full line-width grid can be treated as optional unless the claim is expanded beyond unresolved-line sensitivity.

**B5 detector-effects model.** The revised manuscript states that the detector response is an idealized single Gaussian event-energy proxy and omits gain drift, non-Gaussian tails, pile-up, saturation, and response scans. A full detector-effects engine is important for a detector-characterization paper, but it is beyond the present selected-rate estimate.

**B7 reconstruction validation.** The revised manuscript defines the baseline classes and stops treating unreconstructed retained events as field-of-view-passing events. Revan/Mimrec or equivalent reconstruction validation remains a necessary next step before using the multi-hit selection as a finalized reconstruction method.

**B3d diffuse fields.** Diffuse Galactic and extragalactic components are outside the present instrumental-background estimate. They should be added only when the paper moves from detector-background performance to astrophysical observation forecasting.

**BCsI shield trade.** The revised discussion flags iodine activation in CsI as motivation for future shield-material trade studies. A comparative shield-material optimization is not attempted in this manuscript phase.

**Bfig figure redesign.** Phase 1 fixed float placement and removed the main-text toy Compton/FoV figure, but a NIM A submission will benefit from redrawn physics figures with cleaner labels, uncertainty bars, spectra, optics response, and cut-flow separation.
