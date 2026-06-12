# Route-A B-FULL Laue Lens Design Rationale (2026-06-01)

## Scope

This is the review package requested by `LAUE_LENS_DESIGN_SPEC_20260601.md`: design a physically plausible Ge(111) Laue focusing mirror for 480-550 keV, run the B-FULL optical simulation, and stop before the detector full-chain integration.

## Selected Design

- Design name: `balloon511_f9m_ge111_511line`.
- Material/reflection: Ge(111), d = `3.266590088` Angstrom.
- Focal length: `9.0 m`.
- Tile size: `15.0 mm x 15.0 mm`.
- Ring z pitch: `0.0 mm`.
- Mosaicity: `30.0 arcsec`.
- Energies: `511 keV`.
- Total tiles: `27`.
- Total geometric crystal area: `60.75 cm2`.
- Exact 511-keV A_eff: `15.2993 cm2`.
- Design target A_eff(511): `16 cm2` with `0.15` fractional tolerance.
- A_eff target residual: `0.043795`.
- Sampled line-band A_eff sum: `15.2993 cm2`.
- Natural mosaic passband FWHM: `500.994-521.006 keV` (`20.0121 keV` full width).
- Ge mass estimate for active crystals only: `0.330448 kg`.
- Outer ring radius plus half tile: `74.3501 mm`.

## Physical Justification

- The optical design is now 511-line first. The 480-550 keV interval is treated as the detector analysis window for line fitting and local continuum, not as an equal-weight Laue focusing band.
- The 9 m focal length is the upper end of the 6-9 m balloon-compatible execution envelope and stays close to the 8.3 m 511-CAM Laue-lens scale obtained by scaling the CLAIRE balloon lens concept from 170 keV to 511 keV.
- The optical area is placed in a full-azimuth 511-keV ring rather than split into broad 480/550 keV endpoint rings.
- 15 mm square Ge tiles are at the upper end of the common 5-15 mm Laue-crystal scale and give near-full azimuthal fill at the 511-keV Bragg radius without chord-overlap.
- The 30 arcsec mosaicity gives the design natural FWHM passband through DeltaE/E = cot(theta_B) * mosaic_FWHM_rad. For Ge(111) at 511 keV this is about 511 +/- 10 keV.
- A tested 507-515 keV multi-ring axial stack was rejected because overlapping projected apertures caused upstream rings to shadow the 511-keV anchor ring. This baseline keeps the projected aperture honest.
- The minimum within-ring azimuthal edge gap is `0.521654 mm`.
- The 30 arcsec mosaicity is retained because it is the already validated B-FULL baseline and lies inside the 10-60 arcsec quality range quoted for Laue-lens crystals.
- The 511-keV ring uses the existing XOP/CRYSTAL rocking curve and B-FULL is run with the map required.

Public anchors used for review wording:

- CLAIRE demonstrated a balloon Laue lens using 556 Ge-Si crystals on eight rings.
- MAX/GRI/LAUE studies use mosaicities around 30 arcsec and focal lengths from about 10 m to much longer formation-flying concepts.
- 511-CAM is a 511-keV line instrument; o-Ps continuum is below 511 keV and is kept as detector-side analysis/future-prospect context rather than the Laue optical driver.

## Ring Table

| ring | E keV | z mm | radius mm | n tiles | geom area cm2 | thickness mm | analytic eff | emergent within-Be eff | A_eff cm2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 511 | 0.000000e+00 | 66.8501 | 27 | 60.75 | 10.2188 | 0.257481 | 0.25184 | 15.2993 |

## Be-Window Focus Check

- Be radius requirement: `r99 <= 1.898 cm`.
- Diffracted focal rows: `12605`.
- Within-Be focal rows: `12592`.
- r95 all diffracted crossings: `0.219108 cm`.
- r99 all diffracted crossings: `0.29141 cm`.
- Outside-Be focal rows: `13`.
- Within-Be fraction: `0.998969`.
- Max within-Be focal radius: `1.45767 cm`.
- Max all-diffracted radius: `17.7637 cm`.
- Pass: `True`.

## Cross-Check Gate

- B-FULL run status: `RUN_AVAILABLE`.
- Rocking curve map: `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_xop_map.csv`.
- Emergent focal diffraction fraction: `0.2521`.
- Analytic reference focal diffraction fraction: `0.257481`.
- Emergent minus analytic: `-0.00538123`.
- Pass <0.04 design-stage gate: `True`.
- Strict <0.01 diagnostic gate: `True`.

## Review Boundary

Per the design spec, this package stops at the optical design review gate. It does not replace Step07, does not run detector full-chain transport, and does not add lens hardware mass to the DEMO2 background model.

## Artifacts

