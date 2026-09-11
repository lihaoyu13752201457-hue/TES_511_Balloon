from pathlib import Path
import json
import shutil
import sys
import platform
import importlib.metadata
from collections import Counter

ROOT = Path('/tmp/tes511-paper-backup-stage-20260911')

def write(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + '\n', encoding='utf-8')

def main():
    entries = [json.loads(s) for s in (ROOT/'manifests/files.jsonl').read_text().splitlines()]
    roots = json.loads((ROOT/'manifests/source_roots.json').read_text())
    unique = {e['archive_path']: e for e in entries}
    code = [e for e in unique.values() if e['role']=='program_source']
    total = sum(e['bytes'] for e in unique.values())
    env = {'python': sys.version, 'platform': platform.platform(), 'packages': {},
           'note': 'Observed backup-host versions; original production runtime provenance is retained separately.'}
    for name in ['numpy','scipy','pandas','matplotlib','Pillow','pytest','astropy','uproot']:
        try: env['packages'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: env['packages'][name] = None
    write('manifests/backup_host_environment.json',json.dumps(env,indent=2))
    write('README.md',f'''# TES 511 keV 论文与代码备份 · 2026-09-11

本目录保存 2026-08-31 最终英文稿及其代码依赖快照。论文研究球载 Laue 透镜 + TES 望远镜的 511 keV 点源灵敏度、瞬发与活化本底，以及由近场材料来源分析驱动的探测器结构优化。

- **最终正文和 PDF**：[paper/](paper/)，含正文直接使用的 16 个 PDF 配图，可独立编译。
- **代码**：[sources/](sources/)，包括主项目未提交文件、15 个历史工作树的代码差异、光学程序、独立光学校验、PARMA 粒子源驱动与系数表、实际安装的 MEGAlib 源码和记录钩子；另保留 neutron_fen 后续研究代码。
- **规模**：{len(code):,} 个实际保存的程序源文件；快照源文件、配置、文档及论文合计 {len(unique):,} 个文件、{total/2**20:.1f} MiB，另有清单和备份工具。
- **溯源**：[manifests/files.jsonl](manifests/files.jsonl) 逐文件记录原路径、保存路径、SHA-256；[source_roots.json](manifests/source_roots.json) 记录各仓库原 HEAD 和工作区状态。
- **恢复**：[RESTORE.md](RESTORE.md)；**代码导航**：[CODE_MAP.md](CODE_MAP.md)；**论文主题与版本边界**：[PAPER_TOPIC.md](PAPER_TOPIC.md)。

这是独立的根提交，备份分支为 `codex/paper-code-backup-20260911`，使用原项目远端 `https://github.com/lihaoyu13752201457-hue/TES_511_Balloon.git`。原仓库工作区、分支和历史未迁移或修改。

大型 SIM、逐事件目录、NPZ/NPY、活化展开采样列表、编译产物、软件安装环境和旧 Git 历史未复制。**这是论文与代码备份；完整物理重算还需要原始数据及相应软件环境。** 小型几何、谱表、输入配置和结果摘要按清单保留，详见 [DATA_NOT_INCLUDED.md](DATA_NOT_INCLUDED.md)。

历史脚本按原字节保存，可能含原机器绝对路径。不能将不同工作树版本混合执行，也不能把历史源单位错误或旧结果恢复成当前物理依据。恢复工具先重建各自的来源目录；路径迁移须在单独工作副本中进行。

```bash
python3 tools/verify_snapshot.py
python3 tools/verify_snapshot.py --latex
```
''')
    write('PAPER_TOPIC.md','''# 论文主题与最终版本

**题名**：Monte Carlo simulation of background and 511-keV point-source sensitivity for a balloon-borne Laue-lens TES telescope.

研究链：Laue 聚焦光子 → Geant4/MEGAlib 输运 → 瞬发粒子与活化衰变 → TES 响应 → 反符合与 Compton 选择 → 共同时间轴 → 任务期本底积分和顶层大气点源灵敏度。

正文比较 mass model A（SG3B 参考构型）和 mass model B（SH3 OptV3 侧向 chimney 构型），利用选中活化事件的材料、部件、母核素来源来解释结构优化的效果。

本备份的最终版本是 `balloon511_ea_manuscript_en_20260831.tex`，采用固定 **27° 仰角** 的任务期折叠。`tmp/m05_issue9_fixed27_20260831/` 中的代码是最终任务性能和环境外推图表的入口。较早 45° 版本的结果属于上游中间状态，不能代替最终值。

最终稿报告：模型 B 的 day-15 本底约 1.07e-2 s^-1，20 d 条件下的 3σ 线通量阈值约 (3.09 ± 0.28)e-5 ph cm^-2 s^-1，模型 A/B 阈值比约 2.23。

本备份保存现有最终稿的科学口径，不进行结果订正。P70 的当前主链采用去线 gamma continuum，独立 atm511 分支关闭；完整大气 511 线闭合、有限统计和探测器响应仍应按原报告区分。2026-09-11 复核见 `sources/main/engineering/manuscript_gap_review_20260911/`。

`paper/history/` 中 2026-08-21 命名的前稿仅用于版本核对。`sources/` 内其他论文草稿、旧构型和历史代码用于溯源；`neutron_fen` 是后续低温响应研究，不能当作本论文已完成的探测器响应验证。
''')
    write('CODE_MAP.md','''# 代码导航

下列相对路径均相对于恢复后的来源根目录。主项目入口通常在 `sources/main/`；历史工作树采用差异存储，**缺少实体副本不代表代码未保存**，须用 `manifests/files.jsonl` 或恢复工具查看该来源的完整集合。

| 环节 | 主要代码位置 |
|---|---|
| 最终 27° 重算与论文图表 | `tmp/m05_issue9_fixed27_20260831/build_fixed27_paper_assets.py`、同目录 `build_environment_screening_fixed27.py` 与三个来源饼图脚本 |
| 最终英文稿与中间 45° 图表 | `tmp/m05_environment_extension_20260830/build_clean_english_manuscript_20260831.py`、`build_section4_reference_flux_20260830.py`、`figure_revision_r19/`、`figures/` |
| 最终章节与几何绘图 | `core_md/balloon511_ea_latex_drafts/M05NEW/`；`tmp/m05_environment_extension_20260830/figures/` |
| A/B 正式统计整合、共同时间轴、不确定度 | `engineering/geometry_optimization_20260815/70_m05_sg3_sh3_prompt_statistics_integration_20260828/code/` |
| P70 调用的 flux-closed timeline | 来源 `worktree_ebb2`：`engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/code/run_fluxclosed_timeline.py` |
| SG3B/SH3 几何、信号与背景分析 | 各来源 `engineering/geometry_optimization_20260815/` 下 P56–P70；`DEEPSEEK_CODE/modified/` |
| TES 响应与 Compton 选择 | `DEEPSEEK_CODE/modified/build_event_catalog_sh3_step05.py`、`step05_side_compton.py`；`old/code/tools/build_v3p5_centerfinger_step05_l1_response.py` |
| 修正 keV 粒子源、输运、活化、紧凑记录与钩子 | `engineering/particle_source_unit_repair_20260811/` 中代码、源契约、谱表和配置；`code/tools/` |
| PARMA 粒子源上游 | 来源 `codex_tes_511_sim`：`COSMOSRAY_BALLOON_SIM/tools/phase2_parma_grid_driver.cpp`、`external/expacs_parma/parma_cpp/` 及系数表；也保留 Fortran 实现 |
| 环境比较 | P71 `code/build_environment_screening.py` 及 P64/P65；`engineering/environment_response_projection_20260813/`、卫星/月面环境包 |
| Laue 光学 Geant4 实现 | 来源 `opticsim`：`opticsim_full/geant4_app/src/laue_multiring_bfull_demo.cc`、相应 headers、CMake、config、analysis；`external_baseline/` |
| 光学独立校验与补丁 | 来源 `cross_check_laue`：`laue511_validation/` 与根目录 `.patch` 文件 |
| 聚焦光子到 Cosima 的桥接 | `stepwise_maintenance/step09_optics_bridge/` 及光学/独立校验中的转换代码 |
| 实际安装的 Cosima/MEGAlib 实现 | 来源 `megalib`：`src/`、`config/`、安装脚本、补丁及相关模板；含 MCSource、MCEventAction、MCSteppingAction、MCRun、MCIsotopeStore |
| 后续低温响应研究 | 来源 `neutron_fen`：源代码、配置和依赖说明；属于补充研究 |

为防止动态加载、跨工作树导入或临时作图脚本遗漏，保留了这些来源中的更广泛程序源码集合。原代码没有为本次备份修改；因此历史算法、已弃用入口和实验脚本也在快照中，具体入口要以最终稿链条为准。

原始源码的绝对引用统计见 `manifests/external_project_references.json`。该表包含历史和可选工具引用，不等同于最终论文的必需依赖清单。对论文关键入口的备份覆盖检查见 `manifests/critical_code_coverage.json`。
''')
    write('DATA_NOT_INCLUDED.md','''# 未复制的数据与软件环境

按用户要求，备份保留代码和小型支持文件，排除大体积数据。没有启动输运或读取大型模拟事件内容。

- 不复制 `.sim`、ROOT、NPZ/NPY、HDF5、FITS、压缩事件归档和大型事件目录。
- 不复制 `runs/` 中逐任务核素 DAT、展开后的活化位置采样卡及其他批次中间产物；少量顶层审计摘要保留。
- 不复制编译目录、可执行文件、共享库、Python 虚拟环境、Geant4 数据库或旧 `.git` 历史。
- 不复制外接数据盘中的生产数据，也不建立指向原数据盘的 Git 子模块或软链接。
- 最终稿的 16 个配图 PDF 是论文必需资源，已保留；其他生成图片通常不保留。
- 小型几何、修正源谱、配置、CSV/JSON 汇总和文档按清单保留。大 JSON、CSV/DAT 与生成源卡受大小限制；具体排除路径和原因见 `manifests/excluded_files.jsonl`。

排除清单记录的是本次遍历发现的文件，并非所有软件安装目录或外接数据盘的完整目录。被整体跳过的 build、install、环境和隐藏目录不逐文件展开。各历史工作树可能引用同一份数据，清单的逻辑字节总和不应作为本机独立数据的占用量。

要重做完整物理模拟，需要恢复原始事件/活化输入，安装原记录要求的 MEGAlib、ROOT、Geant4 和核数据库，并按 source/inventory provenance、TT、几何头、随机种子和验证记录闭合。代码快照不替代这些输入。

安装权威与历史哈希记录保存在 `sources/main/engineering/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/external_sources.json`：生产 Cosima 记录为 MEGAlib 4.02.00 / Geant4 10.02.p03。光学项目另有 Geant4 11.4 的启动脚本，不应将两套环境混用。PARMA 的 `input/` 系数表（包括算法读取的 `.out` 输入文件）已显式保留。通用第三方依赖按版本重新安装；已在项目树内的定制源码、补丁和 MEGAlib 源码已随快照保存。
''')
    write('RESTORE.md','''# 检查与恢复

## 获取独立备份分支

```bash
git clone --single-branch --branch codex/paper-code-backup-20260911 \
  https://github.com/lihaoyu13752201457-hue/TES_511_Balloon.git TES_511_Paper_Backup
cd TES_511_Paper_Backup
python3 tools/verify_snapshot.py
```

该分支有独立根提交；使用 single-branch 克隆可避免下载其他分支的大型历史。

## 编译最终正文

需要 XeLaTeX 和 TeX Gyre Termes 字体。正文参考文献内嵌，无需 BibTeX。

```bash
python3 tools/verify_snapshot.py --latex
```

此命令在临时目录进行两遍编译，不覆盖保留的原始 PDF。输出与原稿的逐字节一致性不作保证，因为 TeX 版本、时间戳和字体环境可能不同。

## 重建原来源目录的代码集合

```bash
python3 tools/materialize_sources.py --list
python3 tools/materialize_sources.py --root-id main --destination /tmp/tes511-restored-main
python3 tools/materialize_sources.py --root-id worktree_ebb2 --destination /tmp/tes511-restored-ebb2
python3 tools/materialize_sources.py --root-id opticsim --destination /tmp/tes511-restored-opticsim
```

恢复工具按该来源的逐文件清单解析共享副本并核对 SHA-256，只写入**新建的空目标目录**。不会将当前主目录额外文件混入旧工作树，也不会覆盖原仓库。

归档内的程序、配置保持原字节，不直接替换 `/home/ubuntu/TES_511_Balloon` 或历史工作树的绝对路径。重新执行前，在独立工作副本中按 `manifests/source_roots.json` 映射这些路径并准备数据。P70 对 ebb2/P67 的动态导入尤其需要保留来源对应关系。

备份时未执行完整模拟或改动物理代码。哈希校验、关键代码覆盖和论文编译通过，只说明备份完整性与稿件资源可用，不表示缺失的大数据输入已经恢复。
''')
    write('.gitignore','''# Keep future generated simulation/build products out of this source snapshot.
*.sim
*.sim.gz
*.npz
*.npy
*.root
*.h5
*.hdf5
*.pyc
__pycache__/
.venv/
node_modules/
*.aux
*.log
*.xdv
*.fls
*.fdb_latexmk
*.synctex.gz
/restored/
/local_runs/
''')
    write('tools/materialize_sources.py',r'''
#!/usr/bin/env python3
"""Materialize exactly one source-root inventory, resolving shared main copies."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[1]

def safe_relative(value):
    p = Path(value)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError(f'Unsafe relative path: {value}')
    return p

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list', action='store_true')
    p.add_argument('--root-id')
    p.add_argument('--destination', type=Path)
    args = p.parse_args()
    entries = [json.loads(s) for s in (BASE/'manifests/files.jsonl').read_text().splitlines()]
    ids = sorted(set(e['root_id'] for e in entries))
    if args.list:
        print('\n'.join(ids)); return
    if args.root_id not in ids or args.destination is None:
        p.error('--root-id must exist and --destination is required')
    selected = [e for e in entries if e['root_id']==args.root_id]
    for e in selected:
        source = BASE/safe_relative(e['archive_path'])
        safe_relative(e['relative_path'])
        if hashlib.sha256(source.read_bytes()).hexdigest()!=e['sha256']:
            raise RuntimeError(f'Hash mismatch: {source}')
    dest = args.destination.expanduser().absolute()
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(f'Destination must not already exist: {dest}')
    dest.mkdir(parents=True, exist_ok=False)
    for e in selected:
        target = dest/safe_relative(e['relative_path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE/safe_relative(e['archive_path']), target)
    print(json.dumps({'root_id':args.root_id,'files':len(selected),'destination':str(dest)}))

if __name__=='__main__': main()
''')
    write('tools/verify_snapshot.py',r'''
#!/usr/bin/env python3
"""Verify archived bytes, critical-code coverage, and optional paper compilation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--latex', action='store_true')
    args = p.parse_args()
    entries = [json.loads(s) for s in (BASE/'manifests/files.jsonl').read_text().splitlines()]
    unique = {e['archive_path']:e for e in entries}
    errors = []
    for name,e in unique.items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:
            errors.append('unsafe manifest path: '+name); continue
        f=BASE/rel
        if not f.is_file() or f.is_symlink():
            errors.append('missing file or symlink: '+name); continue
        raw=f.read_bytes()
        if len(raw)!=e['bytes'] or hashlib.sha256(raw).hexdigest()!=e['sha256']:
            errors.append('hash/size mismatch: '+name)
        if f.suffix.lower() in {'.sim','.npz','.npy','.root','.h5','.hdf5'} or len(raw)>25*2**20:
            errors.append('unexpected large data artifact: '+name)
    coverage=json.loads((BASE/'manifests/critical_code_coverage.json').read_text())
    if any(not e['present'] for e in coverage['files']):
        errors.append('missing critical program source')
    originals={e['original_path'] for e in entries}
    if any(e['original_path'] not in originals for e in coverage['files']):
        errors.append('critical coverage entry absent from inventory')
    tex=BASE/'paper/balloon511_ea_manuscript_en_20260831.tex'
    figures=re.findall(r'\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex.read_text())
    # Match the literal LaTeX command, not a regex escape.
    figures=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex.read_text())
    if len(figures)!=16 or any(not (tex.parent/f).is_file() for f in figures):
        errors.append('paper figure inventory is incomplete')
    if errors:
        print(json.dumps({'status':'FAIL','errors':errors},indent=2)); raise SystemExit(1)
    result={'status':'PASS','logical_entries':len(entries),'physical_snapshot_files':len(unique),
            'program_files':sum(e['role']=='program_source' for e in unique.values()),
            'snapshot_bytes':sum(e['bytes'] for e in unique.values()),'paper_figures':len(figures),
            'critical_code_files':len(coverage['files'])}
    if args.latex:
        exe='/usr/bin/xelatex' if Path('/usr/bin/xelatex').exists() else shutil.which('xelatex')
        if not exe: raise RuntimeError('XeLaTeX is required for --latex')
        with tempfile.TemporaryDirectory(prefix='tes511-paper-compile-') as td:
            for _ in range(2):
                r=subprocess.run([exe,'-interaction=nonstopmode','-halt-on-error',f'-output-directory={td}',tex.name],
                                 cwd=tex.parent,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                if r.returncode:
                    print(r.stdout[-10000:]); raise SystemExit(r.returncode)
            pdf=Path(td)/tex.with_suffix('.pdf').name
            if not pdf.is_file(): raise RuntimeError('No compiled PDF')
            log=(Path(td)/tex.with_suffix('.log').name).read_text(errors='replace')
            if 'undefined references' in log or 'undefined citations' in log:
                raise RuntimeError('Unresolved LaTeX references or citations')
            result['latex']={'status':'PASS','passes':2,'compiled_bytes':pdf.stat().st_size,
                             'original_pdf_overwritten':False}
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
''')
    # Remove accidental redundant regex before execution.
    verify = ROOT/'tools/verify_snapshot.py'
    v=verify.read_text()
    v=v.replace("    figures=re.findall(r'\\includegraphics(?:\\[[^\\]]*\\])?\\{([^}]+)\\}',tex.read_text())\n",'')
    verify.write_text(v)
    shutil.copy2('/tmp/collect_tes511_paper_backup_20260911.py',ROOT/'tools/collect_snapshot_original.py')
    shutil.copy2('/tmp/tes511_original_worktree_before_backup.json',ROOT/'manifests/original_worktree_before_backup.json')
    for p in (ROOT/'tools').glob('*.py'): p.chmod(0o755)
    print(json.dumps({'physical_snapshot_files':len(unique),'program_files':len(code),'bytes':total,'roots':len(roots)}))

if __name__=='__main__':main()
