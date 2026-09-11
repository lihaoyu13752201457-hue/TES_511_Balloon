# 01 annotated code commentary

## Table builder side

```text
bragg_angle_rad()
  输入 E_keV 和 d_spacing_A，输出 theta_B。
  如果 lambda/(2d) 不在 (0,1)，立即报错，避免生成物理上不可能的 ring。

darwin_mosaic_probabilities()
  计算 mosaic 权重 w(delta_theta)，再得到 coherent sigma。
  p_abs 来自吸收透过率，p_diff 来自 Darwin mosaic diffraction efficiency * absorption transmission。
  最后把 p_diff + p_abs + p_trans 重新归一化，保证 Geant4 抽样是三分支概率。

_write_table()
  对每个 ring 的 design energy 扫描 delta_theta 网格。
  每个网格点写一行 E, theta_B, delta_theta, material, hkl, thickness, p_diff, p_abs, p_trans。
```

## Geant4 side

```text
MultiRingProcess::PostStepDoIt()
  1. 只处理 primary gamma。
  2. 只在 fGeomBoundary 且 volume 名含 LaueCrystal 时触发。
  3. 用 copyNo 找 ring 和 tile。
  4. 用 thetaLocal - thetaB 得到 deltaTheta。
  5. 查 LaueEfficiencyTable，得到 pAbs/pDiff/pTrans。
  6. 随机数 u < pAbs：吸收，kill track。
  7. u >= pAbs + pDiff：透过，kill track，并写 transmitted_space。
  8. 否则：生成一个二次 gamma 指向焦平面，写 phase_space。
```

## 这段代码最容易错在哪里

- ring 半径不是任意输入，必须和 `F tan(2 theta_B)` 对齐。
- `p_diff` 不是固定常数；它随 ring energy 和 `delta_theta` 变。
- Geant4 里 primary gamma 被 kill，衍射支路用 secondary gamma 表示，后续要读 `phase_space.csv` 而不是追原 track。
