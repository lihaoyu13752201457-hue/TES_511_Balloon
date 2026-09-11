#!/usr/bin/env python3
"""Build the lightweight companion HTML slide deck.

The deck embeds the installed Editorial Light theme, shared component CSS,
and runtime.  Only the two validated source-comparison plots remain external
assets so the report stays easy to update when those plots are regenerated.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path("/home/ubuntu/.codex/skills/html-slides")


def notes(title: str, script: str, bullets: list[str]) -> str:
    payload = json.dumps(
        {"title": title, "script": script, "notes": bullets},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        '<script type="application/json" class="slide-notes">'
        + payload
        + "</script>"
    )


def build() -> Path:
    theme_css = (SKILL_ROOT / "assets/themes/editorial-light.css").read_text(
        encoding="utf-8"
    )
    components_css = (SKILL_ROOT / "assets/components.css").read_text(
        encoding="utf-8"
    )
    runtime_js = (SKILL_ROOT / "assets/slides-runtime.js").read_text(
        encoding="utf-8"
    )

    custom_css = dedent(
        r"""
        /* === REPORT-SPECIFIC SURFACE AND TYPE === */
        :root {
          --font-body: "Noto Sans CJK SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
          --font-mono: "IBM Plex Mono", "Noto Sans Mono CJK SC", monospace;
          --report-blue: #075b9d;
          --report-blue-soft: #eaf4fb;
          --report-green: #237a57;
          --report-green-soft: #eaf6f0;
          --report-amber: #aa6708;
          --report-amber-soft: #fff5df;
          --report-ink: #17212b;
          --report-muted: #53606d;
        }

        html, body, .deck {
          width: 100vw;
          height: 100vh;
          height: 100dvh;
          background: #ffffff !important;
        }

        .slide {
          height: 100vh;
          height: 100dvh;
          overflow: hidden;
          padding: clamp(1.4rem, 4vh, 3.25rem) clamp(2rem, 5vw, 6rem);
          background: #ffffff;
        }

        .particles, .glow-blob { display: none !important; }
        .branding { top: clamp(0.9rem, 2.3vh, 1.5rem); right: clamp(1.5rem, 3vw, 2.5rem); }
        .branding-icon { border-color: var(--report-blue) !important; color: var(--report-blue); }
        .nav-hints, .slide-counter { bottom: clamp(0.65rem, 2vh, 1.3rem); }
        .slide-nav { right: clamp(0.6rem, 1vw, 1rem); }

        h1 {
          color: var(--report-ink);
          font-size: clamp(2.4rem, 5vw, 4.9rem);
          letter-spacing: clamp(-0.09rem, -0.08vw, -0.03rem);
          margin-bottom: clamp(0.8rem, 2vh, 1.4rem);
        }
        h2 {
          color: var(--report-ink);
          font-size: clamp(1.8rem, 3.1vw, 3rem);
          letter-spacing: clamp(-0.05rem, -0.04vw, -0.02rem);
          margin-bottom: clamp(0.5rem, 1.2vh, 0.85rem);
        }
        .slide-tag {
          color: var(--report-blue) !important;
          font-size: clamp(0.68rem, 0.8vw, 0.82rem);
          letter-spacing: clamp(0.08rem, 0.13vw, 0.16rem);
          margin-bottom: clamp(0.5rem, 1.2vh, 0.9rem);
        }
        .subtitle {
          color: var(--report-muted) !important;
          font-size: clamp(1rem, 1.45vw, 1.35rem);
          line-height: 1.55;
        }

        /* === TITLE === */
        .title-rule {
          width: clamp(4rem, 9vw, 8rem);
          height: clamp(0.18rem, 0.35vh, 0.28rem);
          margin: clamp(1rem, 2.6vh, 1.8rem) 0;
          border-radius: 99rem;
          background: var(--report-blue);
        }
        .scope-chip {
          margin-top: clamp(1rem, 3vh, 2.2rem);
          padding: clamp(0.45rem, 0.9vh, 0.65rem) clamp(0.8rem, 1.3vw, 1.1rem);
          border-radius: 99rem;
          color: var(--report-blue);
          background: var(--report-blue-soft);
          font-size: clamp(0.76rem, 0.95vw, 0.92rem);
          font-weight: 700;
          letter-spacing: clamp(0.015rem, 0.03vw, 0.03rem);
        }

        /* === SOURCE FIGURES === */
        .figure-slide { justify-content: flex-start; }
        .figure-slide .image-frame {
          max-width: clamp(46rem, 78vw, 68rem);
          margin-top: clamp(0.55rem, 1.4vh, 1rem);
        }
        .figure-slide .slide-image {
          max-height: min(50vh, 400px) !important;
          border-radius: clamp(0.4rem, 0.8vw, 0.65rem);
          box-shadow: 0 clamp(0.35rem, 1vh, 0.75rem) clamp(1.2rem, 2.8vw, 2.5rem) rgba(20, 44, 66, 0.09);
        }
        .figure-caption {
          max-width: clamp(44rem, 75vw, 66rem);
          margin-top: clamp(0.55rem, 1.3vh, 0.9rem);
          text-align: center;
          color: var(--report-muted);
          font-size: clamp(0.82rem, 1.05vw, 1rem);
          line-height: 1.45;
        }
        .source-level-label {
          display: inline-flex;
          margin-top: clamp(0.42rem, 0.9vh, 0.65rem);
          padding: clamp(0.3rem, 0.6vh, 0.42rem) clamp(0.7rem, 1.2vw, 0.95rem);
          border-radius: 99rem;
          background: #f3f5f7;
          color: #4e5965;
          font-size: clamp(0.72rem, 0.9vw, 0.86rem);
          font-weight: 650;
        }

        /* === COMPUTE BURDEN === */
        .burden-formula {
          margin: clamp(0.6rem, 1.8vh, 1.2rem) 0 clamp(0.8rem, 2.2vh, 1.5rem);
          color: var(--report-blue);
          font-family: var(--font-mono);
          font-size: clamp(1rem, 1.65vw, 1.45rem);
          font-weight: 700;
          text-align: center;
        }
        .burden-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: clamp(0.7rem, 1.5vw, 1.25rem);
          width: min(100%, 67rem);
        }
        .burden-card {
          min-height: clamp(9rem, 22vh, 13.2rem);
          padding: clamp(1rem, 2.2vw, 1.7rem);
          border-radius: clamp(0.7rem, 1.1vw, 1rem);
          background: #f6f8fa;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        .burden-card.blue { background: var(--report-blue-soft); }
        .burden-card.amber { background: var(--report-amber-soft); }
        .burden-kicker {
          color: var(--report-muted);
          font-size: clamp(0.72rem, 0.9vw, 0.86rem);
          font-weight: 750;
          letter-spacing: clamp(0.04rem, 0.06vw, 0.07rem);
        }
        .burden-main {
          color: var(--report-ink);
          font-size: clamp(1.1rem, 1.7vw, 1.55rem);
          font-weight: 800;
          line-height: 1.3;
        }
        .burden-detail {
          color: var(--report-muted);
          font-size: clamp(0.78rem, 1vw, 0.95rem);
          line-height: 1.48;
        }
        .proof-line {
          margin-top: clamp(0.8rem, 2vh, 1.25rem);
          color: var(--report-green);
          font-size: clamp(0.8rem, 1.05vw, 1rem);
          font-weight: 750;
        }

        /* === CURRENT COMPUTE PIPELINE === */
        .pipeline {
          display: grid;
          grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
          align-items: stretch;
          gap: clamp(0.35rem, 0.85vw, 0.75rem);
          width: min(100%, 72rem);
          margin-top: clamp(1rem, 3vh, 2rem);
        }
        .pipe-box {
          min-height: clamp(10rem, 25vh, 14rem);
          padding: clamp(0.9rem, 1.8vw, 1.45rem);
          border-radius: clamp(0.7rem, 1vw, 0.9rem);
          background: #f6f8fa;
          display: flex;
          flex-direction: column;
          gap: clamp(0.45rem, 1.1vh, 0.75rem);
        }
        .pipe-box:nth-of-type(1) { background: var(--report-blue-soft); }
        .pipe-box:nth-of-type(5) { background: var(--report-green-soft); }
        .pipe-step {
          width: clamp(1.8rem, 2.7vw, 2.35rem);
          height: clamp(1.8rem, 2.7vw, 2.35rem);
          border-radius: 50%;
          display: grid;
          place-items: center;
          color: #ffffff;
          background: var(--report-blue);
          font-size: clamp(0.72rem, 0.9vw, 0.86rem);
          font-weight: 800;
        }
        .pipe-title {
          color: var(--report-ink);
          font-size: clamp(1rem, 1.4vw, 1.25rem);
          font-weight: 800;
        }
        .pipe-body {
          color: var(--report-muted);
          font-size: clamp(0.75rem, 0.95vw, 0.9rem);
          line-height: 1.5;
        }
        .pipe-arrow {
          align-self: center;
          color: #8da1b1;
          font-size: clamp(1rem, 1.7vw, 1.5rem);
          font-weight: 800;
        }
        .pipeline-foot {
          margin-top: clamp(0.85rem, 2.2vh, 1.4rem);
          color: var(--report-muted);
          font-size: clamp(0.78rem, 1vw, 0.95rem);
          text-align: center;
        }

        /* === STORAGE AND DATA PROCESSING === */
        .data-metrics {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: clamp(0.6rem, 1.2vw, 1rem);
          width: min(100%, 69rem);
          margin: clamp(0.9rem, 2.2vh, 1.4rem) 0;
        }
        .metric {
          padding: clamp(0.75rem, 1.5vw, 1.15rem);
          border-radius: clamp(0.65rem, 1vw, 0.9rem);
          background: #f6f8fa;
          text-align: center;
        }
        .metric strong {
          display: block;
          color: var(--report-blue);
          font-size: clamp(1.25rem, 2.25vw, 2rem);
          line-height: 1.15;
        }
        .metric span {
          display: block;
          margin-top: clamp(0.25rem, 0.55vh, 0.4rem);
          color: var(--report-muted);
          font-size: clamp(0.7rem, 0.9vw, 0.85rem);
          line-height: 1.35;
        }
        .storage-flow {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: clamp(0.7rem, 1.4vw, 1.1rem);
          width: min(100%, 69rem);
        }
        .storage-layer {
          padding: clamp(0.95rem, 1.9vw, 1.45rem);
          border-radius: clamp(0.7rem, 1vw, 0.9rem);
          background: var(--report-blue-soft);
        }
        .storage-layer:nth-child(2) { background: #f3f5f7; }
        .storage-layer:nth-child(3) { background: var(--report-green-soft); }
        .storage-title {
          color: var(--report-ink);
          font-size: clamp(0.92rem, 1.25vw, 1.12rem);
          font-weight: 800;
          margin-bottom: clamp(0.35rem, 0.8vh, 0.55rem);
        }
        .storage-text {
          color: var(--report-muted);
          font-size: clamp(0.73rem, 0.92vw, 0.88rem);
          line-height: 1.48;
        }

        /* === EARLY VS CURRENT === */
        .compare-wrap {
          width: min(100%, 69rem);
          margin-top: clamp(0.8rem, 2vh, 1.3rem);
          border-radius: clamp(0.7rem, 1vw, 0.95rem);
          overflow: hidden;
          box-shadow: 0 clamp(0.25rem, 0.7vh, 0.5rem) clamp(1.2rem, 2.6vw, 2.2rem) rgba(20, 44, 66, 0.07);
        }
        .compare-slide {
          justify-content: flex-start;
          padding-top: clamp(2.6rem, 6vh, 4.2rem);
        }
        .compare-slide h2 {
          max-width: min(100%, 74rem);
          font-size: clamp(1.7rem, 2.7vw, 2.55rem);
        }
        .compare-row {
          display: grid;
          grid-template-columns: clamp(6rem, 11vw, 9rem) 1fr 1fr;
          background: #ffffff;
        }
        .compare-row:nth-child(even) { background: #f7f9fb; }
        .compare-row > div {
          padding: clamp(0.55rem, 1.2vh, 0.85rem) clamp(0.65rem, 1.2vw, 1rem);
          font-size: clamp(0.7rem, 0.92vw, 0.88rem);
          line-height: 1.35;
        }
        .compare-row.header { background: var(--report-blue); color: #ffffff; }
        .compare-row.header > div { font-weight: 800; }
        .compare-label { color: var(--report-blue); font-weight: 800; }
        .compare-old { color: #66717b; }
        .compare-new { color: var(--report-ink); font-weight: 650; }
        .closing {
          margin-top: clamp(0.8rem, 2.2vh, 1.35rem);
          color: var(--report-green);
          font-size: clamp(1rem, 1.45vw, 1.3rem);
          font-weight: 800;
          text-align: center;
        }

        /* === VIEWPORT FITTING === */
        @media (max-height: 700px) {
          .slide { padding-top: clamp(1rem, 3vh, 1.7rem); padding-bottom: clamp(1rem, 3vh, 1.7rem); }
          .figure-slide .slide-image { max-height: min(46vh, 330px) !important; }
          .burden-card, .pipe-box { min-height: clamp(7.8rem, 20vh, 10.5rem); }
          .branding, .nav-hints { display: none; }
        }
        @media (max-height: 600px) {
          .figure-slide .slide-image { max-height: min(43vh, 265px) !important; }
          .figure-caption { line-height: 1.3; }
          .burden-formula, .data-metrics { margin-top: clamp(0.35rem, 1vh, 0.55rem); margin-bottom: clamp(0.35rem, 1vh, 0.55rem); }
          .proof-line, .pipeline-foot, .closing { margin-top: clamp(0.35rem, 1vh, 0.55rem); }
        }
        @media (max-height: 500px) {
          .slide { padding: clamp(0.6rem, 2vh, 0.9rem) clamp(1.5rem, 4vw, 3rem); }
          .slide-tag { display: none; }
          .figure-slide .slide-image { max-height: min(40vh, 200px) !important; }
          .source-level-label { margin-top: clamp(0.2rem, 0.4vh, 0.28rem); }
          .burden-card, .pipe-box { min-height: clamp(6.4rem, 18vh, 8rem); }
        }
        @media (max-width: 900px) {
          .burden-grid { grid-template-columns: 1fr; }
          .burden-card { min-height: auto; }
          .pipeline { grid-template-columns: 1fr 1fr; }
          .pipe-arrow { display: none; }
          .data-metrics { grid-template-columns: 1fr 1fr; }
          .storage-flow { grid-template-columns: 1fr; }
        }

        /* === STATIC EXPORT === */
        .export-mode *, .export-mode *::before, .export-mode *::after {
          animation: none !important;
          transition: none !important;
        }
        """
    ).strip()

    slide_0 = f"""
    <div class="slide active" data-slide="0">
      <p class="slide-tag anim-1">Mass_model_511 · S3d-O8</p>
      <h1 class="anim-2">从 38 km 气球<br>到 530 km 近地轨道</h1>
      <div class="title-rule anim-3"></div>
      <p class="subtitle anim-4">入射源环境、计算负担与当前模拟流程</p>
      <div class="scope-chip anim-5">简化技术报告 · 2026-08-13</div>
      {notes(
          "从气球到近地轨道",
          "这份简报只回答三个问题：气球和近地轨道的入射环境有什么不同，完整任务会带来多少额外计算维度，以及我们现在怎样组织计算、存储和数据处理。",
          ["比较入射源环境", "评估计算负担", "说明当前模拟与数据流程"],
      )}
    </div>
    """

    slide_1 = f"""
    <div class="slide figure-slide" data-slide="1">
      <p class="slide-tag anim-1">01 · 环境对比</p>
      <h2 class="anim-2">入射源：两类环境不是整体缩放</h2>
      <div class="image-frame anim-3">
        <img src="assets/source_components.png" alt="气球与近地轨道各入射粒子组件的微分强度谱" class="slide-image">
      </div>
      <p class="figure-caption anim-4">轨道侧拆分天区 γ、反照成分以及原初/次级带电粒子；气球侧保留八粒子族和角箱结构。</p>
      <span class="source-level-label anim-5">入射源级 · 不含活化 · 不是探测器计数</span>
      {notes(
          "入射组件谱",
          "先看入射源本身。气球环境受残余大气层影响，轨道环境则要区分天区、地球反照、原初和次级粒子，所以不能把一套谱简单乘一个系数后当作另一套环境。",
          ["轨道源需要按物理成分拆分", "气球源保留八粒子族与方向结构", "此图不代表探测器最终本底"],
      )}
    </div>
    """

    slide_2 = f"""
    <div class="slide figure-slide" data-slide="2">
      <p class="slide-tag anim-1">01 · 511 keV 相关能区</p>
      <h2 class="anim-2">关键能带：轨道环境并非全面更高或更低</h2>
      <div class="image-frame anim-3">
        <img src="assets/gamma_source.png" alt="气球与近地轨道伽马入射源谱及关键能段对比" class="slide-image">
      </div>
      <p class="figure-caption anim-4">γ：100–300 keV 为 1.17×，300 keV–10 MeV 为 0.30–0.60×；1–10 MeV 质子为 21.5×、正电子为 4.55×。最终探测器本底仍需输运确认。</p>
      <span class="source-level-label anim-5">入射源级 · 不含活化 · 不是探测器计数</span>
      {notes(
          "511 keV 相关能区",
          "对 511 keV 任务最重要的结论不是轨道环境整体更好或更差，而是能段依赖很强。正常轨道的宽带伽马在部分能区更低，但最终本底还要由屏蔽、反符合和探测器响应共同决定。",
          ["差异随能量变化", "窄线目标源与连续本底分开建模", "源级优势需要探测器输运确认"],
      )}
    </div>
    """

    slide_3 = f"""
    <div class="slide" data-slide="3">
      <p class="slide-tag anim-1">02 · 计算负担</p>
      <h2 class="anim-2">单状态近似同量级，完整轨道链更重</h2>
      <div class="burden-formula anim-3">计算规模 ≈ 状态数 × 方向数 × 粒子族 × 物理链</div>
      <div class="burden-grid anim-3">
        <article class="burden-card blue">
          <div class="burden-kicker">代表状态</div>
          <div class="burden-main">静态 prompt<br>可按同量级预算</div>
          <div class="burden-detail">同一质量模型下，单个轨道状态和单个气球状态都可用分片输运完成。</div>
        </article>
        <article class="burden-card amber">
          <div class="burden-kicker">完整任务</div>
          <div class="burden-main">轨道状态维度<br>显著增加</div>
          <div class="burden-detail">轨道位置、姿态、暴露权重，以及穿越高辐射区后的活化与延迟链均需独立审计。</div>
        </article>
        <article class="burden-card">
          <div class="burden-kicker">推荐做法</div>
          <div class="burden-main">先做代表状态<br>pilot 再扩展</div>
          <div class="burden-detail">用短试跑测量每族耗时、输出体积和方差，再决定轨道分箱与统计量。</div>
        </article>
      </div>
      <div class="proof-line anim-4">当前分片主线已验证：6,149,560 primaries · 488 receipts</div>
      {notes(
          "计算负担",
          "如果只比较一个固定状态，气球和轨道的 prompt 输运可以按同一数量级规划。真正抬高轨道任务成本的是状态维度和完整物理链，因此现在不先给一个拍脑袋的倍率，而是先用代表状态试跑得到实测成本。",
          ["单状态 prompt 可同量级规划", "完整轨道链增加状态和活化维度", "先 pilot 再确定生产规模"],
      )}
    </div>
    """

    slide_4 = f"""
    <div class="slide" data-slide="4">
      <p class="slide-tag anim-1">03 · 当前计算方式</p>
      <h2 class="anim-2">物理条件冻结，计算切成可恢复短分片</h2>
      <div class="pipeline anim-3">
        <article class="pipe-box">
          <div class="pipe-step">1</div>
          <div class="pipe-title">冻结计算契约</div>
          <div class="pipe-body">源、几何、模式、粒子族和随机种子均显式登记。</div>
        </article>
        <div class="pipe-arrow">→</div>
        <article class="pipe-box">
          <div class="pipe-step">2</div>
          <div class="pipe-title">短分片自适应</div>
          <div class="pipe-body">目标约 5–10 分钟/任务；依据近期实测耗时调整下一片规模。</div>
        </article>
        <div class="pipe-arrow">→</div>
        <article class="pipe-box">
          <div class="pipe-step">3</div>
          <div class="pipe-title">按粒子族调度</div>
          <div class="pipe-body">重尾粒子使用更小批次和轮转排程，避免单个任务拖住整批。</div>
        </article>
        <div class="pipe-arrow">→</div>
        <article class="pipe-box">
          <div class="pipe-step">4</div>
          <div class="pipe-title">分片即刻验收</div>
          <div class="pipe-body">每片通过后才登记；只在同几何、模式和粒子族域内汇总。</div>
        </article>
      </div>
      <p class="pipeline-foot anim-4">优化的是任务组织、并发、压缩与恢复；物理输入在同一批次内保持不变。</p>
      {notes(
          "当前计算方式",
          "当前流程先冻结物理契约，再把大任务拆成短而可恢复的分片。分片规模根据实测耗时自适应调整，重尾粒子单独调度，每一片完成后立即验收，所以失败只需要补缺失的小片。",
          ["物理条件与调度优化分离", "短分片降低失败重算成本", "按粒子族和合并域严格隔离"],
      )}
    </div>
    """

    slide_5 = f"""
    <div class="slide" data-slide="5">
      <p class="slide-tag anim-1">03 · 存储与数据处理</p>
      <h2 class="anim-2">原始层保留，验证与分析走轻量派生层</h2>
      <div class="data-metrics anim-3">
        <div class="metric"><strong>976</strong><span>selected jobs</span></div>
        <div class="metric"><strong>13,777,092</strong><span>primary histories</span></div>
        <div class="metric"><strong>77.6 GB</strong><span>selected .sim.gz；原始层保留</span></div>
        <div class="metric"><strong>62.8 MB</strong><span>当前活跃派生输出</span></div>
      </div>
      <div class="storage-flow anim-3">
        <article class="storage-layer">
          <div class="storage-title">① 压缩原始产物</div>
          <div class="storage-text">SIM / DAT / log 保留完整信息；临时文件完成后原子改名，失败尝试单独隔离。</div>
        </article>
        <article class="storage-layer">
          <div class="storage-title">② 不可变 receipt</div>
          <div class="storage-text">每个分片记录种子、事件数、TT/RP、耗时、内存、字节数与校验摘要。</div>
        </article>
        <article class="storage-layer">
          <div class="storage-title">③ 派生工作层</div>
          <div class="storage-text">日常筛选和统计直接读取小型表格与 checkpoint，不反复扫描全部大文件。</div>
        </article>
      </div>
      {notes(
          "存储与数据处理",
          "存储策略不是删除原始信息，而是把原始层、验证层和分析层分开。原始产物继续保留，receipt 负责可审计性，日常分析使用六十多兆的派生工作层，从而减少重复读取和重复解析。",
          ["原始层完整保留", "每个分片都有不可变验证记录", "轻量派生层加速日常分析"],
      )}
    </div>
    """

    slide_6 = f"""
    <div class="slide compare-slide" data-slide="6">
      <p class="slide-tag anim-1">总结 · 早期与当前</p>
      <h2 class="anim-2">从“大任务 + 事后处理”转为“分片 + 即时验证”</h2>
      <div class="compare-wrap anim-3">
        <div class="compare-row header"><div>环节</div><div>早期流程</div><div>当前流程</div></div>
        <div class="compare-row"><div class="compare-label">任务组织</div><div class="compare-old">较大的固定任务</div><div class="compare-new">短分片，自适应规模</div></div>
        <div class="compare-row"><div class="compare-label">失败恢复</div><div class="compare-old">重跑较大输出段</div><div class="compare-new">只补缺失分片</div></div>
        <div class="compare-row"><div class="compare-label">质量控制</div><div class="compare-old">批次结束后集中检查</div><div class="compare-new">每片完成立即验收</div></div>
        <div class="compare-row"><div class="compare-label">存储入口</div><div class="compare-old">分析直接读取大文件</div><div class="compare-new">原始层 + receipt + 派生层</div></div>
        <div class="compare-row"><div class="compare-label">汇总边界</div><div class="compare-old">以批次为主要单位</div><div class="compare-new">几何 / 模式 / 粒子族严格分域</div></div>
      </div>
      <div class="closing anim-4">下一步：用代表轨道状态 pilot，实测成本后再扩展完整轨道链。</div>
      {notes(
          "早期流程与当前流程",
          "现在的核心变化可以概括为四个词：短分片、即时验证、分层存储和严格分域。它让生产更容易恢复，也让分析不必反复读取全部原始文件。轨道版本的下一步就是把这套机制用于代表状态试跑，再据实扩展。",
          ["减少失败后的重算范围", "验证和分析都由 receipt 驱动", "代表轨道状态 pilot 是下一步"],
      )}
    </div>
    """

    body = "\n".join(
        dedent(s).strip()
        for s in [slide_0, slide_1, slide_2, slide_3, slide_4, slide_5, slide_6]
    )

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="generator" content="html-slides v0.9.4">
  <title>从气球到近地轨道：源环境、计算负担与模拟流程</title>
  <style>
  /* === EDITORIAL LIGHT THEME === */
  {theme_css}

  /* === SHARED PRO COMPONENTS === */
  {components_css}

  {custom_css}
  </style>
</head>
<body>
  <!-- === PRESENTATION CHROME === -->
  <div class="particles" id="particles"></div>
  <div class="branding"><div class="branding-icon">511</div> TES-511</div>
  <div class="slide-nav" id="slideNav"></div>
  <div class="progress-bar" id="progress"></div>
  <div class="slide-counter" id="counter"></div>
  <div class="nav-hints"><span><kbd>←</kbd><kbd>→</kbd> 翻页</span></div>

  <!-- === SLIDES === -->
  <div class="deck" id="deck">
  {body}
  </div>

  <script>
  {runtime_js}

  // === STATIC EXPORT / DEEP LINK SUPPORT ===
  (function () {{
    const params = new URLSearchParams(window.location.search);
    if (params.get('export') === '1') {{
      document.documentElement.classList.add('export-mode');
    }}
    const requested = Number.parseInt(params.get('slide') || '0', 10);
    if (Number.isInteger(requested) && requested >= 0 && requested < total) {{
      if (requested !== 0) goTo(requested);
    }}
  }})();
  </script>
</body>
</html>
"""

    output = ROOT / "index.html"
    output.write_text(html, encoding="utf-8")
    return output


if __name__ == "__main__":
    built = build()
    print(built)
