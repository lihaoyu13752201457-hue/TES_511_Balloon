#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/ubuntu/TES_511_Balloon")
SESSION_ROOT = Path("/home/ubuntu/.codex/sessions")
HISTORY = Path("/home/ubuntu/.codex/history.jsonl")
EA_PREFIX = "core_md/balloon511_ea_latex_drafts"
EA_DIR = ROOT / EA_PREFIX
RECOVERY_DIR = EA_DIR / "_recovery_logs"


def iter_log_objects():
    paths = []
    if SESSION_ROOT.exists():
        paths.extend(sorted(SESSION_ROOT.rglob("*.jsonl")))
    if HISTORY.exists():
        paths.append(HISTORY)

    for path in paths:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for lineno, line in enumerate(handle, 1):
                    try:
                        yield path, lineno, json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue


def payload(obj):
    return obj.get("payload") if isinstance(obj.get("payload"), dict) else {}


def safe_name(text: str, max_len: int = 120) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return text[:max_len] or "item"


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_apply_patch_inputs():
    patches = []
    for log_path, lineno, obj in iter_log_objects():
        p = payload(obj)
        if p.get("type") == "custom_tool_call" and p.get("name") == "apply_patch":
            text = p.get("input") or ""
            if EA_PREFIX in text:
                patches.append((log_path, lineno, text))
        # Some older records store tool calls one level differently.
        if p.get("name") == "apply_patch" and isinstance(p.get("input"), str):
            text = p["input"]
            if EA_PREFIX in text:
                patches.append((log_path, lineno, text))
    return patches


def restore_add_files_from_patch(patch: str):
    restored = []
    current_path = None
    current_lines = []
    in_add = False

    def flush():
        if not in_add or not current_path:
            return
        if not current_path.startswith(EA_PREFIX + "/"):
            return
        out_path = ROOT / current_path
        content = "\n".join(current_lines)
        if patch.endswith("\n") or current_lines:
            content += "\n"
        write_text(out_path, content)
        restored.append(str(out_path.relative_to(ROOT)))

    for line in patch.splitlines():
        if line.startswith("*** Add File: "):
            flush()
            current_path = line[len("*** Add File: ") :].strip()
            current_lines = []
            in_add = current_path.startswith(EA_PREFIX + "/")
            continue
        if line.startswith("*** Update File: ") or line.startswith("*** Delete File: ") or line.startswith("*** End Patch"):
            flush()
            current_path = None
            current_lines = []
            in_add = False
            continue
        if in_add:
            if line.startswith("+"):
                current_lines.append(line[1:])
            elif line == "":
                current_lines.append("")

    flush()
    return restored


def parse_exec_calls_and_outputs():
    calls = {}
    outputs = []
    for log_path, lineno, obj in iter_log_objects():
        p = payload(obj)
        if p.get("type") == "function_call" and p.get("name") == "exec_command":
            call_id = p.get("call_id")
            args = {}
            raw_args = p.get("arguments")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
            if call_id:
                calls[call_id] = {
                    "cmd": args.get("cmd", ""),
                    "log": str(log_path),
                    "line": lineno,
                }
        elif p.get("type") == "function_call_output":
            call_id = p.get("call_id")
            output = p.get("output", "")
            if call_id in calls:
                outputs.append((log_path, lineno, call_id, calls[call_id], output))
    return outputs


def command_output_body(raw_output: str) -> str:
    marker = "\nOutput:\n"
    if marker in raw_output:
        return raw_output.split(marker, 1)[1]
    return raw_output


def extract_ea_path(text: str):
    match = re.search(r"(core_md/balloon511_ea_latex_drafts/[^\s'\"|;]+)", text)
    if not match:
        return None
    return match.group(1).rstrip(":,")


def extract_sed_range(cmd: str):
    match = re.search(r"sed\s+-n\s+['\"](\d+),(\d+)p['\"]", cmd)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def strip_nl_numbers(text: str):
    lines = []
    for line in text.splitlines():
        lines.append(re.sub(r"^\s*\d+\t", "", line))
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def save_command_evidence(outputs):
    saved = []
    fragments = []
    by_path = defaultdict(list)

    for index, (log_path, lineno, call_id, call, raw_output) in enumerate(outputs, 1):
        cmd = call.get("cmd", "")
        if EA_PREFIX not in cmd and EA_PREFIX not in raw_output:
            continue

        body = command_output_body(raw_output)
        meta = {
            "call_id": call_id,
            "cmd": cmd,
            "call_log": call.get("log"),
            "call_line": call.get("line"),
            "output_log": str(log_path),
            "output_line": lineno,
        }
        out_name = f"output_{index:05d}_{safe_name(cmd)}.txt"
        out_path = RECOVERY_DIR / "command_outputs" / out_name
        write_text(out_path, json.dumps(meta, ensure_ascii=False, indent=2) + "\n\n" + body)
        saved.append(str(out_path.relative_to(ROOT)))

        ea_path = extract_ea_path(cmd)
        sed_range = extract_sed_range(cmd)
        if ea_path and sed_range and body:
            fragment = strip_nl_numbers(body) if "nl -ba" in cmd else body
            frag_name = f"{safe_name(ea_path)}__L{sed_range[0]}_{sed_range[1]}.txt"
            frag_path = RECOVERY_DIR / "fragments" / frag_name
            write_text(
                frag_path,
                json.dumps(meta | {"source_path": ea_path, "range": sed_range}, ensure_ascii=False, indent=2)
                + "\n\n"
                + fragment,
            )
            fragments.append(str(frag_path.relative_to(ROOT)))
            by_path[ea_path].append({"range": sed_range, "fragment": str(frag_path.relative_to(ROOT))})

    return saved, fragments, by_path


