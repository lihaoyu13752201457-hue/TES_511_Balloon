# balloon511 — Experimental Astronomy (Springer) format

This directory is the active editorial home of the **Experimental Astronomy
(EA, Springer)** manuscript. The root English and Chinese `.tex` files are the
authoritative working sources. They began as a format port of the NIM-A draft,
but later detector, mission-fold, background, and optimization revisions are
maintained here and are no longer a verbatim mirror.

## Files

| File | What |
|---|---|
| `balloon511_ea_draft_en.tex` | English EA-format manuscript (authoritative working source) |
| `balloon511_ea_draft_zh.tex` | Sentence-aligned Chinese manuscript (authoritative working source) |
| `balloon511_ea_draft_en_aligned_20260713.pdf` | Current aligned English reading copy |
| `balloon511_ea_draft_zh_aligned_20260713.pdf` | Current aligned Chinese reading copy |
| `recovered_compile_ready/` | Mirrored compile-ready copies (`graphicspath` uses `../`) |
| `paper_source_figure_table/` | Paper figures for the reference geometry, background origins, final graded shield, cut flow, and mission result |
| `paper_source_figure_table/build_background_optimization_story_20260713.py` | Regenerates the current source-backed geometry, background, cut-flow, and mission-significance figures |
| `convert_numeric_citations_20260713.py` | Reorders both bibliographies by first citation and removes author--year item labels |
| `validate_bilingual_alignment_20260713.py` | Checks EN/ZH structure, references, current values, public terminology, build logs, and PDF text |
| `ea_bilingual_alignment_validation_20260713.json` | Machine-readable result of the bilingual validation |

## Build

```bash
latexmk -pdfxe -jobname=balloon511_ea_draft_en_aligned_20260713 balloon511_ea_draft_en.tex
latexmk -pdfxe -jobname=balloon511_ea_draft_zh_aligned_20260713 balloon511_ea_draft_zh.tex
python3 validate_bilingual_alignment_20260713.py
```

Engine: **XeLaTeX** (`latexmk -pdfxe`), matching the project convention. Latin
text uses **TeX Gyre Termes** (a free Times clone, the Springer body font); the
Chinese draft adds `ctex`.

## What "EA format" means here (important)

Springer's **official** EA class is `sn-jnl.cls` (the Springer Nature template).
It is **not installed on this machine and was not downloaded into this
workspace**. The layout here therefore **emulates** the EA/Springer single-column look
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

## Editorial conventions

- Citations use sequential numbers in order of first appearance. The `cite`
  package sorts and compresses multi-reference groups (for example, `[3--5]`),
  while the shared manual `thebibliography` keeps EN/ZH numbering identical.
- Float captions read `Figure N` / `Table N` (kept consistent with the body
  text, which says "Figure"/"Section"). Springer production uses `Fig. N`.
- Authors/affiliations remain anonymized ("Authors omitted for review"), exactly
  as in the source.

## Source of truth

The active sources are:

- `balloon511_ea_draft_en.tex`
- `balloon511_ea_draft_zh.tex`

The NIM-A draft and its evidence manifest remain historical provenance, not a
rewrite authority for current EA text. `recovered_compile_ready/` is a frozen
derived/recovery mirror and must not be edited as an independent manuscript.
Do not run the historical `build_ea_format.py` over the active sources; if a
derived mirror is needed, regenerate it explicitly from the reviewed root EA
sources after both language versions compile and their numerical evidence has
passed validation.

## Current revision status — 2026-07-13

### Internal M02 audit correction — 2026-08-04

The final quantitative BGO anticoincidence path sums step-level `CC HIT`
deposits over the active volumes and applies the 50 keV cut in post-processing.
The detector-map `TriggerThreshold 80` field is not consumed by this selection,
and raw/production data retain deposits below 80 keV. Do not schedule a native
50 keV rerun unless new evidence shows that the final mask reads native flags or
that `CC HIT` was truncated before serialization. This is project-governance
context only; manuscript prose should state the offline deposited-energy method
and its hardware-response limitations without narrating this audit history.

The active EN/ZH manuscripts now tell the same public, current-geometry story
section by section and paragraph block by paragraph block. A generated
mass-complete reference detector--cryostat geometry establishes the transported
instrument and identifies the particle and material origins of the 511 keV
background. Those origins motivate the final directionally graded BGO shield;
the final full chain then closes the cut flow, finite-count support, background
budget, and mission significance. The headline rates include the stated 420 eV
FWHM pixel-level energy response and a 64-seed numerical response audit.

The mission result uses the family/nuclide-resolved trajectory fold that
supersedes the retired scalar fold: at 20 days, the central and conservative
significances are 18.574 and 6.484, and the corresponding $3\sigma$ flux
thresholds are $1.6152\times10^{-5}$ and $4.6265\times10^{-5}$
ph cm$^{-2}$ s$^{-1}$. The article body contains only public descriptive names
for the reference and final geometries; it presents neither internal design
labels nor a mass-reduction story.

See `EA_BACKGROUND_OPTIMIZATION_STORYBOARD_20260713.md` for the literature-led
narrative, figure questions, numerical authorities, and scope. The official
journal guidance consulted for this revision specifies a 150--250-word abstract
and four to six keywords. Run `validate_bilingual_alignment_20260713.py` after
rebuilding both PDFs to verify the synchronized structure, citation inventory,
first-citation reference order, numeric citation rendering, current mission
values, public terminology, compile logs, and visible PDF text.
