# 日–地 L2 静态入射源谱口径

## 结论先行

本包把日–地 L2 视为近地 1 AU 的深空环境，而不是更高的 LEO。静态基线只包含：

- 1 AU 太阳调制后的 GCR `p / alpha / e- / e+`；
- 全空 `4π` 的宇宙弥散 gamma 连续谱。

不从 LEO 搬运以下分量：地球反照 gamma、独立大气 511 keV 线、反照/大气中子、
大气次级带电粒子、SAA。SEP 是独立瞬变场景，不混入静态基线。

## 与 LEO 保持同一母模型

为了使 L2 与现有 PPT 的 530 km LEO 口径可比，本包不再拼接另一套年代或太阳活动
状态不同的 GCR 表，而是使用固定 COSI DC4 源包中同一套 1 AU primary 母谱，并仅去除
LEO 的地磁传输项。

COSI/LEOBackground 对 primary 的地磁传输为：

```text
G(E) = 1 / [1 + (R(E) / Rc)^(-n)]
Rc = 12.6 GV
n = 12  (p, alpha)
n = 6   (e-, e+)
```

因此 L2 的 full-sphere 曲线定义为：

```text
(dF/dE)_L2 = 4π × <I_LEO_primary(E)> / G(E)
```

其中 `<I_LEO_primary>` 是固定 COSI primary 分量在其 LEO 未遮挡天区内的平均强度。
gamma 不受地磁传输，直接使用 COSI cosmic-photon 平均强度：

```text
(dF/dE)_L2,gamma = 4π × <I_COSI_cosmic_gamma(E)>
```

这一步同时把 LEO 的未遮挡天区 `8.6073797 sr` 扩展到 L2 的 `4π`，而不是把 LEO
源卡的角域积分率原样照搬。

## 单位和有效域

- 横轴：单个入射粒子的总动能 `keV_total`；alpha 不再乘 4。
- 纵轴：所声明角域上的积分微分通量 `dF/dE [cm^-2 s^-1 keV^-1]`。
- 本包实际固定节点范围为：`p / alpha` 总动能 `10 MeV–10 TeV`，
  `e- / e+` 总动能 `657.93 MeV–351.12 GeV`，cosmic gamma
  `0.1 MeV–739.07 GeV`。
- 这些是本次固定 COSI 表在上游有效域过滤后的实际可用支撑，不用解析模型更宽的
  名义范围替代文件中真正存在的节点。
- 不在有效域外做谱外推；响应事件落在域外时写成 coverage 缺口，而不称为物理零。

## L2 中子、muon 与重离子

- nominal L2 没有行星大气/表面反照中子，因此外部 `n` 分量设为无该组件；由 GCR
  在 SH3 内部产生的次级中子已包含在 `p / alpha` 的保留输运响应中。
- nominal L2 没有大气 muon 外源；同理，不把 COSI 缺失的 muon 曲线补成一条经验谱。
- 深空 GCR 实际包含 `Z>2` 重离子，但当前 SH3 八族源/响应没有该族，因此本次性能
  估算不包含 HZE 活化；这使结果只能作为八族范围内的代理，不能作为完整 L2 权威。
- SEP、太阳中子、磁尾低能等离子体与太阳活动时变均另建情景。

## 文献与固定实现

- Cumani et al., *Background for a gamma-ray satellite on a low-Earth orbit*,
  Experimental Astronomy 47 (2019), DOI: [10.1007/s10686-019-09624-0](https://doi.org/10.1007/s10686-019-09624-0)。
- COSI LEOBackgroundGenerator（primary 谱及地磁传输实现）：
  [cositools/cosi-background](https://github.com/cositools/cosi-background)。
- COSI DC4 固定源包：
  [cositools/cosi-sim / DC4 backgrounds](https://github.com/cositools/cosi-sim/tree/eec0dbf1aaabc79fea2706946434e30f7060a59a/cosi_sim/Source_Library/DC4/backgrounds)。
- Slaba & Whitman, *The Badhwar–O'Neill 2020 GCR Model*, Space Weather 18
  (2020), DOI: [10.1029/2020SW002456](https://doi.org/10.1029/2020SW002456)。该文用于
  支持“1 AU 深空静态 GCR”这一环境语义；本包数值仍取与 LEO 一致的 COSI 母谱，
  不用 BON2020 数值替换 COSI。

## 权威边界

该合同授权 L2 静态源谱代理及其与现有环境曲线的同口径比较。它不授权 L2 的完整
prompt、activation、delayed、偶然符合或任务灵敏度；这些仍需 L2 专用 source card 与
匹配输运闭合。
