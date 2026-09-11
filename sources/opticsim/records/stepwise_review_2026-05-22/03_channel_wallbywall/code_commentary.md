# 03 annotated code commentary

## Main loop

```text
simulate_wallbywall_channel()
  1. 先按 ring collecting area 抽一个 ring。
  2. 再在该 ring 上抽 tile 和入口位置。
  3. 如果抽到 W 层或支撑闭合部分，写 ENTRY_BLOCKED。
  4. 如果抽到 Si spacer，进入 _trace_one_event()。
```

## One photon trace

```text
_trace_one_event()
  state.s_mm      当前沿 channel 长度走了多远。
  state.q_mm      当前在 spacer gap 内的横向位置。
  state.alpha_rad 当前光线相对局部 channel tangent 的角度。

  while photon has not exited:
    _next_wall_hit() 解下一次撞哪一面墙。
    如果启用 Si path absorption，先对 spacer 路径做 exp(-mu*path) 抽样。
    lookup.lookup(abs(theta_hit)) 得到该 grazing angle 的 R/A/T。
    u < A           -> ABSORB
    u >= A + R      -> LEAK
    otherwise       -> BOUNCE, alpha 反号，继续下一墙

  EXIT photon 被投影到 focal_length_mm 平面，并写入 phase_space.csv。
```

## 独立闭合

```text
compute_reflectivity_rows()
  使用 xraydb.multilayer_reflectivity 生成 W/Si stack 的 R(theta)。

manual_parratt_reflectivity_s()
  不调用 xraydb.multilayer_reflectivity，只用 optical constants 手写 Parratt recursion。

build_channel_independent_closure.py
  用 roughness 和 Si path absorption 的组合扫描，检查不加校正因子时和 CAM511 0.80 headline 的距离。
```

## 最容易误读的地方

- wall-by-wall 不是 Geant4 navigation，而是 Python 独立 ray trace；Geant4 的价值在后续 detector/activation handoff。
- `max_bounces` 是死循环保护，不是物理上强行规定反射次数；实际 survivor mean bounces 来自几何和随机过程。
- `best_no_fudge_variant` 接近 CAM511 0.80，但没有完全闭合，不能偷加 multiplier。
