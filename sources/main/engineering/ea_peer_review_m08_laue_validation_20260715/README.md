# EA 同行评审 M08：Laue 单晶片验证包

状态：`PARTIAL_PASS`

本目录补齐同行评审 M08 要求的三项证据：固定单晶片的 `R/T/A` 角度—能量扫描、
Geant4 晶体最大步长收敛、mosaic 出射角/焦斑的独立验证。它是 2026-07-15
新建的审计包，不覆盖 `stepwise_maintenance/step04_opticsim/` 的权威运行，也没有
修改 `/home/ubuntu/opticsim` production worktree。

## 结论

- 65 点 `R/T/A` 扫描完成：5 个能量、每能量 13 个角点、每点 20,000 个光子；
- `R` 在 65/65 点通过，最大 `|Geant4-XOP|=0.01732`；完整 `R/T/A` 仅
  29/65 点通过，原因是 Geant4 标准 EM 与 XOP 衰减参考产生最高 3.75 个百分点的
  `T/A` 系统差；
- unlimited/5/1/0.2 mm 四档步长结果逐事例一致，步长收敛通过；
- 当前 production 等价的 `gaussian_plane` 点源 `d90=0.406226 cm`，比缩放到
  10 m 的 HEART 2.1.3 参考宽 51.93%；
- 候选 `gaussian_outgoing` 得到 `d90=0.265752 cm`，与解析 30 arcsec 2D
  高斯相差 +0.26%，与 HEART 相差 -0.61%，通过双重独立门；
- 18 mm footprint 下 Be 门内比例从 0.99823 变为 0.99873，因此旧 `A_eff`
  数值变化很小，但 production 出射角抽样仍需修正并重跑三种子焦面源。

完整中文报告见 [reports/M08_VALIDATION_REPORT_ZH.md](reports/M08_VALIDATION_REPORT_ZH.md)，
机器可读裁决见 [reports/audit_summary.json](reports/audit_summary.json)。

## 冻结输入与软件

- 上游 opticsim commit：`68f5e6717b101569a2896a3c1a1bcf945cb7c23a`；
- 冻结的上游相关源文件在 `source/`，其 M08 审计扩展只存在于本目录；
- Geant4：11.4.0；编译器：GCC 11.4.0；
- XOP 参考：CRYSTAL diff_pat v1.8、xoppylib 1.0.55、DABAX 1.0.12；
- HEART 独立参考：2.1.3 保留 oracle；
- 晶片：Ge(111)，`d=3.266590088 Å`，厚 10.218801 mm，边长 18 mm；
- 焦距：10,000 mm；mosaic FWHM：30 arcsec；Be 门半径：18.98 mm。

原始五能量 XOP 曲线及其 SHA-256 在 `data/input_manifest.json`。因为保留曲线原先
使用各能量的优化厚度，`code/prepare_inputs.py` 先反解同一 Darwin-Hamilton slab
系数，再把各曲线严格换算到固定 10.218801 mm；不拟合或移动峰位/宽度。

关键哈希：

- 验证源 `laue_multiring_bfull_demo.cc`：
  `136e11bd098d242a30cd693b716d7697a702a807617645025463f903b1f53c88`；
- 输入清单：
  `65ef53831312fc45241a3cd867ce4e16ca4b39df776abaabf8dbb1b9023e8973`；
- 裁决 JSON：
  `ddda842a0e0b92ef262984effedfc88529258bcd6aed28017f111032662499c1`；
- 本轮编译二进制：
  `dfd5191ad491962dfb7484b533c97d2994fa68023f2279b96fe21d3d78e72642`。

## 可复现命令

从仓库根目录运行：

```bash
python3 engineering/ea_peer_review_m08_laue_validation_20260715/code/prepare_inputs.py

/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh \
  cmake -S engineering/ea_peer_review_m08_laue_validation_20260715/source \
  -B /tmp/ea_m08_bfull_build_20260715 -DCMAKE_BUILD_TYPE=Release

/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh \
  cmake --build /tmp/ea_m08_bfull_build_20260715 --parallel 8

/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh \
  python3 engineering/ea_peer_review_m08_laue_validation_20260715/code/run_validation.py \
  --section all --jobs 8

python3 engineering/ea_peer_review_m08_laue_validation_20260715/code/analyze_validation.py
```

`outputs/` 保留 75 个 Geant4 原始运行：65 个 `R/T/A` 点、4 个步长点和 6 个
mosaic 模型/footprint 点。每个运行目录含命令与种子的 `run_metadata.json`、完整
`run.log`、`summary.json`、焦面/透射/历史 CSV。

## 产物索引

- `reports/rta_angle_energy_scan.csv`：65 点逐点 XOP—Geant4 `R/T/A`；
- `reports/step_convergence.csv`：四档步长与实际最大步长；
- `reports/mosaic_outgoing_comparison.csv`：三种出射模型、点源/18 mm footprint；
- `reports/audit_summary.json`：验收门、极值和 M08 总裁决；
- `reports/M08_VALIDATION_REPORT_ZH.md`：可直接用于修复日志/同行评审答复的中文报告。

## 销项条件

1. production opticsim 用 `gaussian_outgoing` 或经验证的条件微晶取向模型替代
   `gaussian_plane`；
2. 重跑 f10m A1/R2 三种子与下游焦面 EventList；
3. 统一 XOP/Geant4 衰减口径，或把最大 3.75 个百分点 `T/A` 差作为响应系统误差；
4. 冻结 production commit/patch 后再把 M08 从 `PARTIAL_PASS` 改为 `PASS`。
