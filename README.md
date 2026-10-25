# 电磁场可视化 · Electric Field Visualization

用 p5.js 做的实时电场流场动画：一个**有限长均匀带电平板** + **三个可拖动的点电荷**，
1400 个粒子沿电场方向运动，在拖尾层上留下连续的场线。

![预览](docs/preview.png)

## 快速开始

```bash
git clone <你的仓库地址>
cd Electromagnetic-Field-Visualization
```

然后**双击 `index.html`** 就能看。不需要安装、不需要构建、不需要本地服务器。

> 唯一的要求是能访问 CDN（页面从 `jsdelivr` 加载 p5@2.3.4）。离线使用的话，把
> `lib/p5.min.js` 下载到本地，改一下 `<script src>` 即可。

## 操作

| 操作 | 效果 |
|---|---|
| 拖动电荷 | 实时改变整个电场，粒子自然被新场带过去 |
| `R` | 电荷复位 + 清空拖尾 |

拖动时旧的拖尾会在约 0.5 秒内淡出，看起来像场在「重组」。

### 值得试的几个构型

| 拖法 | 会看到 |
|---|---|
| 负电荷拖到平板正上方 | 场线从扇形散开收拢成**垂直平行束**（匀强场） |
| 两个正电荷靠近 | 中间出现**暗区**（场强零点），两侧场线被挤开绕行 |
| 正电荷拖到负电荷旁 | 放射状变成**偶极子**的纺锤形 |
| 负电荷拖到画面外缘 | 平板一侧不再汇聚，改为向四周发散 |

## 物理模型

**点电荷**

```
E = k·q·(r − r₀) / |r − r₀|³
```

**有限长均匀线电荷**（平板，侧视图，解析解而非数值积分）

```
Ex = kλ·(1/ra − 1/rb)
Ey = kλ·(b/rb − a/ra) / y

a = x − L/2      b = x + L/2
ra = √(a² + y²)  rb = √(b² + y²)
```

平板被当作一条均匀线电荷处理——这是「薄板侧视」的标准近似。

## 实现要点

**1. 两块画布**

拖尾需要「不清空画布、只让它变淡」。但如果平板、电荷、文字也画在同一块画布上，
它们会每帧叠加一次，几十帧后糊成实心色块。所以拆成两层：

```js
// ① 拖尾层：不清空，只按 alpha 衰减
trail.background(BG[0], BG[1], BG[2], TRAIL_ALPHA);
trail.push();
trail.translate(W / 2, H / 2);      // ← 和静态层用同一个原点
trail.line(s.x0, s.y0, s.x1, s.y1);
trail.pop();

// ② 主画布：每帧彻底重画
background(BG[0], BG[1], BG[2]);
image(trail, 0, 0);
drawPlate(); drawCharges(); drawLabels();
```

`TRAIL_ALPHA` 决定线有多长：越小拖尾越长。

**2. 只取场方向，不取场强**

粒子速度恒定，否则靠近平板时会被 `1/y` 奇异性甩飞出画面。场线密度本身已经
表达了场强大小。

**3. 固定微小偏角**

每个粒子带一个 ±0.03 rad 的固定偏角。不加的话，两个正源之间会出现一条极度
锐利的分界线（电场零点处的分界线，separatrix），看起来像贴图接缝。

**4. 归一化长度尺度**

点电荷是 `1/r²`、线电荷是 `1/r` 量级，直接相加会让平板强出几百倍。所有坐标
先除以 `R0 = 100` 再计算，让两者可比。

## 目录

```
.
├─ index.html            # 全部代码（单文件，无构建）
├─ docs/preview.png      # README 截图
└─ tools/
   ├─ sim.mjs            # 离线：驱动粒子系统，累积成密度图
   └─ preview_flow.py    # 离线：密度图 → docs/preview.png
```

`tools/` 只是为了让 README 有张静态图，**和页面运行完全无关**。它从 `index.html`
里抽出 `<script>` 直接执行，保证预览用的数学和页面是同一份代码。

```bash
node tools/sim.mjs           # → tools/density.bin
python tools/preview_flow.py # → docs/preview.png
```

依赖：Node 18+、Python 3.9+（numpy、Pillow）。

## 已知限制

- 需要联网（从 CDN 载入 p5）
- 平板本身不可拖动，长度与线电荷密度写死在 `PLATE` 常量里
- **尚未实现视频导出**：拖拽会破坏帧的确定性，导出时需先把三个电荷的位置写死
- 场强只用颜色和密度表达，没有等势线

## 参数

集中在 `index.html` 顶部：

```js
const CHARGES = [...]        // 电荷位置与电荷量
const PLATE = {x, y, len, lambda}
const N_PARTICLES = 1400     // 粒子数：多→密，少→线条更分明
const SPEED       = 3.4      // 速度：快→线更直更长
const TRAIL_ALPHA = 8        // 拖尾衰减：小→线更长
```

## 许可

MIT（如果你要加 LICENSE 文件的话）。底层依赖 [p5.js](https://p5js.org/)，LGPL-2.1。
