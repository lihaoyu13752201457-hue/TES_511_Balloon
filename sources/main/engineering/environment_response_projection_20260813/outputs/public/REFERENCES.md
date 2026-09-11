# 图 2 数据来源与角域

下列编号与 `02_full_spectrum_comparison` 图内编号一致。引用已于 2026-08-13 对照期刊/DOI 页面、固定代码提交和数据 DOI。

1. Sato, T. (2015), Analytical Model for Estimating Terrestrial Cosmic Ray Fluxes Nearly Anytime and Anywhere in the World: Extension of PARMA/EXPACS, PLOS ONE 10, e0144679. [10.1371/journal.pone.0144679](https://doi.org/10.1371/journal.pone.0144679)
   - 角分布：Sato, T. (2016), Analytical Model for Estimating the Zenith Angle Dependence of Terrestrial Cosmic Ray Fluxes, PLOS ONE 11, e0160390. [10.1371/journal.pone.0160390](https://doi.org/10.1371/journal.pone.0160390)
2. Gallego et al. (2026), Preflight Background Estimates for COSI, The Astrophysical Journal 997, 284. [10.3847/1538-4357/ae32f4](https://doi.org/10.3847/1538-4357/ae32f4)
   - 固定数据/代码: https://github.com/cositools/cosi-sim/tree/eec0dbf1aaabc79fea2706946434e30f7060a59a/cosi_sim/Source_Library/DC4/backgrounds
3. Dobynde, M. I. & Guo, J. (2021), Radiation Environment at the Surface and Subsurface of the Moon: Model Development and Validation, JGR: Planets 126, e2021JE006930. [10.1029/2021JE006930](https://doi.org/10.1029/2021JE006930)
   - 公开数据集: https://doi.org/10.5281/zenodo.5561427
   - 注：Lunar gamma additionally includes a 2pi COSI cosmic-sky proxy.

## 支撑模型引用

- JAEA/PHITS, EXPACS official distribution and documentation. https://phits.jaea.go.jp/expacs/
- Cumani, P. et al. (2019), Background for a gamma-ray satellite on a low-Earth orbit, Experimental Astronomy 47, 273–302. [10.1007/s10686-019-09624-0](https://doi.org/10.1007/s10686-019-09624-0)

固定输入抽查：REDMoon `fig5.txt` SHA-256 = `82d72b510ead4d136a289de0f32091bab5446418447c53168af32a3822f0c1f5`；
COSI `AlbedoPhotons.source` SHA-256 = `6055789674d633f9050f2889cab46cc9172c59fa42ac3e8f385e902c476ee616`。

## 角域解释

图中纵轴是各源物理角域积分后的 `E dF/dE [cm^-2 s^-1]`，不是某个方向的 `sr^-1` 强度，也不是三套谱都统一到 4π。

- 大气：20 个等 μ 角箱求和，严格为 4π。
- LEO：各 primary/albedo/secondary 分量在自身角域积分后求和。
- 月面：月壤上行半球为 2π；γ 另加天空下行 2π 代理。

因此曲线适合做源级环境对照，但不能直接解释成共同方向的强度比。
