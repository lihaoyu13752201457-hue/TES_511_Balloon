# Stepwise Maintenance Reference Papers Index (2026-06-02)

This file records the paper and technical-reference anchors currently mentioned
by `stepwise_maintenance/` documents, with direct top-level Route-A/Route-B
documents included where they define the same step-maintenance claims.

Scope rule: this is an index of cited or locally mentioned references, not a
final BibTeX file. Rows marked `needs bib completion` should be verified before
they are used in a manuscript bibliography.

## Confirmed Paper References

| status | suggested key | reference | local role | local mentions |
| --- | --- | --- | --- | --- |
| keep | `Shirazi2023_511CAM` | Shirazi et al., "The 511-CAM Mission: A Pointed 511 keV Gamma-Ray Telescope with a Focal Plane Detector Made of Stacked Transition Edge Sensor Microcalorimeter Arrays", JATIS 9, 024006 (2023), arXiv:2206.14652, DOI:10.1117/1.JATIS.9.2.024006. | 511-keV line-focused science, TES stack, 390 eV-class line resolution, Laue/channel optics scale. | `step04_opticsim/SOURCE_MODEL_EXPLAINER.html`; `step04_opticsim/optics_design_rationale.md`; `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`; `README.md`/mass-model context. |
| keep | `Siegert2016_MW511` | Siegert et al., "Gamma-ray spectroscopy of positron annihilation in the Milky Way", A&A 586, A84 (2016), arXiv:1512.00325, DOI:10.1051/0004-6361/201527510. | Step07/Route-B Galactic 511-keV bulge, disk, total, and central-component flux anchors; positronium/line-spectrum context. | `step07_source_cases/code/build_step07_source_cases.py`; `step04_opticsim/SOURCE_MODEL_EXPLAINER.html`; `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`; `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`. |
| keep | `Siegert2016_V404` | Siegert et al., "Positron annihilation signatures associated with the outburst of the microquasar V404 Cygni", Nature 531, 341-343 (2016), arXiv:1603.01169, DOI:10.1038/nature16978. | V404 Cyg transient positron-annihilation benchmark/source-case grid. | `step07_source_cases/code/build_step07_source_cases.py`; `step04_opticsim/SOURCE_MODEL_EXPLAINER.html`. |
| keep | `Knodlseder2003_SPIBulge` | Knodlseder et al., "Early SPI/INTEGRAL constraints on the Galactic 511 keV annihilation emission", A&A 411, L457-L460 (2003), arXiv:astro-ph/0309442, DOI:10.1051/0004-6361:20031437. | Extended Galactic bulge morphology context; used by Route B as the physical background for an 8-9 deg bulge-scale model. | `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`; related to Step07 diffuse aperture foreground. |
| keep, local wording check | `CLAIRE_FirstLight` | "CLAIRE's first light" Laue-lens balloon precedent, ScienceDirect PII:S1387647303003129, DOI:10.1016/j.newar.2003.11.032. | Balloon Laue-lens scale: 2.77 m focal length, 170 keV narrow-band precedent, 556 Ge-Si crystals on 8 rings. | `step04_opticsim/SOURCE_MODEL_EXPLAINER.html`; `step04_opticsim/optics_design_rationale.md`; `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`; `LAUE_LENS_DESIGN_SPEC_20260601.md`. Local top-level note says "ExA 2005"; source link points to New Astronomy Reviews, so final bibliography should reconcile this. |
| keep | `Barriere2009_LaueCrystals` | Barriere et al., "Experimental and theoretical study of diffraction properties of various crystals for the realization of a soft gamma-ray Laue lens", J. Appl. Cryst. 42, 834-845 (2009), DOI:10.1107/S0021889809023218, arXiv:0907.0458. | External experimental anchor for Laue diffraction efficiency/reflectivity, used to validate B-FULL physics wording. | `step04_opticsim/laue_review_20260601.html`; `LAUE_LENS_DESIGN_SPEC_20260601.md`; `OPTICS_BFULL_BACKEND_INTEGRATION_20260601.md`. |
| keep | `Kohnle1998_DiffractionEfficiencies` | Kohnle et al., "Measurement of diffraction efficiencies relevant to crystal lens telescopes", Nucl. Instrum. Meth. A 416, 493-504 (1998), DOI:10.1016/S0168-9002(98)00628-7. | External Ge(111)/APS endpoint diffraction-efficiency anchor for the Darwin/Laue validation chain. | `step04_opticsim/laue_review_20260601.html`; `LAUE_LENS_DESIGN_SPEC_20260601.md`; `OPTICS_BFULL_BACKEND_INTEGRATION_20260601.md`. |
| keep | `Reiazi2025_G4BraggReflection` | Reiazi et al., "G4BraggReflection: A Geant4 physical process for reflection in crystals", J. Phys. D: Applied Physics 58, 295102 (2025), DOI:10.1088/1361-6463/aded1d. | Prior Geant4 crystal-reflection process; cited to avoid claiming a first/original Geant4 toolkit patch. | `step04_opticsim/laue_review_20260601.html`; `LAUE_LENS_DESIGN_SPEC_20260601.md`; `EXECUTE_ROUTE_A_FULLCHAIN_AND_REPORT_20260601.md`. |
| keep | `Guan2023_Geant4Bragg` | Guan et al., "Adding X-ray Bragg reflection physical process in crystal to the Geant4 Monte Carlo simulation toolkit. Part I: reflection from a crystal slab", Precision Radiation Oncology 7, 59-66 (2023), DOI:10.1002/pro6.1188. | Prior Geant4 crystal-diffraction / Bragg-reflection work; cited to position B-FULL as an application-level Laue-transmission implementation, not a toolkit novelty claim. | `step04_opticsim/laue_review_20260601.html`; `step04_opticsim/LAUE_COMPUTATION_PRINCIPLE_AND_CODE.md`; `LAUE_LENS_DESIGN_SPEC_20260601.md`. |
| keep | `Kondev2021_NUBASE2020` | Kondev, Wang, Huang, Naimi, Audi, "The NUBASE2020 evaluation of nuclear physics properties", Chinese Physics C 45, 030001 (2021), DOI:10.1088/1674-1137/abddae. | Ground-state half-life correction and unit audit anchor for delayed-source cleanup. | `step02_raw_background_simulation/README.md`; `step03_delay_source/README.md`; `CURRENT_PROGRESS_STEP_BREAKDOWN.md`; `inputs/nubase/README.md`. |
| keep, if MEGAlib is discussed in paper | `Zoglauer2006_MEGAlib` | Zoglauer, Andritschke, Schopper, "MEGAlib: The Medium Energy Gamma-ray Astronomy Library", New Astronomy Reviews 50, 629-632 (2006), DOI:10.1016/j.newar.2006.06.049. | MEGAlib/Cosima simulation environment and EventList/trigger ecosystem. | Explicit DOI appears in `基于立方星的康普顿望远镜在轨性能模拟.md`; Stepwise files reference MEGAlib in `step02`, `step04`, `step05`, and `step09`. |

