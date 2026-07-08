{
  "call_id": "call_Obx6ARKJ0LeRsXHrfTvCERN3",
  "cmd": "tail -40 core_md/balloon511_ea_latex_drafts/_recovery_logs/fragments/core_md_balloon511_ea_latex_drafts_README.md__L1_260.txt",
  "call_log": "/home/ubuntu/.codex/sessions/2026/07/07/rollout-2026-07-07T22-24-21-019f3cf7-3376-7f00-b377-ae00d8780a8d.jsonl",
  "call_line": 1299,
  "output_log": "/home/ubuntu/.codex/sessions/2026/07/07/rollout-2026-07-07T22-24-21-019f3cf7-3376-7f00-b377-ae00d8780a8d.jsonl",
  "output_line": 1303
}


Engine: **XeLaTeX** (`latexmk -pdfxe`), matching the project convention. Latin
text uses **TeX Gyre Termes** (a free Times clone, the Springer body font); the
Chinese draft adds `ctex`.

## What "EA format" means here (important)

Springer's **official** EA class is `sn-jnl.cls` (the Springer Nature template).
It is **not installed on this machine, and was not downloaded** (no network was
used). The layout here therefore **emulates** the EA/Springer single-column look
with standard LaTeX packages (`geometry`, `titlesec`, `fancyhdr`, `caption`,
`fontspec`): running header with the journal name, left-aligned bold title,
author/affiliation block, ruled abstract with a bold `Abstract` run-in, a
`Keywords` line with `·` separators, bold numbered section headings, and Times
body text.

**For an actual submission**, replace the emulated preamble with the official
`sn-jnl.cls` (drop `sn-jnl.cls` + its `.bst` files into this folder and change
`\documentclass`); the document is already organized in Springer order
(title → authors → abstract → keywords → numbered sections → references), so the
swap is mechanical.

## Deliberately NOT changed (still matches the source)

- **Citations stay numbered** (`[1]`, `[2]`, …) using the source's manual
  `thebibliography`. EA's published style is author–year; converting would need a
  `.bib` + Springer `.bst` and would alter in-text citation rendering, so it was
  left as-is to preserve the text exactly. Switch on request.
- Float captions read `Figure N` / `Table N` (kept consistent with the body
  text, which says "Figure"/"Section"). Springer production uses `Fig. N`.
- Authors/affiliations remain anonymized ("Authors omitted for review"), exactly
  as in the source.

## Source of truth

Numbers and wording are governed by the NIM-A draft and
`../balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.md`. This EA
copy is a **format port**; if the manuscript text changes, re-run
`build_ea_format.py` to regenerate both EA `.tex` files rather than editing them
by hand.
