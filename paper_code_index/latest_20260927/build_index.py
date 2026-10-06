#!/usr/bin/env python3
"""Freeze selected manuscript code without running or changing original code."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
WORK = PROJECT / "paper_review_workspace_20260920"
PARENT = WORK / "outputs/00_parent"
GEO = PROJECT / "engineering/geometry_optimization_20260815"
ACT = PARENT / "activation_correction_20260924"
REPAIR = ACT / "production_repair_20260925"
OPT = WORK / "outputs/01_intro_geometry_optics/c_repair_20260920"
SIGNAL = WORK / "outputs/02_sources_response_compton/corrected_optics_signal_20260920"
EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
SOURCE_EXTENSIONS = {".py", ".sh", ".cc", ".cpp", ".c", ".hh", ".hpp", ".h", ".patch", ".cmake", ".geo", ".setup", ".det", ".source"}
SOURCE_LIMIT = 2 * 1024 * 1024
# Snapshot entire named code modules conservatively. This is not a per-file
# assertion that every helper was executed for the last manuscript revision.
MODULES = [
    ("publication", "末版正文、图表和检查", PARENT / "final_manuscript_20260926_activation/code"),
    ("editorial", "投稿文献样式构建", PARENT / "revision_20260927_ea_references/code"),
    ("editorial", "后续PAIRS蓝标版本构建", PARENT / "revision_20260927_pairs_blue/code"),
    ("figure_support", "末版仍调用的图样式", PARENT / "revision_20260921_AA_continuous/code"),
    ("figure_support", "末版仍调用的功能剖视与位置标记", PARENT / "revision_20260921_pro_figures_markers/code"),
    ("figure_support", "图1/2的结构绘制辅助", PARENT / "revision_20260921_3d_structure/code"),
    ("activation", "核链、响应归一化和环境重加权", ACT / "code"),
    ("activation", "定向补算的依赖结果代码", ACT / "targeted_response/final/code"),
    ("production_repair", "母核生产时间索引修复与库存重算", REPAIR / "code"),
    ("production_repair", "论文采用的最终响应与任务积分", REPAIR / "final/code"),
    ("runtime_patch", "逐核态响应与普通生产两个独立程序源码", REPAIR / "runtime"),
    ("runtime_patch", "此前明确核态及禁止重复子体排队的补丁源码", ACT / "targeted_response"),
    ("timeline", "信号/瞬时/延迟三路泊松时间轴", PARENT / "three_stream_poisson_20260921/code"),
    ("transport_aa", "最终Under-stage/AA生产、回放和信号响应", PARENT / "AA_run_20260921_v1/code"),
    ("transport_executor", "AA调用的工作副本8633执行器", EXECUTOR),
    ("geometry_aa", "最终AA几何生成", PROJECT / "engineering/mass_model_AA_20260921/code"),
    ("geometry_aa", "最终AA几何输入", PROJECT / "engineering/mass_model_AA_20260921/geometry"),
    ("geometry_aa", "实际AA运行的几何输入", PARENT / "AA_run_20260921_v1/geometry"),
    ("optics", "已发布修正光学、XOP对照与焦面导出", OPT / "code"),
    ("optics", "Geant4 Laue过程及CrystalKernel源码", OPT / "src"),
    ("signal_response", "修正光学焦面信号输运和像素几何判选", SIGNAL / "code"),
    ("signal_response", "输入清单绑定的几何（A为AA更新前的前驱，B为SH3）", SIGNAL / "geometry"),
    ("signal_response", "光学信号源卡", SIGNAL / "configs"),
    ("catalog_sh3", "侧置SH3的合并瞬时统计与事例目录", GEO / "70_m05_sg3_sh3_prompt_statistics_integration_20260828/code"),
    ("transport_support", "AA执行器使用的最小敏感体构建辅助", GEO / "68_sg3_minimal_sd_prompt_supplement_20260823/code"),
    ("environment", "最终图17采用的环境模型", GEO / "71_m05_sh3_environment_screening_20260830/code"),
    ("environment", "完整L2太阳活动模型（71的上游）", GEO / "65_sh3_complete_l2_solar_activity_20260820/code"),
    ("environment", "环境谱基础模型（65的上游）", GEO / "64_sh3_l2_environment_projection_20260820/code"),
    ("environment", "LEO谱模型辅助", PROJECT / "engineering/satellite_leo530_source_comparison_20260813/code"),
    ("environment", "月面谱模型辅助", PROJECT / "engineering/lunar_surface_source_comparison_20260813/code"),
    ("environment", "南极PARMA谱与任务重加权", PARENT / "antarctic_environment_20260924/code"),
    ("corrected_source", "corrected-keV源输入构建和验证", PROJECT / "engineering/particle_source_unit_repair_20260811/code"),
]
# These are named, bounded source/evidence inputs, not raw simulation data.
EXTRAS = [
    ("optics", OPT / "CMakeLists.txt"),
    ("response_rng", PROJECT / "engineering/particle_source_unit_repair_20260811/seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py"),
    ("evidence", PARENT / "LATEST_MANUSCRIPT_ZH.md"),
    ("evidence", PARENT / "final_manuscript_20260926_activation/README_ZH.md"),
    ("evidence", PARENT / "final_manuscript_20260926_activation/MACHINE_HANDOFF.json"),
    ("evidence", PARENT / "revision_20260927_pairs_blue/README_ZH.md"),
    ("evidence", REPAIR / "README_ZH.md"),
    ("evidence", REPAIR / "REPAIR_REVIEW_ZH.md"),
    ("evidence", REPAIR / "MACHINE_HANDOFF.json"),
    ("evidence", REPAIR / "data/final_validation.json"),
    ("evidence", REPAIR / "final/data/RESULTS.json"),
    ("evidence", REPAIR / "final/data/NUMERIC_COMPARISON_TWO_MODELS.csv"),
    ("evidence", REPAIR / "final/data/table3_delayed_replacement.csv"),
    ("evidence", REPAIR / "runtime/manifest.json"),
    ("evidence", REPAIR / "runtime/production/manifest.json"),
    ("evidence", OPT / "README_ZH.md"),
    ("evidence", OPT / "reports/release_manifest.json"),
    ("evidence", OPT / "paper_ready/focus_export_manifest.json"),
    ("evidence", SIGNAL / "README_ZH.md"),
    ("evidence", SIGNAL / "inputs_manifest.json"),
    ("evidence", PARENT / "three_stream_poisson_20260921/SOURCE_MANIFEST.json"),
    ("figure_input", PARENT / "activation_manuscript_proposal_20260926/FIG10_NEW_POSITIONS_a.csv"),
    ("figure_input", PARENT / "activation_manuscript_proposal_20260926/FIG10_NEW_POSITIONS_b.csv"),
    ("figure_input", WORK / "outputs/04_results_environments_conclusions/numeric_sync_20260920/data/parent_nuclide_figure_data.json"),
    ("figure_input", PARENT / "antarctic_environment_20260924/data/antarctic_native.csv"),
    ("evidence", PROJECT / "engineering/mass_model_AA_20260921/data/manifest.json"),
    ("evidence", EXECUTOR / "README.md"),
    ("executor_config", EXECUTOR / "config.json"),
]
SKIP_DIRECTORIES = {".git", "__pycache__", "node_modules", "build", "lib", "logs", "jobs", "generated", "data", "responses", "final"}
EXCLUDE_FILES = {"prune_events.py", "build_ppt0821_sh3_l2.py", "observe_detached.py", "observe_bounded.py", "write_continuation_report.py"}
SECRET_PATTERN = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(PROJECT), *args], env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, text=True).strip()


def label(path: Path) -> str:
    try:
        return "project/" + path.relative_to(PROJECT).as_posix()
    except ValueError:
        return "external/worktree_8633/tool/execute/" + path.relative_to(EXECUTOR).as_posix()


def freeze(path: Path, group: str, files: dict, excluded: list) -> None:
    if not path.is_file():
        excluded.append({"path": str(path), "reason": "missing_or_broken_link"})
        return
    if path.stat().st_size > SOURCE_LIMIT:
        excluded.append({"path": str(path), "reason": "exceeds_2MiB_source_limit"})
        return
    data = path.read_bytes()
    if SECRET_PATTERN.search(data):
        raise RuntimeError(f"Potential credential in selected source; nothing may be pushed: {path}")
    if path.suffix == ".py":
        ast.parse(data.decode("utf-8-sig"), filename=str(path))
    key = label(path)
    destination = OUT / "snapshot" / key
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError(f"Refusing to overwrite an existing snapshot: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_bytes(data)
    executable = bool(path.stat().st_mode & 0o111)
    destination.chmod(0o755 if executable else 0o644)
    entry = files.setdefault(key, {"source_path": str(path), "resolved_source": str(path.resolve()), "snapshot_path": "snapshot/" + key, "bytes": len(data), "sha256": digest(data), "executable": executable, "groups": []})
    if group not in entry["groups"]:
        entry["groups"].append(group)
    if path.is_symlink():
        entry["original_symlink_target"] = os.readlink(path)


def main() -> None:
    if git("diff", "--cached", "--name-only"):
        raise RuntimeError("Index must start empty; do not include pre-existing staged work")
    files: dict = {}
    excluded: list = []
    modules = []
    for group, description, directory in MODULES:
        if not directory.is_dir():
            excluded.append({"path": str(directory), "reason": "module_directory_missing"})
            continue
        count_before = len(files)
        for root, dirs, names in os.walk(directory):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRECTORIES)
            for name in sorted(names):
                path = Path(root) / name
                if name in EXCLUDE_FILES:
                    excluded.append({"path": str(path), "reason": "cleanup_monitor_or_nonpaper_auxiliary"})
                    continue
                if path.suffix in SOURCE_EXTENSIONS or name == "CMakeLists.txt":
                    freeze(path, group, files, excluded)
        modules.append({"group": group, "description_zh": description, "original_directory": str(directory), "new_files": len(files) - count_before})
    for group, path in EXTRAS:
        freeze(path, group, files, excluded)
    numeric_directory = PARENT / "final_manuscript_20260926_activation/data"
    for path in sorted(numeric_directory.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".csv"} and path.stat().st_size <= 256 * 1024:
            freeze(path, "paper_numeric_input", files, excluded)
    identity = []
    for role, path in [("official_latest_tex", PARENT / "EA_submission_20260927_data_availability/paper_clean.tex"), ("official_latest_pdf", PARENT / "EA_submission_20260927_data_availability/paper_clean.pdf"), ("later_pairs_blue_tex", PARENT / "revision_20260927_pairs_blue/paper_pairs_blue.tex")]:
        data = path.read_bytes()
        identity.append({"role": role, "path": str(path), "bytes": len(data), "sha256": digest(data), "bundled": False})
    disk = Path("/media/ubuntu/903261CE3261BA3C")
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_project": str(PROJECT),
        "base_head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "scope": "Versioned code index and source snapshot; not a complete independently runnable reproduction package",
        "selection": "Verified manuscript entry points plus conservative module-level supporting sources; no claim that every helper ran for the final revision",
        "manuscripts": identity,
        "modules": modules,
        "files": sorted(files.values(), key=lambda r: r["snapshot_path"]),
        "excluded_or_unavailable": excluded,
        "external_data": [{"path": str(disk / "TES_Balloon_511_data"), "mountpoint_exists_at_index_time": disk.exists(), "bundled": False, "note": "Raw SIM, production/activation inputs, responses and original receipts must be retained separately"}],
        "not_bundled": ["Raw SIM/DAT, NPY/NPZ/PKL, runtime logs and executable binaries", "Manuscript body, PDF and figure files (identified by hashes, not newly published)", "Third-party MEGAlib/Geant4/ROOT and XOP/xoppylib/xraylib/DABAX/crystalpy installations", "Other dirty files, historical paper revisions and unrelated worktrees"],
        "checks": {"python_source_ast_parse": "PASS", "credential_pattern_scan": "PASS", "physics_or_build_executed": False, "source_files_modified": False},
    }
    (OUT / "INDEX.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    tsv = ["group\tbytes\tsha256\tsnapshot_path\toriginal_path"]
    for row in manifest["files"]:
        tsv.append("\t".join([",".join(row["groups"]), str(row["bytes"]), row["sha256"], row["snapshot_path"], row["source_path"]]))
    (OUT / "SOURCES.tsv").write_text("\n".join(tsv) + "\n")
    print(json.dumps({"files": len(files), "source_bytes": sum(r["bytes"] for r in files.values()), "modules": len(modules), "excluded": excluded}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
