"""把 tools/density.bin 渲染成 docs/preview.png（README 用的离线截图）。

密度图是 sim.mjs 按拖尾层的真实衰减累积出来的，所以这张图可以近似
代表 p5 页面运行到稳态时的样子（少了抗锯齿和合成细节）。

用法：
    node tools/sim.mjs
    python tools/preview_flow.py
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

GW, GH = 1600, 900
W, H = 1600, 900

# ---------------------------------------------------------------- 字体
FONT_BOLD = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_REG = [
    r"C:\Windows\Fonts\msyh.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def load_font(candidates, size):
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------- 密度 → 颜色
raw = np.fromfile(os.path.join(HERE, "density.bin"), dtype=np.float32).reshape(3, GH, GW)

# 每个源单独归一化（99.5 分位），避免个别热点把整体压暗
COLS = [(251, 113, 133), (167, 139, 250), (34, 211, 238)]   # A / C / 平板
acc = np.zeros((GH, GW, 3), np.float32)
for k in range(3):
    p = raw[k]
    ref = np.percentile(p[p > 0], 99.5) if (p > 0).any() else 1.0
    v = np.clip(p / max(ref, 1e-6), 0, 1) ** 0.72
    for c in range(3):
        acc[:, :, c] += v * (COLS[k][c] / 255.0)

img = (np.clip(acc, 0, 1) ** 0.85 * 255).astype(np.uint8)
img = Image.fromarray(img, "RGB").resize((W, H), Image.BICUBIC)

# ---------------------------------------------------------------- 静态元素
d = ImageDraw.Draw(img, "RGBA")
OX, OY = W // 2, H // 2


def X(v):
    return v + OX


def Y(v):
    return v + OY


# 平板
px, py, plen = 0, 210, 620
for i in range(6, 0, -1):
    d.rounded_rectangle(
        [X(px - plen / 2 - i * 3), Y(py - 9 - i * 2),
         X(px + plen / 2 + i * 3), Y(py + 9 + i * 2)],
        radius=8, fill=(34, 211, 238, 9),
    )
d.rounded_rectangle(
    [X(px - plen / 2), Y(py - 9), X(px + plen / 2), Y(py + 9)],
    radius=7, fill=(10, 20, 34, 255), outline=(34, 211, 238, 200), width=2,
)
f_plus = load_font(FONT_BOLD, 13)
for i in range(9):
    d.text((X(px - plen / 2 + (i + 0.5) * (plen / 9)), Y(py)), "+",
           font=f_plus, fill=(248, 113, 113), anchor="mm")

# 电荷
CH = [(-470, -180, 1.0, (251, 113, 133)),
      (170, -260, -1.3, (96, 165, 250)),
      (600, 120, 0.7, (167, 139, 250))]
for cx, cy, q, col in CH:
    r = 11 + abs(q) * 6
    for k in range(7, 0, -1):
        rr = r + k * 6.5
        d.ellipse([X(cx - rr), Y(cy - rr), X(cx + rr), Y(cy + rr)], fill=col + (14,))
    d.ellipse([X(cx - r), Y(cy - r), X(cx + r), Y(cy + r)], fill=col)
    d.text((X(cx), Y(cy)), "+" if q > 0 else "\u2212",
           font=load_font(FONT_BOLD, int(r * 1.25)), fill=(4, 7, 12), anchor="mm")

f_lab = load_font(FONT_REG, 21)
for (cx, cy, q, _), nm, (ox, oy) in zip(
    CH, ["+1.0q", "\u22121.3q", "+0.7q"], [(34, -36), (36, -8), (34, -32)]
):
    d.text((X(cx + ox), Y(cy + oy)), nm, font=f_lab, fill=(203, 213, 225), anchor="lm")
d.text((X(px + plen / 2 + 22), Y(py)), "\u6709\u9650\u957f\u5e26\u7535\u5e73\u677f   +\u03bb",
       font=load_font(FONT_REG, 19), fill=(148, 163, 184), anchor="lm")

# 说明
fa = load_font(FONT_REG, 17)
cap_a = ("\u7535\u573a\u7ebf\u4ece\u6b63\u7535\u8377\u4e0e\u5e73\u677f\u8868\u9762\u6d41\u51fa\uff0c"
         "\u7ec8\u6b62\u4e8e\u8d1f\u7535\u8377\u6216\u5ef6\u4f38\u81f3\u65e0\u7a77\u8fdc")
wa = d.textlength(cap_a, font=fa)
d.rounded_rectangle([24, 20, 24 + wa + 28, 56], radius=9, fill=(4, 7, 12, 190))
d.text((38, 30), cap_a, font=fa, fill=(100, 116, 139), anchor="la")

os.makedirs(DOCS, exist_ok=True)
out = os.path.join(DOCS, "preview.png")
img.save(out, optimize=True)
print("saved", out, img.size)