- Ring config: `/home/ubuntu/opticsim/data/laue/ge111_balloon511_f9m_511keV_line_config.csv`.
- Repository copy of ring config: `stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_line_config.csv`.
- Rocking-curve map: `stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_xop_map.csv`.
- A_eff authority: `stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`.
- Cross-check report: `stepwise_maintenance/step04_opticsim/real_design_crosscheck_20260601.md`.
- B-FULL output directory: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_real`.

---

## Claude (Opus 4.8) Review — 2026-06-02(对 Codex f9m 定稿设计 + 全链更新的审核)

> 审核人:**Claude**。对照 `EXECUTE_ROUTE_A_FULLCHAIN_AND_REPORT_20260601.md` §2 定稿 spec,实测复核(非只读 summary)。

### 总评:实现正确、且超出 spec(做了全链 + 探测器耦合),**未发现 bug**。显著性诚实地降低了——这是对的,不是退步。

### 通过项(实测复核)
- ✅ **设计照 spec**:Ge(111) 单环 511、f=9m、r=66.85mm、27×15mm 满方位密排、30″ 镶嵌、**A_eff(511)=15.30 cm²**;
  emergent−analytic=**−0.0054**(过严格 0.01 门控);光学焦斑 r99=**0.288 cm**(我直接复算 focal_crossings 一致)< Be 1.898。
- ✅ **天然 passband 已记录**:`optics_aeff_authority.json.natural_passband_fwhm` = 500.99–521.01 keV,ΔE/E=**3.92%**,公式 cot θ_B×ω。与 §2 一致。
- ✅ **统计口径照 spec 改**:W1=`W1_design_passband`(500.99–521.01,替换 480–550 当 headline);最终 3σ=`line_pm_3sigma`=**511±420 eV**;参考源 **V404 511 扫强度** case 保留。
- ✅ **全链已打通(超出 Task A)**:Step07 科学源换成**聚焦 EventList**(非 HomogeneousBeam),A_opt 用 **15.30 替换 50.89 占位**;Step09 **全量 Cosima 传输**(SE=11910,非 smoke)。
- ✅ **探测器耦合空间切割(升级,闭合 0531 P1_FOCUSED_SPOT)**:`spatial_line_proxy` 现用**全量传输后 TES 实测质心**做空间切割(claim `L1_SPATIAL_LINE_DETECTOR_COUPLED_CLOSED`)。
- ✅ **validator 20/20 PASS**。

### 关键发现:显著性诚实降低(正确,需写进论文理解)
当前最佳探测器耦合空间切割(`spot_r68`,r=0.188cm):**Z20d=5.95**,3σ flux=**5.04e-5 ph cm⁻² s⁻¹**(参考 1e-4);511±420eV 无切割 Z20d=2.75。
比早前 ~22 低,原因有二,**都是物理上正确的诚实化**:
1. **真实 Laue A_eff=15.30 cm² 替换了 channel 占位 50.89 cm²**(信号 ×3.3 少)——这是真实气球单能 Ge Laue 的 A_eff 上限(∝f)。
2. **探测器把 511 焦斑康普顿展开**:光学焦斑 r99=0.29cm,但 **TES 实测质心 r99≈1.22cm**(511keV 光子在 **Ta**(钽)叠层里先康普顿散射再光电吸收,质心散到 ~cm)。**聚焦的空间压本底优势被探测器展宽部分抵消**——真实效应,现被探测器耦合传输如实捕获。

> 含义:**这就是"气球 Ge(111) Laue + Ta-TES @511keV"的真实性能数**(Z~6 量级、3σ flux ~5e-5),不是退步,是把占位/理想化换成了真实物理。论文应如实呈现,并把"探测器康普顿展宽限制焦斑空间切割"作为一个明确结论/局限。
> (材料勘误 2026-06-02:TES 吸收体为 **Ta**,`GenerateGeo_ADR_v4c_mkflange.py:337` 确认;早稿误写 Bi,源自 opticsim 旧探测器原型,几何未变,结论/数不变。)

### 小项(非阻塞)
- 🔹 `build_line_window_sensitivity.py` 仍保留 `broad_480_550` 行作次级参考(headline 已是 `W1_design_passband`)。建议加注释标 "superseded by W1 design passband",免将来误读。
- 🔹 本 md 上面 "Review Boundary" 仍写 "stops at design / does not replace Step07 / does not run full-chain"——但 Codex 实际已替换 Step07 并跑了全链传输,该句**已过时**,建议更新。
- 🔹 `focal_stats.r99=0.29cm` 是**光学焦斑**;探测器耦合实测 r99≈1.22cm 在 Step08 侧——不同平面的量(光学 vs 探测器),都对,建议在 md 里点一句区别免混。

### 结论
Codex 这轮**正确、完整、超额**(全链 + 探测器耦合),与 §2 spec 对齐,无 bug。显著性降到诚实量级(Z~6、3σ~5e-5),是把占位 A_eff 和理想焦斑换成真实 Laue + 真实探测器响应的必然结果。**可接受**;论文按真实数写,并明说探测器康普顿展宽是焦斑空间切割的主要限制。
— Claude (Opus 4.8), 2026-06-02