## Technical And Database References

| status | suggested key | reference | local role | local mentions |
| --- | --- | --- | --- | --- |
| keep | `NIST_XCOM` | NIST XCOM Photon Cross Sections Database, https://www.nist.gov/pml/xcom-photon-cross-sections-database. | Photon attenuation at 511 keV, especially Ge/Be linear attenuation checks. | `step04_opticsim/SOURCE_MODEL_EXPLAINER.html`; `step04_opticsim/laue_review_20260601.html`; `LAUE_LENS_DESIGN_SPEC_20260601.md`. |
| keep, choose exact citation before manuscript | `Geant4_Toolkit` | Geant4 toolkit documentation and canonical Geant4 papers. | Standard EM transport and B-FULL `G4VDiscreteProcess` competition wording. | `step04_opticsim/README.md`; `step04_opticsim/LAUE_COMPUTATION_PRINCIPLE_AND_CODE.md`; `step09_optics_bridge/README.md`. |
| keep, needs exact tool citation | `XOP_CRYSTAL_DABAX` | XOP/CRYSTAL `diff_pat`, xoppylib, and DABAX documentation/papers. | Independent rocking-curve map for Ge(111) at 511 keV; per-ring external curve used by B-FULL. | `step04_opticsim/README.md`; `step04_opticsim/real_design_crosscheck_20260601.md`; `LAUE_LENS_DESIGN_SPEC_20260601.md`. |
| keep, optional | `PyTTE_CrystalPy` | PyTTE and CrystalPy documentation/papers. | Optional Takagi-Taupin/perfect-crystal qualitative cross-checks in the Laue validation roadmap. | `LAUE_LENS_DESIGN_SPEC_20260601.md`. |
| keep, optional | `HEART_McXtrace` | HEART/McXtrace native optics packages. | Proposed independent PSF check for mosaic-Laue lens focusing. | `step04_opticsim/laue_review_20260601.html`; `LAUE_LENS_DESIGN_SPEC_20260601.md`. |

