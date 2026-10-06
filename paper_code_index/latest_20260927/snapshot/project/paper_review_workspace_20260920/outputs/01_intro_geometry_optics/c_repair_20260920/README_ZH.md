**Laue511独立修正发布包**

先看[结论、设计理由和对照](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/01_intro_geometry_optics/c_repair_20260920/REPORT_ZH.md)。本目录是独立的、511 keV概念设计光学实现，不覆盖原opticsim、M08或论文。所有原始正式运行已保留；不要在此目录重复启动全套输运。

依赖：C++17、CMake、Geant4 11.4.0；分析使用Python、NumPy、SciPy、pandas、Matplotlib。精确安装版本和源码/输入/二进制SHA-256记录在`MACHINE_HANDOFF.json`与`reports/release_manifest.json`。运行时只需Geant4和本包`inputs/corrected_physics.dat`，不需联网，也不需运行XOP。`legacy`对照另需旧曲线。

源文件职责：

- `src/CrystalKernel.hh`：受控物理输入、厚度独立局部率、条件Bragg抽样、历史对照曲线。
- `src/laue511.cc`：Geant4离散过程、无重叠几何、单片/整环源、独立能量/出口/焦面记录。
- `src/kernel_check.cc`：固定五个入射角的运动学核样本。
- `code/build_reference.py`：精确版本XOP参考重建及独立Q核验。依赖此前诊断包保留的xoppylib1.0.55/DIFF_PAT和本机xraylib4.2.1、DABAX1.0.12；不会隐式安装或下载。拒绝覆盖参考目录。
- `code/run_suite.py`：冻结的42项矩阵及4项预检；每个运行保存完整命令和哈希，拒绝覆盖运行目录。
- `code/analyze_suite.py`、`reference_audit.py`、`geometry_report.py`：只读已有事件/参考，生成分析表与图。分析器会更新本目录派生报告，不改变原始事件。
- `code/release_checks.py`：最后观察器更改的4次同种子重放与非法配置测试；现有重放已完成，拒绝覆盖。
- `code/export_focus.py`：仅汇合相同新几何/物理的3个独立种子，按18.98 mm孔径导出，附输入数量、投影面积与哈希。

本机编译示例（已有编译结果；按需才执行）：

```bash
cd /home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/01_intro_geometry_optics/c_repair_20260920
/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh cmake --build build --parallel 2
```

跨机器先按当地Geant4安装设置`CMAKE_PREFIX_PATH`及运行环境；编译本包CMake即可，不依赖本机包装器代码。执行时传绝对物理输入和一个**尚不存在**的输出目录。例子只是接口说明，本轮没有自动执行这一额外种子：

```bash
# 下述路径位于本任务独占目录；示例保留种子92029990，尚未运行。
/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh \
  ./build/laue511 --model dh --physics combined --geometry ring25cut \
  --data ./inputs/corrected_physics.dat --n 50000 --seed 92029990 \
  --thickness 10.218801 --step 1 --gap 0.2 --out ./runs/example_92029990
```

参数单位：`thickness/step/gap`为mm，`offset`为arcsec，`mu-loss`为cm⁻¹。`--step 0`取消最大光子步长；`--point`关闭18 mm足迹；`--check-only`只初始化及检查几何。输出上限1,000,000初级/次，仅为有界运行保护。旧重叠环`legacy25`必须显式传`--allow-invalid-legacy`，不能将其标记为新几何有效运行。

物理模式：`combined`为局部Laue加标准EM；`laue_only`为纯衍射；`loss`为Laue加已知均匀终止系数；`em_only`为标准EM。模型`dh`是推荐实现；`legacy`和`input_only`仅服务因果对照。默认只对能量511±10⁻⁶ keV的光子启用新衍射；降能光子保留标准EM。不得拿本包直接声称覆盖480–550 keV。

只重新分析已存数据，无新输运：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 code/analyze_suite.py
PYTHONDONTWRITEBYTECODE=1 python3 code/reference_audit.py
PYTHONDONTWRITEBYTECODE=1 python3 code/geometry_report.py
PYTHONDONTWRITEBYTECODE=1 python3 code/export_focus.py
```

CSV契约：`events.csv`以入射事件为单位；`exits.csv`记录所有晶体表面出射粒子；`focal.csv`记录世界中z=10000 mm的gamma过面；`diffractions.csv`记录每次衍射。R_clean/T_coherent分别为无EM的奇/偶次衍射束，T_uncollided为零衍射且无EM。其它gamma和无gamma不能合称光电吸收。坐标mm、能量keV、方向无量纲。焦面有效面积按每事件截获光子数的样本均值乘真实投影面积，SE从逐事件计数计算；本次每个入射最多一个被接受光子。

整环源均匀抽取每片截面、晶片等权分配；每片面积相等。所有正式对照为独立新种子，配对步长组除外；不同几何/模型从不合池。焦斑表的分位数为各种子分位数的均值，不是其二阶矩。所有统计误差不含晶体系统不确定度。

正式矩阵使用`build/suite_version/laue511`归档二进制（SHA前缀435e3b8b）；当前发布版`build/laue511`（1fd7c854）仅增加gamma步长观察器并格式化。四组发布配对CSV逐字相同，证明对这些验收案例数值输出未变。预检的早期二进制在`build/smoke_version/`，不冒充最终版本。

[论文候选TeX](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/01_intro_geometry_optics/c_repair_20260920/paper_ready/optics_methods.tex)与[独立PDF](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/01_intro_geometry_optics/c_repair_20260920/paper_ready/REPAIR_NOTE_ZH.pdf)可审阅；正式论文合入和下游响应更新尚未执行。完整数据不会因本README中的复现示例自动重跑。
