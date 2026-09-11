# M06 corrected-keV transport interim manuscript

> **DRAFT — NOT_PUBLICATION_AUTHORITY**

This directory is a non-overwriting, bilingual working copy of the latest M05
manuscript source. It now contains a validated, explicitly non-full
corrected-keV interim Methods/Results/Discussion replacement. It does not mutate
M05 and it is not publication authority.

## Lineage and current state

- Parent directory:
  `core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/`
- English parent TeX SHA-256:
  `8db941a4ce069bdb44b483ac93715615cf1d2765660e6fd69c7533f75186c129`
- Chinese parent TeX SHA-256:
  `a7ab9bca602a4b0236330cb35647ad80f99faa53814107351f4e458d2a1219f0`
- M06 initialization date: 2026-08-12
- Publication authority: **false**

The M06 English and Chinese TeX files are independent physical copies. Their
lineage remains recorded in `PARENT_SNAPSHOT.json`. The inherited M05
Methods/Results/Discussion blocks are preserved in-place but disabled with
`\iffalse ... \fi`; the active replacement reports only validated corrected-keV
gamma results and batch0004/batch0005 exposure metadata. Inherited factor-1000
prompt, activation, delayed, response, geometry-ranking, significance, and
sensitivity results are not active M06 content.

The M05 PDF and XDV files are recorded in `PARENT_SNAPSHOT.json` but were not
copied: they are compiled M05 artifacts and must not be mislabeled as M06.
No M06 compile or publication action was performed. The TeX sources retain the
existing shared figure references under
`core_md/balloon511_ea_latex_drafts/paper_source_figure_table/`; any eventual
release package must snapshot validated replacement figures explicitly.

## Files

| File | Purpose |
|---|---|
| `balloon511_ea_draft_en_m06_corrected_kev_transport_interim_20260812.tex` | English working source |
| `balloon511_ea_draft_zh_m06_corrected_kev_transport_interim_20260812.tex` | Chinese working source |
| `PARENT_SNAPSHOT.json` | Immutable parent paths, sizes, hashes, and copy mapping |
| `CHANGELOG.md` | Human-readable revision log |
| `DATA_AUTHORITY_MATRIX.md` | Evidence gates and paired replacement map |
| `manuscript_numbers.json` | Machine-readable authority registry and exact interim values |
| `validate_m06_scaffold.py` | Standard-library lineage, hash, number, and bilingual-scope validator |
| `README.md` | This status and use guide |

## Editing contract

1. Do not import any transport result whose source card references
   `cosima_spectra_dp_2602units`.
2. Do not add a separate monoenergetic 511 keV source to the repaired
   `unit_only_total_gamma` continuum. Its retained profile already includes the
   annihilation bump. A continuum-plus-mono model requires a separate,
   flux-closed, single-environment package.
3. A runtime batch may enter the manuscript only after dynamic validation and
   its merge ledger pass. Never pool geometry, mode, or particle family.
4. Update Methods and Results as a pair. Update the English and Chinese drafts
   in the same revision, then reconcile the abstract and conclusion against the
   same `manuscript_numbers.json` records.
5. Do not fill a result slot without a validated artifact path, SHA-256,
   normalization/exposure definition, uncertainty method, and reviewer state.
6. Proton pilot results remain diagnostic until the full-spectrum weighting and
   coverage decision is documented. Delayed claims additionally require the
   NUBASE ground-state correction, per-family TT guard, and inventory/source
   provenance.
7. Mission significance or sensitivity stays blocked until prompt, proton,
   atmospheric-line scope, delayed activation, detector response, and
   mission-time normalization all close on one consistent geometry contract.

## Validation

From the repository root, run:

```bash
python3 core_md/balloon511_ea_latex_drafts/m06_corrected_kev_transport_interim_20260812/validate_m06_scaffold.py
```

The validator fails if a parent hash changes, a M06 TeX is a link, an input
authority/hash/status differs from the registry, gamma cutflow values fail to
match the validated post-process summary, bilingual guardrails are missing, a
blocked claim is reopened, a required file is missing, or a compiled artifact
appears in this directory.

## Paper-writer phase state

| Phase | Status | Note |
|---|---|---|
| Project initialization / lineage | Done | Bilingual M06 scaffold and parent snapshot created |
| Methods and Results correction | Draft complete | Corrected source, gamma diagnostic, and batch0004/0005 exposure metadata inserted as non-full results |
| Figures and tables correction | Draft complete | Validated gamma spectrum/veto figures cited; exact cutflow and exposure tables inserted |
| Abstract and conclusion reconciliation | Draft complete | Both languages explicitly state the interim boundary |
| Humanize | Done for inserted text | Neutral wording; no promotion/sensitivity inference |
| Quality review | In progress | Machine validator covers provenance and bilingual numerical scope; independent scientific review remains open |
| Pre-submission / publication | Prohibited | This directory is not publication authority |