## Mentions Needing Bibliographic Completion

| item | why it is here | next action |
| --- | --- | --- |
| `Virgilli2016` | Mentioned in `step04_opticsim/laue_review_20260601.html` as part of prior online checks, but the local stepwise docs do not pin the exact title/DOI. | Search and select the exact Laue-lens paper only if it will be cited in the final optics section. |
| `MAX/GRI/LAUE studies` | Mentioned as public anchors for mosaicity/focal-length scale in `step04_opticsim/optics_design_rationale.md`, without exact titles. | Convert to exact citations if the manuscript needs broader Laue-lens design precedent beyond CLAIRE/511-CAM. |
| `SPI/INTEGRAL GC review` | Mentioned in `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md` as context for positronium fraction and Galactic-center annihilation spectrum. | If a review citation is needed, choose one review paper and separate it from the Siegert 2016 flux anchor. |

## Paper-Facing Checklist

- [x] Route-A science/mission scale has a primary 511-CAM citation.
- [x] Route-B diffuse bulge/disk input has a primary SPI/Siegert citation and an extended-bulge morphology citation.
- [x] V404 Cyg transient source case has a Nature/Siegert citation.
- [x] B-FULL Laue validation has experimental anchors: Barriere 2009 and Kohnle 1998.
- [x] B-FULL novelty wording has prior Geant4 crystal-reflection citations: Reiazi 2025 and Guan 2023.
- [x] 511-keV attenuation uses NIST XCOM as a database citation, not an invented constant.
- [x] Delayed-source half-life correction uses the archived NUBASE2020 table plus the NUBASE2020 paper.
- [ ] Before final manuscript BibTeX, resolve CLAIRE publication metadata versus the local "ExA 2005" wording.
- [ ] Before final manuscript BibTeX, decide whether to cite Geant4 canonical papers, MEGAlib, XOP/CRYSTAL/DABAX, PyTTE/CrystalPy, and HEART/McXtrace in the methods section.
- [ ] Before final manuscript BibTeX, either complete or drop the loose `Virgilli2016`, `MAX/GRI/LAUE studies`, and `SPI/INTEGRAL GC review` mentions.

## Local Search Commands Used

```bash
rg --files stepwise_maintenance | rg '\\.md$'
rg -n "arXiv|doi|DOI|A&A|Nature|Siegert|Knodlseder|CLAIRE|511-CAM|XOP|CRYSTAL|Geant4|MEGAlib|NIST|NUBASE|Barrière|Kohnle|Reiazi|Guan" stepwise_maintenance code *.md inputs/nubase/README.md
```
