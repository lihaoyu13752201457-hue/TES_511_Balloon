# Chart contract — matched PARMA mono-511 comparison

- Analytical question: after adding only the W-grid, how does the selected
  PARMA monoenergetic 510.99895-keV response change relative to open SH3?
- Intended takeaway: report the measured final rate ratio with independent MC
  uncertainty, then show at which common selection stage that ratio appears.
- Family/variant: `Uncertainty & Benchmark`; two-panel dot-and-interval chart.
  Panel A compares the two absolute final line rates from a zero baseline.
  Panel B shows ordered W-grid/open stage ratios against a neutral ratio-1
  benchmark.
- Data sufficiency: two geometry totals, five matched ordered selection stages,
  and two complete 80-row equal-mu contribution tables. The 80-bin tables are
  used for sum closure and a sparse descriptive angular diagnostic, not a main
  chart.
- Renderer and surface: reproducible Matplotlib static output, PNG plus vector
  PDF, embedded in a Chinese technical Markdown report.
- Palette/non-color policy: hard two-root cap. Open SH3 is blue with an open
  circular marker; W-grid is gold with a filled square. A dashed neutral line
  marks ratio 1, so the comparison remains readable without color.
- Required context: 510.99895 keV; day-15 PARMA full-space flux
  0.16651547160226118 ph cm^-2 s^-1; 80 equal-mu components; matched incident
  count, response, selection, and physical exposure; 1-sigma independent MC
  intervals.
- Scope guard: the chart is mono-line-only. It must not be labeled or read as a
  broadband total-background, accumulated-background, significance, or Fmin
  comparison.
- QA surface: inspect the generated PNG at full size; verify the PDF header,
  CJK font selection, non-clipped labels, zero-based absolute-rate scale,
  ratio-1 reference, source hashes, and all numerical closure gates in
  `qa_receipt.json`.