def collect_predelete_file_lists(outputs):
    lists = []
    for index, (log_path, lineno, call_id, call, raw_output) in enumerate(outputs, 1):
        cmd = call.get("cmd", "")
        if not any(token in cmd for token in ("find ", "rg --files", "git status")):
            continue
        if EA_PREFIX not in raw_output and EA_PREFIX not in cmd:
            continue
        body = command_output_body(raw_output)
        out_path = RECOVERY_DIR / "file_lists" / f"file_list_{index:05d}_{safe_name(cmd)}.txt"
        meta = {
            "call_id": call_id,
            "cmd": cmd,
            "call_log": call.get("log"),
            "call_line": call.get("line"),
            "output_log": str(log_path),
            "output_line": lineno,
        }
        write_text(out_path, json.dumps(meta, ensure_ascii=False, indent=2) + "\n\n" + body)
        lists.append(str(out_path.relative_to(ROOT)))
    return lists


def read_fragment(fragment_path: Path):
    text = fragment_path.read_text(encoding="utf-8", errors="replace")
    head, sep, body = text.partition("\n\n")
    if not sep:
        return {}, text
    try:
        meta = json.loads(head)
    except json.JSONDecodeError:
        meta = {}
    return meta, body


def restore_complete_markdown_fragments():
    restored = []
    partial = []
    candidates = {
        EA_DIR / "README.md": RECOVERY_DIR / "fragments" / "core_md_balloon511_ea_latex_drafts_README.md__L1_260.txt",
        EA_DIR / "physics_review_publishability_20260702.md": RECOVERY_DIR / "fragments" / "core_md_balloon511_ea_latex_drafts_physics_review_publishability_20260702.md__L1_280.txt",
        EA_DIR
        / "paper_source_figure_table"
        / "README.md": RECOVERY_DIR
        / "fragments"
        / "core_md_balloon511_ea_latex_drafts_paper_source_figure_table_README.md__L1_260.txt",
        EA_DIR
        / "paper_source_figure_table"
        / "reconstruction_failure_diagnostic_20260702.md": RECOVERY_DIR
        / "fragments"
        / "core_md_balloon511_ea_latex_drafts_paper_source_figure_table_reconstruction_failure_diagnostic_20260702.md__L1_80.txt",
    }

    for out_path, fragment_path in candidates.items():
        if not fragment_path.exists():
            continue
        meta, body = read_fragment(fragment_path)
        end = (meta.get("range") or [None, None])[1]
        body_lines = body.splitlines()
        if end and len(body_lines) >= end:
            partial.append(str(out_path.relative_to(ROOT)))
            continue
        write_text(out_path, body)
        restored.append(str(out_path.relative_to(ROOT)))

    aoo_fragment = RECOVERY_DIR / "fragments" / "core_md_balloon511_ea_latex_drafts_AOO.md__L1_260.txt"
    if aoo_fragment.exists():
        meta, body = read_fragment(aoo_fragment)
        partial_header = (
            "<!-- RECOVERED PARTIAL 20260708: reconstructed from Codex log fragment "
            f"{aoo_fragment.relative_to(ROOT)}. The original file may have continued after "
            f"line {(meta.get('range') or ['', ''])[1]}. -->\n\n"
        )
        out_path = EA_DIR / "_recovered_partial" / "AOO.md"
        write_text(out_path, partial_header + body)
        partial.append(str(out_path.relative_to(ROOT)))

    return restored, partial


