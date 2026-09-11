#!/usr/bin/env python3
"""Validate executable m05cc-v2 TSV headers against the record schema."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from preflight_common import PACKAGE, rel, sha256, strict_json


MAPPING = PACKAGE / "schema/m05cc_v1.mapping.json"
LOGICAL_SCHEMA = PACKAGE / "schema/m05cc_v2.record_schema.json"
ACTIVE_WHITELIST = PACKAGE / "schema/active_volume_whitelist_v1.json"
SCORER = PACKAGE / "code/shadow_extensions/M05CompactScorer.cc"
CPP_STREAMS = {
    "roots": "Root",
    "generated_observations": "GeneratedObservation",
    "events": "Event",
    "pixels": "Pixel",
    "deposits": "Deposit",
    "veto_blocks": "VetoBlock",
    "activation": "Activation",
    "truth_index": "TruthIndex",
    "footer": "Footer",
}


def _cpp_header(text: str, stream: str) -> list[str]:
    pattern = rf'm_{re.escape(stream)}Out\s*<<\s*((?:"(?:[^"\\]|\\.)*"\s*)+);'
    match = re.search(pattern, text, re.DOTALL)
    if match is None:
        raise ValueError(f"missing literal header for m_{stream}Out")
    literals = re.findall(r'"(?:[^"\\]|\\.)*"', match.group(1))
    value = "".join(ast.literal_eval(literal) for literal in literals)
    if not value.endswith("\n") or "\n" in value[:-1]:
        raise ValueError(f"m_{stream}Out header is not exactly one line")
    columns = value[:-1].split("\t")
    if not columns or len(columns) != len(set(columns)):
        raise ValueError(f"m_{stream}Out has empty/duplicate columns")
    return columns


def _cpp_array(text: str, name: str) -> list[str]:
    match = re.search(
        rf"const char\* const\s+{re.escape(name)}\[\]\s*=\s*\{{(.*?)\}};", text, re.DOTALL
    )
    if match is None:
        raise ValueError(f"missing physical-volume array {name}")
    values = [ast.literal_eval(value) for value in re.findall(r'"(?:[^"\\]|\\.)*"', match.group(1))]
    if not values or len(values) != len(set(values)):
        raise ValueError(f"empty/duplicate physical-volume array {name}")
    return values


def validate_mapping() -> dict[str, Any]:
    schema = strict_json(LOGICAL_SCHEMA)
    whitelist = strict_json(ACTIVE_WHITELIST)
    scorer_text = SCORER.read_text(encoding="utf-8")
    tables = schema.get("x-tsv-tables")
    if schema.get("$id") != "urn:tes511:m05cc-v2-record-bundle" or not isinstance(tables, dict):
        raise ValueError("wrong executable record schema")
    if set(CPP_STREAMS) != set(tables):
        raise ValueError("C++/record-schema table set mismatch")
    actual: dict[str, list[str]] = {}
    for table, stream in CPP_STREAMS.items():
        actual[table] = _cpp_header(scorer_text, stream)
        if actual[table] != tables[table]["header"]:
            raise ValueError(f"{table} scorer header differs from executable record schema")
    scorer_arrays = {
        "mass_csi_physical_volumes": _cpp_array(scorer_text, "kMassCSI"),
        "o8_bgo_physical_volumes": _cpp_array(scorer_text, "kO8BGO"),
        "o8_plastic_physical_volumes": _cpp_array(scorer_text, "kO8Plastic"),
    }
    for key, actual_values in scorer_arrays.items():
        if actual_values != whitelist.get(key):
            raise ValueError(f"scorer {key} differs from frozen active-volume whitelist")
    if (
        'volume.compare(0, 4, "TP_L") == 0' not in scorer_text
        or "volume[4] >= '0' && volume[4] <= '5'" not in scorer_text
        or 'upper.find("KAPTON")' not in scorer_text
        or "const bool truthRequired = rawTES || row.control" not in scorer_text
        or "m_TESZeroControlCount > 0" not in scorer_text
    ):
        raise ValueError("scorer selection/TES/Kapton rules differ from frozen schema")
    return {
        "status": "PASS__SCORER_HEADERS_MATCH_FROZEN_M05CC_MAPPING",
        "mapping_path": rel(LOGICAL_SCHEMA),
        "mapping_sha256": sha256(LOGICAL_SCHEMA),
        "logical_schema_path": rel(LOGICAL_SCHEMA),
        "logical_schema_sha256": sha256(LOGICAL_SCHEMA),
        "legacy_mapping_path": rel(MAPPING),
        "legacy_mapping_sha256": sha256(MAPPING),
        "active_volume_whitelist_path": rel(ACTIVE_WHITELIST),
        "active_volume_whitelist_sha256": sha256(ACTIVE_WHITELIST),
        "scorer_path": rel(SCORER),
        "scorer_sha256": sha256(SCORER),
        "physical_table_columns": actual,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
