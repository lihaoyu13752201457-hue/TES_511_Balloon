# PDF QA report

Final artifact:
`TES_511_particle_source_unit_evidence_20260811.pdf`

## Result

PASS. The final PDF was rendered from the validated, self-contained static
HTML and visually inspected page by page.

## Mechanical checks

- PDF size: 750,255 bytes
- Page count: 5
- Page size: A4, 594.96 × 841.92 pt
- PDF version: 1.4
- Tagged PDF: yes
- Encryption: none
- Searchable text extraction: PASS, 18,792 bytes extracted
- Embedded evidence chart: PASS, page 2, 1629 × 759 px source image
- Font embedding: PASS; all listed fonts embedded
- Expected headline text: PASS (`480`, `7,639,501`, raw-rebuild residuals,
  source-directory name, and source appendix all found)
- Negative label scan: PASS; no Share/Edit/Refresh/Publish controls or internal
  snapshot/widget/manifest/package/validation/temp labels found

## Visual checks

Rendered every final page at 120 dpi to `qa/pages/page-1.png` through
`qa/pages/page-5.png` and inspected them for:

- blank or missing pages
- missing Chinese glyphs
- clipped titles, narrative, chart, tables, paths, and source appendix
- overlapping chart labels
- table overflow beyond A4 margins
- app-only controls or runtime metadata

All checks passed. The chart is legible, all tables remain within the page,
and the final source section is reader-facing.

## Build note

The canonical artifact passed the portable builder's schema/provenance
validation. The plugin's optional full interactive browser verifier exceeded
its environment time budget, so the report uses a reviewed Matplotlib static
chart in the print path and was independently checked with `pdfinfo`,
`pdftotext`, `pdffonts`, `pdfimages`, `pdftoppm`, negative text scans, and
all-page visual inspection. `qpdf` was not installed.

## Artifact hashes

```text
59ee9035c9caef4a5f085feb6aa467000159c4100002e1ef6b44125a4aa343de  TES_511_particle_source_unit_evidence_20260811.pdf
0b40fab472cfe95a50decaa9e8e26065ecf121111424fd55eaf4a6d1e5c334cd  TES_511_particle_source_unit_evidence_20260811.html
8e2a62f27753884bc76e767ffc5720e302212fd9a1e2d39193cdf567500f4848  artifact.json
```
