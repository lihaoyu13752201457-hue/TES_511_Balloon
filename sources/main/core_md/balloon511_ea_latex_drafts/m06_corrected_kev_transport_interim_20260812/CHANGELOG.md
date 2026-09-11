# M06 changelog

## 2026-08-12 — scaffold initialization

- Created the new, independent directory
  `m06_corrected_kev_transport_interim_20260812`; no retained directory was
  overwritten.
- Physically copied the latest English and Chinese M05 TeX parents to paired
  M06 filenames.
- Added only a seven-line `%` comment banner to each copied TeX identifying it
  as `DRAFT -- NOT_PUBLICATION_AUTHORITY` and as the M06 interim scaffold.
- Preserved every inherited scientific value, table, figure reference,
  citation, and manuscript sentence byte-for-byte below that banner.
- Recorded all six M05 parent artifacts and their SHA-256 values in
  `PARENT_SNAPSHOT.json`.
- Did not copy the M05 PDF/XDV build products, compile M06, publish anything,
  or fill any result value.
- Added the data-authority gate matrix, empty number registry, and automated
  lineage validation.

## Required format for future entries

Each future change must record:

- date and author/agent;
- English and Chinese locations changed;
- `manuscript_numbers.json` record identifiers used;
- validated input artifact paths and SHA-256 values;
- normalization and uncertainty definition;
- validation/review command and outcome; and
- whether any inherited figure, table, abstract value, conclusion, or mission
  result remains blocked.

## 2026-08-12 — corrected-keV non-full interim insertion (Codex)

- Updated the English and Chinese title, abstract, Methods, Results,
  Discussion, limitations, and conclusion as a paired revision.
- Preserved the inherited M05 Methods/Results/Discussion text in both TeX files
  but disabled it with `\iffalse ... \fi`; no M05 file was modified.
- Populated `manuscript_numbers.json` schema 2.0 with exact values separated by
  geometry, selection, and window for the validated $2.001$M-per-geometry
  prompt-gamma diagnostic.
- Inserted batch0004 partial-checkpoint and batch0005 reduced-breadth exposure
  metadata by stage and geometry: new events, TT, RP record count, and
  `sum_RP`. RP is explicitly labelled as a raw production tally, not Bq or a
  delayed rate.
- Cited the validated gamma TES-spectrum PNG and veto-cutflow PNG in both
  active manuscripts. Exact artifact paths and SHA-256 values are in the
  machine-readable registry.
- Input authorities: corrected source contract `5424eeca…4326`; gamma-prefix
  ledger/validation `3519c39d…16fc` / `5d2784c9…9813`; gamma post-process
  summary/validation `08e43171…ad2` / `8012f103…a7f`; batch0004 partial
  ledger/validation `b4de513e…ba0` / `3d29449d…291`; batch0005 add-on
  ledger/validation `670bc6f1…1a0` / `d100985b…cee`.
- Gamma rate normalization is count divided by summed positive matching TT;
  rate intervals are two-sided exact 95% Garwood intervals, and efficiency
  intervals are two-sided 95% Wilson intervals.
- Kept proton coverage, activity, delayed transport, all-stream response,
  geometry promotion, mission significance, and sensitivity blocked. No old
  factor-1000 value is active in the M06 Methods/Results/Discussion block.
- Validation command:
  `python3 core_md/balloon511_ea_latex_drafts/m06_corrected_kev_transport_interim_20260812/validate_m06_scaffold.py`.
- M06 remains `DRAFT — NOT_PUBLICATION_AUTHORITY`; no PDF was compiled.
