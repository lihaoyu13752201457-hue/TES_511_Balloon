{
  "call_id": "call_T1A6oToagZCH2pY8gDiOb61B",
  "cmd": "sed -n '1,240p' core_md/balloon511_ea_latex_drafts/README.md",
  "call_log": "/home/ubuntu/.codex/sessions/2026/07/01/rollout-2026-07-01T22-08-25-019f1e02-73cd-7511-ac67-a36d2a3c1926.jsonl",
  "call_line": 2270,
  "output_log": "/home/ubuntu/.codex/sessions/2026/07/01/rollout-2026-07-01T22-08-25-019f1e02-73cd-7511-ac67-a36d2a3c1926.jsonl",
  "output_line": 2274
}

# balloon511 — Experimental Astronomy (Springer) format

The **same manuscript** as `../balloon511_nima_latex_drafts/`, re-cast into the
**Experimental Astronomy (EA, Springer)** journal layout and reorganized into an
EA-style section architecture. The title, abstract, keywords, body text,
equations, tables, figures, and the 32-entry bibliography are carried over
**verbatim**; only the journal *format* and the *section structure* changed.

## Files

| File | What |
|---|---|
| `balloon511_ea_draft_en.tex` / `.pdf` | English manuscript — official Springer Nature class (`sn-jnl.cls`), 31 pp A4. Compile with **pdfLaTeX**. |
| `balloon511_ea_draft_zh.tex` / `.pdf` | Chinese internal-comparison draft — EA layout emulated on `article`+`ctex`, 22 pp A4. Compile with **XeLaTeX**. |
| `sn-jnl.cls` | Official Springer Nature journal class used by the English draft. |
| `paper_source_figure_table/` | Figure assets (self-contained copy). |
| `build_ea_format.py` | Original generator: NIM-A (`elsarticle`) source → EA layout. |
| `restructure_ea_en.py`, `restructure_ea_zh.py` | 11-section → 8-section regrouping. |
| `restructure_ea_5sec.py` | 8-section → final 5-section compression (both languages). |
| `*_prestructure.bak.tex`, `*_8sec.bak.tex` | Backups at each stage (rollback). |

## Section structure (EA-aligned, 5 sections)

```
1  Introduction
     1.1  Science and instrument requirements
2  Detector and cryostat mass model          (the instrument, before the methods)
3  Simulation framework
     3.1  Simulation workflow      3.2  Laue optics & signal replay
     3.3  Prompt & delayed source model (3.3.1 prompt / 3.3.2 delayed)
     3.4  Event selection & veto   3.5  Mission-time fold & significance
4  Results
     4.1  Primary unresolved-line sensitivity   4.2  Background composition
     4.3  Delayed-source normalization & convergence   4.4  Upstream optics boundary
5  Discussion and conclusions
     5.1  Limitations and future validation     5.2  Conclusions
Appendix A  Delayed-source construction diagnostics
```

This follows how EA gamma-ray simulation papers are organized — few top-level
sections, the instrument before the methods, the whole simulation chain grouped
under one section, validation folded into Results, and Discussion merged with
Conclusions. Reference templates: Ciabattoni et al. 2025, *Exp. Astron.* 60, 1
(doi:10.1007/s10686-025-10019-7); Gallego et al. 2025, COSI balloon background
(arXiv:2503.02493). The English `.tex` was restructured from the original
11-section technical-report layout in two scripted, auditable passes
(11→8→5); each pass preserves every table, figure, equation, and reference.

## How it was built

```bash
latexmk -pdf   balloon511_ea_draft_en.tex     # sn-jnl + pdfLaTeX -> en PDF
latexmk -pdfxe balloon511_ea_draft_zh.tex     # article+ctex + XeLaTeX -> zh PDF
```

The English draft is on the **official `sn-jnl.cls`** (submission-ready class).
The Chinese draft stays on an **EA-emulated `article`+`ctex`** layout because
`sn-jnl.cls` targets pdfLaTeX/English; moving the Chinese draft onto `sn-jnl`
with XeLaTeX/CJK is a possible follow-up but is not yet validated. Both share the
same 5-section structure and content.

## Deliberately NOT changed (still matches the source)

- **Citations stay numbered** (`[1]`, `[2]`, …) via the manual `thebibliography`.
  EA's published style is author–year; converting needs a `.bib` + Springer
  `.bst` and would change in-text citations, so it is left as-is. Switch on request.
- Draft-revision markup (`\added` red / `\rewritten` green, and the red Phase-2
  evidence tables) is preserved; accept it into black before submission.
- Authors/affiliations remain anonymized ("Authors omitted for review").

## Source of truth

Numbers and wording are governed by the NIM-A draft and
`../balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.md`. This EA
copy is a format + structure port; regenerate/restructure with the scripts above
rather than hand-editing if the underlying manuscript text changes.
