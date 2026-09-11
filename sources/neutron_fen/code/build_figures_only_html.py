#!/usr/bin/env python3
"""Build one self-contained HTML deck containing every presentation figure."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "outputs" / "figures"
OUTPUT = FIGURES / "sh3_all_figures.html"


@dataclass(frozen=True)
class Figure:
    title: str
    filename: str
    alt: str
    bullets: tuple[str, ...]
    takeaway: str
    script: str


FIGURE_SPECS = (
    Figure(
        "MEGAlib：六层 Si HIT 与像素 footprint",
        "sh3_megalib_si_depositions_six_layers.png",
        "六层 Si 沉积点与半透明像素 footprint",
        (
            "六个面板分别是 L0–L5；横、纵轴是 36 × 36 mm² Si 的局部坐标。",
            "半透明白色方格是 376 个 1.5 × 1.5 mm² 像素 footprint。",
            "圆点是一条 Si 正沉积 HIT；点越大、颜色越偏黄，单条沉积能量越高。",
            "圆点落在哪个方格上，就表示该沉积位于哪个像素 footprint 下方；方格外的点位于无像素覆盖区域。",
        ),
        "结论：六层都有沉积；HIT 位置可以直接与像素阵列对照。",
        "半透明方格是像素 footprint，彩色圆点是硅沉积。叠加显示后，可以直接判断每条沉积相对像素阵列的位置。",
    ),
    Figure(
        "G4CMP 原理：声子从强散射转向弹道传播",
        "sh3_g4cmp_phonon_transport_physics.png",
        "声子能量与散射、非谐衰变平均自由程",
        (
            "横轴是单声子能量，纵轴是平均自由程；两轴都是对数刻度。",
            "蓝线是同位素散射，橙线是纵声子非谐分裂；曲线越低，过程越频繁。",
            "水平线是 Si 厚度 0.3 mm 与横向尺寸 36 mm。",
            "声子降频时从右向左移动；平均自由程超过器件尺寸后，传播接近弹道。",
        ),
        "62、30、2.7 meV 是初始声子谱测试点，不是中子事件总能量。",
        "这张图解释为什么不能直接使用普通热扩散：声子先快速散射和降频，之后平均自由程达到器件尺度。",
    ),
    Figure(
        "G4CMP 输出：非热声子能量最终流入哪些 sensor pixels",
        "sh3_all86_six_layer_matplotlib_map.png",
        "全部 86 个事件的逐像素时间积分非热声子能量",
        (
            "青色圆点是 MEGAlib 的 Si 声子源位置；点大小表示源沉积能量。",
            "每个方格是一个独立像素；紫色到黄色表示该像素累计收到的声子能量由低到高。",
            "颜色代表 ∫Pᵢ(t)dt，即流入像素的时间积分能量，不代表温度。",
            "这不是热流矢量图：G4CMP 输出是离散、尚未热化的声子终止记录，没有唯一的局部 T(x,t) 或 −κ∇T。",
        ),
        "逐像素能量是 TES 模型的直接输入，因此比虚构温度场或直线流线更适合当前触发问题。",
        "彩色像素显示声子最终向各 TES 通道输送了多少能量。它类似能量流入分布，但物理上是时间积分能量，而不是连续热流矢量。",
    ),
    Figure(
        "候选 C：逐层、逐像素能量分配",
        "sh3_candidate_C_six_layer_matplotlib_map.png",
        "候选 C 的六层逐像素能量图",
        (
            "L0 青点是 43 条 Si 沉积；彩色像素是 G4CMP 声子累计输入。",
            "L1 有两个直接沉积像素：P231 = 433.544 keV，P147 = 24.848 keV。",
            "L0 最强声子像素是 P251 = 29.455 keV；L2–L5 为零。",
            "整格着色只是把通道值画清楚，不表示物理 sensor 覆盖整个 footprint。",
        ),
        "没有任何单像素接近 511 keV；510.964 keV 只是跨层、跨像素算术和。",
        "这张图必须逐像素读取。最大通道是四百三十三点五千电子伏，因此候选 C 不会形成单像素五百一十一千电子伏触发。",
    ),
    Figure(
        "两节点 TES 脉冲：只保留主脉冲图",
        "sh3_tes_two_node_pulse_comparison.png",
        "单像素光子模板与候选 C 反事实阵列求和模板",
        (
            "横轴是时间 ms，纵轴是 TES 电流下降量除以各自峰值。",
            "黑线是一个像素的光子路径：能量先进入 Ta 吸收体。",
            "绿线是把候选 C 所有通道人为相加后的压力测试，不是一个真实 TES 通道。",
            "两种输入均缩放到 1 keV 小信号条件，因此只比较归一化形状。",
        ),
        "实际逐像素读出不会形成绿线；候选 C 的最大真实通道仍是 433.544 keV。",
        "脉冲图只保留主面板。黑线是单像素光子，绿线是反事实阵列和；实际硬件逐像素读出不会形成绿线。",
    ),
)


def data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def slide_html(index: int, spec: Figure) -> str:
    notes = json.dumps(
        {
            "title": spec.title,
            "script": spec.script,
            "notes": list(spec.bullets) + [spec.takeaway],
        },
        ensure_ascii=False,
    )
    bullets = "\n".join(f"<li>{item}</li>" for item in spec.bullets)
    active = " active" if index == 0 else ""
    return f"""
    <div class="slide{active}" data-slide="{index}" aria-label="{spec.title}">
      <header>
        <p class="kicker">SH3 figures · {index + 1}/{len(FIGURE_SPECS)}</p>
        <h2>{spec.title}</h2>
      </header>
      <div class="figure-layout">
        <div class="image-wrap"><img src="{data_url(FIGURES / spec.filename)}" alt="{spec.alt}"></div>
        <aside>
          <h3>怎么读这张图</h3>
          <ol>{bullets}</ol>
          <p class="takeaway">{spec.takeaway}</p>
        </aside>
      </div>
      <script type="application/json" class="slide-notes">{notes}</script>
    </div>"""


def main() -> None:
    for spec in FIGURE_SPECS:
        path = FIGURES / spec.filename
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(path)

    slides = "\n".join(slide_html(index, spec) for index, spec in enumerate(FIGURE_SPECS))
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="generator" content="html-slides v0.9.4">
  <title>SH3 全部图与读图说明</title>
  <style>
    /* === BASIC WHITE FIGURE DECK === */
    :root {{ --ink:#182026; --muted:#58646d; --accent:#006a86; --line:#d3d9dd; --paper:#fff; }}
    * {{ box-sizing:border-box; }}
    html,body {{ width:100%; height:100%; margin:0; overflow:hidden; background:var(--paper); color:var(--ink); font-family:"Noto Sans CJK SC","Source Han Sans SC","Microsoft YaHei",sans-serif; }}
    .deck {{ position:relative; width:100vw; height:100vh; height:100dvh; overflow:hidden; }}
    .slide {{ position:absolute; inset:0; height:100vh; height:100dvh; overflow:hidden; display:grid; grid-template-rows:auto minmax(0,1fr); gap:clamp(.6rem,1.5vh,1.2rem); padding:clamp(1rem,3.2vh,2.5rem) clamp(1.2rem,3.6vw,4rem); opacity:0; visibility:hidden; pointer-events:none; }}
    .slide.active {{ opacity:1; visibility:visible; pointer-events:auto; }}
    .kicker {{ margin:0 0 clamp(.2rem,.6vh,.45rem); color:var(--accent); font-size:clamp(.7rem,.9vw,.92rem); font-weight:700; letter-spacing:.06em; text-transform:uppercase; }}
    h2 {{ margin:0; font-size:clamp(1.45rem,2.6vw,2.8rem); line-height:1.14; }}
    .figure-layout {{ min-height:0; max-height:min(82vh,54rem); display:grid; grid-template-columns:minmax(0,3.2fr) minmax(15rem,1fr); gap:clamp(1rem,2.2vw,2.5rem); align-items:center; }}
    .image-wrap {{ min-width:0; min-height:0; display:flex; justify-content:center; align-items:center; }}
    img {{ display:block; max-width:100%; max-height:min(72vh,46rem); width:auto; height:auto; object-fit:contain; }}
    aside {{ min-width:0; max-height:min(72vh,46rem); overflow:hidden; font-size:clamp(.78rem,1.08vw,1.1rem); line-height:1.43; }}
    h3 {{ margin:0 0 clamp(.4rem,1vh,.8rem); color:var(--accent); font-size:clamp(1rem,1.45vw,1.45rem); }}
    ol {{ margin:0; padding-left:clamp(1.1rem,1.6vw,1.5rem); }}
    li+li {{ margin-top:clamp(.3rem,.8vh,.6rem); }}
    .takeaway {{ margin:clamp(.7rem,1.6vh,1.1rem) 0 0; color:var(--accent); font-weight:700; }}
    .counter {{ position:fixed; right:clamp(.8rem,1.8vw,1.5rem); top:clamp(.7rem,1.5vh,1.1rem); color:var(--muted); font-size:clamp(.68rem,.9vw,.88rem); }}
    .nav {{ position:fixed; right:clamp(.8rem,1.8vw,1.5rem); bottom:clamp(.7rem,1.5vh,1.1rem); display:flex; gap:clamp(.35rem,.7vw,.65rem); }}
    button {{ border:1px solid var(--line); border-radius:999px; padding:clamp(.28rem,.55vw,.45rem) clamp(.55rem,.9vw,.8rem); background:#fff; color:var(--ink); cursor:pointer; font:inherit; }}
    @media (max-width:860px) {{ .figure-layout {{ grid-template-columns:1fr; grid-template-rows:minmax(0,1fr) auto; }} img {{ max-height:min(48vh,26rem); }} aside {{ font-size:clamp(.68rem,1.8vw,.86rem); }} }}
    @media (max-height:700px) {{ .slide {{ padding-top:clamp(.8rem,2vh,1.2rem); padding-bottom:clamp(.8rem,2vh,1.2rem); }} img {{ max-height:min(62vh,28rem); }} aside {{ font-size:clamp(.67rem,.94vw,.84rem); line-height:1.30; }} }}
    @media (max-height:600px) {{ img {{ max-height:min(56vh,22rem); }} h2 {{ font-size:clamp(1.2rem,2.2vw,1.8rem); }} }}
    @media (max-height:500px) {{ img {{ max-height:min(48vh,16rem); }} aside {{ line-height:1.20; }} .nav {{ display:none; }} }}
    @media (prefers-reduced-motion:reduce) {{ .slide {{ transition:none; }} }}
  </style>
</head>
<body>
  <div class="deck" id="deck">{slides}
  </div>
  <div class="counter" id="counter"></div>
  <nav class="nav" aria-label="幻灯片导航">
    <button type="button" id="prevButton" aria-label="上一页">←</button>
    <button type="button" id="nextButton" aria-label="下一页">→</button>
  </nav>
  <script>
    /* === ZERO-DEPENDENCY NAVIGATION === */
    (() => {{
      const slides=[...document.querySelectorAll('.slide')];
      const counter=document.getElementById('counter');
      let current=0;
      const update=()=>{{
        slides.forEach((slide,index)=>slide.classList.toggle('active',index===current));
        counter.textContent=`${{current+1}} / ${{slides.length}}`;
        history.replaceState(null,'',`#${{current+1}}`);
        const node=slides[current].querySelector('.slide-notes');
        if(node){{try{{console.log(JSON.parse(node.textContent));}}catch(_){{}}}}
      }};
      window.goTo=(index)=>{{current=Math.max(0,Math.min(slides.length-1,Number(index)||0));update();}};
      window.next=()=>window.goTo(current+1);
      window.prev=()=>window.goTo(current-1);
      document.getElementById('prevButton').addEventListener('click',window.prev);
      document.getElementById('nextButton').addEventListener('click',window.next);
      document.addEventListener('keydown',(event)=>{{
        if(['ArrowRight','PageDown',' '].includes(event.key)){{event.preventDefault();window.next();}}
        else if(['ArrowLeft','PageUp'].includes(event.key)){{event.preventDefault();window.prev();}}
        else if(event.key==='Home'){{window.goTo(0);}}
        else if(event.key==='End'){{window.goTo(slides.length-1);}}
      }});
      const initial=Number.parseInt(location.hash.slice(1),10);
      if(Number.isFinite(initial))current=Math.max(0,Math.min(slides.length-1,initial-1));
      update();
    }})();
  </script>
</body>
</html>
"""
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"{OUTPUT}\t{OUTPUT.stat().st_size} bytes\t{len(FIGURE_SPECS)} embedded figures")


if __name__ == "__main__":
    main()
