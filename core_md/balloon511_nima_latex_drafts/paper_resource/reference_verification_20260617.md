# Reference Verification Pass

Date: 2026-06-17.

Scope: current English and Chinese LaTeX drafts in
`core_md/balloon511_nima_latex_drafts/`. This pass focused on citation
existence, publication metadata, and whether manuscript claims rely on the
right class of source.

## Actions Applied

- Added verified DOIs for the main 511 keV review/SPI/COSI imaging, V404 Cygni,
  TES review, SPI response, Geant4, and MEGAlib references.
- Added the formal ApJ DOI for the COSI 511 keV detection paper
  (`Kierans2020`) after a Crossref title query.
- Corrected the 511-CAM journal-version author order to match the JATIS/Crossref
  record: Shirazi, Gau, Hossen, Becker, Schmidt, ...
- Updated NASA Science and HEASARC COSI access dates to 17 June 2026 after
  reopening both pages.
- Resolved the remaining weak bibliography entries for XOP, Gehrels, and AMEGO
  using publisher/Crossref/PoS/INSPIRE metadata. An earlier guessed XOP DOI was
  not used; the verified SPIE DOI `10.1117/12.893911` was added instead.

## Verified Strong Anchors

| Key | Status | Evidence used | Manuscript action |
|---|---|---|---|
| `Prantzos2011` | verified journal record | Crossref DOI `10.1103/RevModPhys.83.1001`; arXiv title match | DOI added |
| `Siegert2016AA` | verified journal record | Crossref DOI `10.1051/0004-6361/201527510`; arXiv title match | DOI added |
| `Kierans2020` | verified journal record | Crossref DOI `10.3847/1538-4357/ab89a9`; arXiv `1912.00110` confirms 46 d COSI flight, 7.2 sigma detection, broader-than-point-source result | DOI added |
| `Siegert2020COSI` | verified journal record | Crossref DOI `10.3847/1538-4357/ab9607`; arXiv title match | DOI added |
| `Siegert2016V404` | verified journal record | Crossref DOI `10.1038/nature16978`; arXiv title match | DOI added |
| `Shirazi2023` | verified journal record | Crossref/JATIS DOI `10.1117/1.JATIS.9.2.024006` | author order corrected |
| `Sato2015EXPACS` | verified journal record | Crossref DOI `10.1371/journal.pone.0144679` | already had DOI |
| `Kondev2021NUBASE` | verified journal record | Crossref DOI `10.1088/1674-1137/abddae` | already had DOI |
| `Sturner2003` | verified journal record | Crossref DOI `10.1051/0004-6361:20031171` | DOI added |
| `Agostinelli2003` | verified journal record | Crossref DOI `10.1016/S0168-9002(03)01368-8` | DOI added |
| `Zoglauer2006` | verified journal record | Crossref DOI `10.1016/j.newar.2006.06.049` | DOI added |
| `Gottardi2021TESReview` | verified journal record | Crossref DOI `10.3390/app11093793`; title also found in arXiv metadata | DOI added |
| `SanchezDelRio2011XOP` | verified proceedings record | Crossref/SPIE DOI `10.1117/12.893911` | DOI added; no guessed DOI retained |
| `Gehrels1985` | verified journal record | Crossref DOI `10.1016/0168-9002(85)90732-6` | upgraded from NASA TM note to final NIM A citation |
| `Caputo2017` | verified PoS proceedings record | PoS/Crossref/INSPIRE DOI `10.22323/1.301.0783` | DOI added; container and year normalized |
| `NASACOSI` | verified official page | NASA Science COSI page, reopened 2026-06-17 | access date updated |
| `HEASARCCOSI` | verified official page | HEASARC COSI page, reopened 2026-06-17 | access date updated |
| `Ciabattoni2025ACS` | verified accepted journal record | arXiv `2507.21275` and DOI `10.1007/s10686-025-10019-7`; abstract states that quantitative COSI ACS modeling uses optical-physics simulations and laboratory benchmarks for BGO light collection and response | added as BGO active-shield response boundary citation |

## Verified by Title/Preprint Metadata

These entries exist and support their local citation role, but no journal DOI
was added in this pass:

| Key | Evidence used | Note |
|---|---|---|
| `Yoneda2025` | arXiv `2509.01066` title/authors | recent SPI imaging preprint; keep explicitly as arXiv |
| `Barriere2009Laue` | arXiv `0910.0488` title/authors | Laue-lens design background |
| `Barriere2011LauePrototype` | arXiv `1111.6700` title/authors | Laue-lens prototype background |
| `Weidenspointner2006MAX` | arXiv `astro-ph/0603152` title/authors | MAX Laue-lens detector concept |
| `Zhang2022TESGamma` | arXiv `2204.00010` title/authors | TES gamma-detector context |
| `Karwin2023` | arXiv `2310.12206` title/authors | COSI diffuse continuum context |
| `Gallego2025` | arXiv `2510.25304` title/authors | COSI pre-flight background context |

## Remaining Citation Checks Before Submission

- The current manuscript bibliography has no known unresolved weak metadata
  entries from the Claude R4 review pass. The formal COSI detection paper now
  has its ApJ DOI in the manuscript bibliography.
- Retraction checks were not performed systematically. The checked Crossref
  records did not surface retraction/update notices for these entries, but an
  independent Retraction Watch or publisher-site sweep should still be done
  before submission.
- Recent arXiv-only entries remain intentionally labeled as preprints until a
  journal version is selected or published.
