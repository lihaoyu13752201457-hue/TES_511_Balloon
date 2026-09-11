# SG3B M05 common-time response

Status: `PASS__SG3B_OWN_BACKGROUND_COMMON_TIME_RESPONSE__CONDITIONAL_SIGNAL_PROXY_FLUX_REACH`

## 归一化与选择

- prompt 使用 22 个 INSTANT receipt、3,842,079 primaries；每族事件权重为 `1/sum(TT_family)`。
- delayed 使用 canonical v2 的 33 个 receipt、8,000,000 triggers；每族事件权重为 `A15_family/1,000,000`。
- 先分别施加 10 mm plastic 正电子/带电粒子 veto 与三块 BGO 主动闪烁体 veto，再取二者交集，最后执行 retained Step05 Compton/FoV。两类主动层均用严格 `<50 keV` 离线阈值。
- prompt 与 delayed 的全带探测器 occupancy 按独立泊松流叠加到同一个 1 microsecond 时间轴；弱源 live factor 为 `exp[-tau(R_prompt+R_delayed)]`。
- repaired broadband gamma 已含湮没隆起；PARMA mono-511 sidecar 未加入任何本底和。

## 20-day 条件通量阈值

| stage | B20 counts | proxy Aeff (cm2) | F3 Gaussian | F3 Poisson-Asimov | F5 Poisson-Asimov |
|---|---:|---:|---:|---:|---:|
| pre_veto | 1.060832e+07 | 11.88432 | 0.0007516097 | 0.000751725 | 0.001253003 |
| plastic_positron_veto | 2620828 | 11.88432 | 0.0003735841 | 0.0003736994 | 0.0006229605 |
| bgo_active_scintillator_veto | 100873.7 | 11.88432 | 7.329225e-05 | 7.340754e-05 | 0.0001224738 |
| combined_active_veto | 99123.34 | 11.88432 | 7.265358e-05 | 7.276887e-05 | 0.0001214094 |
| compton_trajectory_veto | 90727.34 | 11.69478 | 7.063507e-05 | 7.075223e-05 | 0.0001180504 |

## 时间解析形式

对任意累计时刻 `T`，本包输出 `K(T)=integral[Aeff(t) T_atm(t) L(t) dt]` 与 `B(T)=integral[B_rate(t)L(t)dt]`。M05 高计数近似为 `F_q(T)=q sqrt(B(T))/K(T)`；同时给出由 `Z_A=sqrt(2[(S+B)ln(1+S/B)-S])` 反解的 Poisson-Asimov 阈值。局部平稳近似的时间分辨式为 `Delta t_min=q^2 B_rate/(F^2 K_rate^2)`。
第 15 天 final stage 的 live 后本底率为 `0.052761 cps`，条件信号 kernel 为 `7.463505 cm2`。
20 天 final stage 条件结果：Gaussian F3=`7.063507e-05`，Poisson-Asimov F3=`7.075223e-05` ph cm^-2 s^-1。

## Authority boundary

这些通量阈值不是 SG3B 最终灵敏度 authority。分母使用 SE3 的 37,194-ray full-envelope W2 selected Aeff 作为条件代理；SG3B 静态审计只证明新增 Bi 不与 primary rays 相交，不能替代 SG3B 自身的 full-envelope 信号输运及共同响应。prompt/delayed 本底、veto cutflow、归一化和 common-time occupancy 则来自 SG3B 自身 accepted transports。