def assemble_partial_tex_fragments():
    partial_dir = EA_DIR / "_recovered_partial"
    reports = []
    tex_paths = [
        "core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en.tex",
        "core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh.tex",
    ]
    fragments = sorted((RECOVERY_DIR / "fragments").glob("*.txt"))

    for source_path in tex_paths:
        by_line = {}
        source_fragments = []
        for frag in fragments:
            meta, body = read_fragment(frag)
            if meta.get("source_path") != source_path:
                continue
            rng = meta.get("range")
            if not rng or len(rng) != 2:
                continue
            start, end = int(rng[0]), int(rng[1])
            order_key = (meta.get("output_log", ""), int(meta.get("output_line") or 0))
            source_fragments.append({"range": [start, end], "fragment": str(frag.relative_to(ROOT))})
            for offset, line in enumerate(body.splitlines(), start):
                if offset > end:
                    break
                old = by_line.get(offset)
                if old is None or order_key >= old[0]:
                    by_line[offset] = (order_key, line)

        if not by_line:
            continue

        out_lines = [
            "% RECOVERED PARTIAL 20260708",
            "% Reconstructed from Codex log sed/nl fragments.",
            "% Gaps below mark original line ranges not present in recovered logs.",
            "",
        ]
        missing_ranges = []
        last = max(by_line)
        line_no = 1
        while line_no <= last:
            if line_no in by_line:
                out_lines.append(by_line[line_no][1])
                line_no += 1
                continue
            gap_start = line_no
            while line_no <= last and line_no not in by_line:
                line_no += 1
            gap_end = line_no - 1
            missing_ranges.append([gap_start, gap_end])
            out_lines.append(f"% [RECOVERY GAP: original lines {gap_start}-{gap_end} not found in logs]")

        base = Path(source_path).name.replace(".tex", ".recovered_partial.tex")
        out_path = partial_dir / base
        write_text(out_path, "\n".join(out_lines) + "\n")
        reports.append(
            {
                "source_path": source_path,
                "partial_path": str(out_path.relative_to(ROOT)),
                "covered_lines": len(by_line),
                "last_recovered_line": last,
                "missing_ranges": missing_ranges,
                "source_fragments": source_fragments,
            }
        )

    if reports:
        write_text(partial_dir / "tex_fragment_coverage_20260708.json", json.dumps(reports, ensure_ascii=False, indent=2))
    return reports


def main():
    EA_DIR.mkdir(parents=True, exist_ok=True)
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)

    patches = extract_apply_patch_inputs()
    restored = []
    saved_patches = []
    update_patches = []
    for index, (log_path, lineno, patch) in enumerate(patches, 1):
        name = f"patch_{index:04d}_{safe_name(str(log_path.relative_to(Path('/home/ubuntu/.codex'))))}_L{lineno}.diff"
        patch_path = RECOVERY_DIR / "patches" / name
        write_text(patch_path, patch)
        saved_patches.append(str(patch_path.relative_to(ROOT)))
        restored.extend(restore_add_files_from_patch(patch))
        if "*** Update File: " in patch or "*** Delete File: " in patch:
            update_patches.append(str(patch_path.relative_to(ROOT)))

    outputs = parse_exec_calls_and_outputs()
    command_outputs, fragments, by_path = save_command_evidence(outputs)
    file_lists = collect_predelete_file_lists(outputs)
    restored_markdown, partial_markdown = restore_complete_markdown_fragments()
    tex_partial_reports = assemble_partial_tex_fragments()

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ea_prefix": EA_PREFIX,
        "recovery_source": [
            str(SESSION_ROOT),
            str(HISTORY),
        ],
        "restored_exact_files_from_add_file_patches": sorted(set(restored)),
        "saved_patch_files": saved_patches,
        "saved_update_or_delete_patch_files": update_patches,
        "saved_command_output_files": command_outputs,
        "saved_fragment_files": fragments,
        "saved_file_list_evidence": file_lists,
        "fragments_by_original_path": by_path,
        "restored_complete_markdown_from_fragments": restored_markdown,
        "restored_partial_markdown_from_fragments": partial_markdown,
        "assembled_partial_tex_reports": tex_partial_reports,
        "note": "Files restored from Add File patches are exact patch payloads. Fragments and update patches are evidence for partial/manual reconstruction.",
    }
    write_text(RECOVERY_DIR / "recovery_manifest_20260708.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    md = [
        "# balloon511_ea_latex_drafts Recovery Manifest",
        "",
        f"Generated UTC: {manifest['generated_at_utc']}",
        "",
        "This directory was reconstructed from Codex session/history logs after the untracked",
        "`core_md/balloon511_ea_latex_drafts/` directory was deleted.",
        "",
        "## Exact Restores",
        "",
    ]
    if restored:
        md.extend(f"- `{path}`" for path in sorted(set(restored)))
    else:
        md.append("- No complete Add File patch payloads were found.")
    md.extend(
        [
            "",
            "## Evidence Saved",
            "",
            f"- Patch files: {len(saved_patches)}",
            f"- Update/delete patch files: {len(update_patches)}",
            f"- Command outputs: {len(command_outputs)}",
            f"- Text fragments: {len(fragments)}",
            f"- File-list/status evidence files: {len(file_lists)}",
            f"- Complete markdown files restored from fragments: {len(restored_markdown)}",
            f"- Partial markdown files saved: {len(partial_markdown)}",
            f"- Partial TeX assemblies: {len(tex_partial_reports)}",
            "",
            "See `_recovery_logs/recovery_manifest_20260708.json` for the full index.",
        ]
    )
    write_text(EA_DIR / "RECOVERY_MANIFEST_20260708.md", "\n".join(md) + "\n")

    print(json.dumps({
        "restored_exact_files": len(set(restored)),
        "patches": len(saved_patches),
        "update_patches": len(update_patches),
        "command_outputs": len(command_outputs),
        "fragments": len(fragments),
        "file_lists": len(file_lists),
        "restored_markdown": len(restored_markdown),
        "partial_markdown": len(partial_markdown),
        "partial_tex": len(tex_partial_reports),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
