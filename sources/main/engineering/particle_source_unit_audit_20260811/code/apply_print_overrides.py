#!/usr/bin/env python3
"""Apply reader-facing A4 print rules to the generated portable HTML."""

from __future__ import annotations

import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
HTML = PACKAGE / "report/TES_511_particle_source_unit_evidence_20260811.html"
MARKER = 'data-tes511-print-overrides="true"'

STYLE = r"""
<style data-tes511-print-overrides="true">
@page { size: A4; margin: 12mm 11mm 14mm; }
@media print {
  html, body { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .portable-page-header {
    display: flex !important;
    margin-bottom: 18px !important;
    padding-bottom: 14px !important;
    border-bottom: 1px solid var(--portable-border) !important;
  }
  .portable-surface-label,
  .portable-page-meta { display: none !important; }
  .portable-block-stack { margin-top: 18px !important; }
  .portable-inline-source { display: none !important; }
  .portable-sources {
    display: block !important;
    break-before: auto;
    overflow-wrap: anywhere;
  }
  .portable-sources details { display: none !important; }
  [data-artifact-block-id="family_chart_block"] { display: none !important; }
  .portable-custom-html iframe {
    height: 320px !important;
    min-height: 320px !important;
    overflow: hidden !important;
  }
  .portable-table-scroll { overflow: visible !important; }
  .portable-table-scroll table {
    width: 100% !important;
    max-width: 100% !important;
    table-layout: fixed !important;
  }
  .portable-table-scroll th,
  .portable-table-scroll td {
    padding: 5px 5px !important;
    overflow: visible !important;
    text-overflow: clip !important;
    overflow-wrap: anywhere !important;
    word-break: normal !important;
    white-space: normal !important;
    font-size: 8.2px !important;
    line-height: 1.35 !important;
  }
  [data-table-id="unit_verdicts"] th:nth-child(1),
  [data-table-id="unit_verdicts"] td:nth-child(1) { width: 22%; }
  [data-table-id="unit_verdicts"] th:nth-child(2),
  [data-table-id="unit_verdicts"] td:nth-child(2) { width: 25%; }
  [data-table-id="unit_verdicts"] th:nth-child(3),
  [data-table-id="unit_verdicts"] td:nth-child(3) { width: 24%; }
  [data-table-id="unit_verdicts"] th:nth-child(4),
  [data-table-id="unit_verdicts"] td:nth-child(4) { width: 29%; }
  [data-table-id="family_detail"] th:nth-child(1),
  [data-table-id="family_detail"] td:nth-child(1) { width: 5%; }
  [data-table-id="family_detail"] th:nth-child(2),
  [data-table-id="family_detail"] td:nth-child(2) { width: 9%; }
  [data-table-id="family_detail"] th:nth-child(3),
  [data-table-id="family_detail"] td:nth-child(3) { width: 9%; }
  [data-table-id="family_detail"] th:nth-child(4),
  [data-table-id="family_detail"] td:nth-child(4) { width: 15%; }
  [data-table-id="family_detail"] th:nth-child(5),
  [data-table-id="family_detail"] td:nth-child(5) { width: 22%; }
  [data-table-id="family_detail"] th:nth-child(6),
  [data-table-id="family_detail"] td:nth-child(6) { width: 23%; }
  [data-table-id="family_detail"] th:nth-child(7),
  [data-table-id="family_detail"] td:nth-child(7) { width: 17%; }
  [data-table-id="package_references"] th:nth-child(1),
  [data-table-id="package_references"] td:nth-child(1) { width: 22%; }
  [data-table-id="package_references"] th:nth-child(2),
  [data-table-id="package_references"] td:nth-child(2) { width: 20%; }
  [data-table-id="package_references"] th:nth-child(3),
  [data-table-id="package_references"] td:nth-child(3) { width: 20%; }
  [data-table-id="package_references"] th:nth-child(4),
  [data-table-id="package_references"] td:nth-child(4) { width: 14%; }
  [data-table-id="package_references"] th:nth-child(5),
  [data-table-id="package_references"] td:nth-child(5) { width: 24%; }
  [data-table-id="authority_impact"] th:nth-child(1),
  [data-table-id="authority_impact"] td:nth-child(1) { width: 20%; }
  [data-table-id="authority_impact"] th:nth-child(2),
  [data-table-id="authority_impact"] td:nth-child(2) { width: 27%; }
  [data-table-id="authority_impact"] th:nth-child(3),
  [data-table-id="authority_impact"] td:nth-child(3) { width: 24%; }
  [data-table-id="authority_impact"] th:nth-child(4),
  [data-table-id="authority_impact"] td:nth-child(4) { width: 29%; }
  [data-table-id="evidence_locators"] th:nth-child(1),
  [data-table-id="evidence_locators"] td:nth-child(1) { width: 13%; }
  [data-table-id="evidence_locators"] th:nth-child(2),
  [data-table-id="evidence_locators"] td:nth-child(2) { width: 25%; }
  [data-table-id="evidence_locators"] th:nth-child(3),
  [data-table-id="evidence_locators"] td:nth-child(3) {
    width: 48%;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 7.2px !important;
  }
  [data-table-id="evidence_locators"] th:nth-child(4),
  [data-table-id="evidence_locators"] td:nth-child(4) { width: 14%; }
}
</style>
""".strip()


def main() -> int:
    text = HTML.read_text(encoding="utf-8")
    text = text.replace(
        '<h2 id="portable-sources-heading">Sources</h2>',
        '<h2 id="portable-sources-heading">来源材料</h2>',
        1,
    )
    if MARKER in text:
        text, substitutions = re.subn(
            r'<style data-tes511-print-overrides="true">.*?</style>\s*',
            "",
            text,
            count=1,
            flags=re.DOTALL,
        )
        if substitutions != 1:
            raise RuntimeError("could not replace existing print override block")
    if "</head>" not in text:
        raise RuntimeError("portable HTML has no closing head element")
    text = text.replace("</head>", STYLE + "\n</head>", 1)
    HTML.write_text(text, encoding="utf-8")
    print(f"updated {HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
