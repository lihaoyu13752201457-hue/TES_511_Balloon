#!/usr/bin/env python3
"""Create and execute a dependency-light audit notebook for this analysis."""

from __future__ import annotations

import contextlib
import io
import json
import uuid
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
OUTPUT = PACKAGE / "analysis/s3d_o8_source_driven_optimization.ipynb"


def markdown(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": source,
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": source,
    }


def execute(cells: list[dict]) -> None:
    namespace: dict = {}
    count = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        count += 1
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exec(compile(cell["source"], f"notebook-cell-{count}", "exec"), namespace)
        cell["execution_count"] = count
        text = stream.getvalue()
        if text:
            cell["outputs"] = [{"name": "stdout", "output_type": "stream", "text": text}]


def main() -> None:
    cells = [
        markdown(
            "# S3d-O8 source-driven background optimization\n\n"
            "This notebook is the compact, executable audit trail for the 2026-08-14 analysis. "
            "It performs post-processing only: no Cosima transport, BUILDUP, or geometry promotion."
        ),
        code(
            "from pathlib import Path\n"
            "import json, csv, math\n"
            f"PACKAGE = Path({str(PACKAGE)!r})\n"
            "summary = json.loads((PACKAGE/'data/source_driven_optimization_summary.json').read_text())\n"
            "print(summary['status'])\n"
            "print('geometry:', summary['geometry'])"
        ),
        markdown("## Reference and frozen operating point"),
        code(
            "for name in ('baseline', 'frozen_selection'):\n"
            "    row = summary[name]\n"
            "    print(name, {k: row[k] for k in row if k in ('aeff_cm2','prompt_cps','delayed_cps','total_cps','mission_f3')})"
        ),
        markdown("## Prompt mechanism and directions"),
        code(
            "p = summary['prompt_origin']\n"
            "print('W2 pre-veto:', p['w2_pre_veto_events'], 'rejected:', p['veto50_rejected'])\n"
            "for row in p['veto50_survivors']:\n"
            "    print(row)\n"
            "print(p['direction_scope'])"
        ),
        markdown("## Delayed source ranking"),
        code(
            "for dimension in ('family','parent_ZA','volume'):\n"
            "    print('\\n'+dimension)\n"
            "    for row in summary['delayed_origin'][dimension][:8]:\n"
            "        print(f\"{row['key']:<55} n={row['events']:3d} rate={row['rate_cps']:.9f} +/- {row['mc_sigma_cps']:.9f}\")"
        ),
        markdown("## LC1/LC2 proxy calculations and the exact retained mission fold"),
        code(
            "gate = summary['mission_gate']\n"
            "print('S20 =', gate['signal_counts_20d'])\n"
            "print('target B20 =', gate['target_background_counts_20d'])\n"
            "print('conditional boundary:', gate['boundary'])\n"
            "for name, row in gate['proxies'].items():\n"
            "    required = row['required_prompt_suppression_fraction_for_target']\n"
            "    if required is None:\n"
            "        budget = ('prompt-only infeasible; additional delayed reduction='\n"
            "                  f\"{100*row['additional_delayed_reduction_required_fraction_if_zero_prompt']:.2f}%\")\n"
            "    else:\n"
            "        budget = f\"required P suppression={100*required:.2f}%\"\n"
            "    print(f\"{name:<48} D20={row['delayed_counts_20d']:.3f} \"\n"
            "          f\"F3(current P)={row['f3_if_current_prompt']:.8e} \"\n"
            "          f\"F3(P=0)={row['f3_if_zero_prompt']:.8e} \"\n"
            "          f\"{budget}\")"
        ),
        markdown(
            "![Source budget and mission gate](../figures/source_budget_and_candidate_gate.png)\n\n"
            "Error bars on the left are counting-only weighted MC errors. The candidate bars on the right are screening proxies, "
            "not a transport confidence interval."
        ),
        markdown("## Decision boundary"),
        code(
            "for item in summary['claim_boundaries']:\n"
            "    print('-', item)\n"
            "print('\\nRecommended route:')\n"
            "for i, item in enumerate(summary['recommended_route'], 1):\n"
            "    print(f'{i}. {item}')"
        ),
    ]
    execute(cells)
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
