# EA manuscript bilingual alignment report — 2026-07-13

## Outcome

`balloon511_ea_draft_en.tex` and `balloon511_ea_draft_zh.tex` now present the
same current scientific story in the same order. The English introduction was
expanded as a direct translation of the more detailed Chinese introduction;
shorter passages elsewhere were likewise brought up to the detail level of the
longer counterpart. The aligned PDFs are:

- `balloon511_ea_draft_en_aligned_20260713.pdf`
- `balloon511_ea_draft_zh_aligned_20260713.pdf`

The prior peer-review and annotated-review drafts were not used as source
material for this alignment. The authorities were the two active manuscript
sources and the retained/current engineering evidence packages.

## Inconsistencies found and resolved

| Area | Before alignment | Resolution |
|---|---|---|
| Introduction | The Chinese draft contained the full annihilation-physics, diffuse-emission, compact-source, Laue-optics, TES, and background context; the English draft was much shorter. | Replaced the short English introduction with a faithful, citation-preserving translation of the detailed Chinese text. |
| Science requirements | The requirement block occupied different structural positions. | Placed it as the first subsection of the introduction in both languages. |
| Geometry terminology | Working design identifiers and historical geometry names remained in the article narrative. | Replaced them with the public terms “mass-complete reference geometry” / “质量完备参考几何” and “final directionally graded active-shield geometry” / “最终方向分级主动屏蔽几何”. |
| Mission fold | The English draft retained an obsolete scalar trajectory implementation that was absent from the Chinese draft and superseded by later engineering evidence. | Removed the historical scalar implementation from the English article and made both texts describe the current family/nuclide-resolved trajectory fold. |
| Activation scope | The distinction between the all-family reference inventory and the neutron-induced final-geometry inventory was not equally explicit. | Both manuscripts now state that the reference inventory diagnoses material origins, while the final geometry uses a separate 29.233 Bq neutron-induced day-15 inventory; delayed activation from the other seven incident families was not transported and is not interpreted as zero. |
| Mission values | Older trajectory-fold counts, significances, thresholds, and exposure times remained in parts of the story. | Updated abstract, methods, result tables, figure, captions, discussion, and conclusions to the current family/nuclide-resolved authority. |
| End matter | The Chinese draft lacked the English data/software and declarations sections. | Added aligned Chinese end matter. |
| References | Citation use and bibliography coverage were not fully synchronized. | Both sources now cite the same 40 keys, use sequential numeric citations, and list the same 40 bibliography entries in first-citation order, with no missing or unused entry. |
| Figures | The reference-geometry filename and mission curve reflected working-package nomenclature or the retired mission fold. | Added a public reference-geometry figure filename and regenerated the mission figure from the current family/nuclide timeline. |

## Current numerical authority carried by both texts

- Day-15 final background: `0.00584951847335 counts s^-1`.
- Day-15 reference signal: `0.00111348117126 counts s^-1`.
- Prompt, delayed, and atmospheric-line background components:
  `0.00339303151412`, `0.00090122560728`, and `0.00155526135195 counts s^-1`.
- Twenty-day source and background counts: `1865.086821171` and
  `10082.93517708`.
- Central and conservative twenty-day significance: `18.5740053275` and
  `6.48443197766`.
- Central and conservative three-sigma flux threshold:
  `1.61516051444e-5` and `4.62646537173e-5 ph cm^-2 s^-1`.
- Central three- and five-sigma exposure: `0.41456678 d` and `1.0456162 d`.
- Conservative three- and five-sigma exposure: `4.13236549 d` and
  `11.50036258 d`.

## Alignment and build audit

The reproducible audit is `validate_bilingual_alignment_20260713.py`; its
machine-readable result is `ea_bilingual_alignment_validation_20260713.json`.
It passes with the following matched structure:

| Element | English | Chinese |
|---|---:|---:|
| Numbered sections | 5 | 5 |
| Unnumbered sections | 2 | 2 |
| Subsections | 12 | 12 |
| Subsubsections | 6 | 6 |
| Figures | 10 | 10 |
| Tables | 7 | 7 |
| Numbered equation environments | 20 | 20 |
| Cited/bibliography keys | 40/40 | 40/40 |
| PDF pages | 24 | 25 |

The heading-level sequence, corresponding paragraph-block counts, and ordered
figure/table/equation sequence are identical. Source and extracted PDF text are
free of the prohibited working design identifiers. Both PDFs compile without
overfull boxes or undefined citations/references. Citations render numerically,
and contiguous multi-reference groups are compressed. The Chinese log retains only
environmental Fandol font-script notices and non-fatal underfull-box messages.
