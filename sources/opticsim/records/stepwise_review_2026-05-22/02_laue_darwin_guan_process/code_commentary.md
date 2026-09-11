# 02 annotated code commentary

## Model/process split

```text
GuanDarwinDynamicalModel::Evaluate()
  1. 用焦距和 off-axis 参数定义 focusPoint。
  2. idealOutDir = focusPoint - hitPosition。
  3. planeNormal = inDir - idealOutDir，代表能把入射方向反射到理想出射方向的晶面法线。
  4. thetaLocal = 0.5 * angle(inDir, idealOutDir)。
  5. deltaTheta = thetaLocal - thetaB。
  6. 调用 OnlineDarwinMosaicProbabilities 在线计算 pAbs/pDiff/pTrans。

GuanStyleLaueBraggProcess::PostStepDoIt()
  1. 做 Geant4 step 过滤：primary gamma、geometry boundary、LaueCrystal volume。
  2. 调用 model_.Evaluate()。
  3. 根据 pAbs/pDiff/pTrans 抽样。
  4. DIFFRACT 分支使用 reflectedOutDir，再用 mosaic sigma 做方向扰动。
```

## 和 01 的真正区别

01 把几何、查表和 Geant4 抽样都写在 process 里。02 把 Bragg/Darwin 判断移到模型类里，并在模型层在线计算 Darwin-Hamilton mosaic 概率，所以它不再只是 01 的类名重构。当前没有做的事情也要明说：没有移植 Guan/Reiazi 源码，没有 patch Geant4 toolkit，也没有进入 Geant4 EM category。

## 最容易误读的地方

- `registered_process` 是 app-level 加到 gamma process manager，不等于 Geant4 官方 EM category 过程。
- 02 的可信度来自“同几何、在线模型与 01 表驱动 baseline 的数值闭合”，不是来自宣称拿到了 Guan/Reiazi 原始代码。
