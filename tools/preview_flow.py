"""把 tools/density.bin + scene.json 渲染成 docs/preview.png（README 用的离线截图）。

密度图由 sim.mjs 按拖尾层的真实衰减累积而来，颜色和几何都从 scene.json 读，
所以改了配色 / 电荷之后重跑这两个脚本，截图会自动同步。

用法：
    node tools/sim.mjs
    python tools/preview_flow.py
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

scene = json.load(open(os.path.join(HERE, "scene.json"), encoding="utf-8"))
GW, GH = scene["gw"], scene["gh"]
W, H = GW, GH
NC = max(1, len(scene["colors"]))

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
raw = np.fromfile(os.path.join(HERE, "density.bin"), dtype=np.float32).reshape(NC, GH, GW)

acc = np.zeros((GH, GW, 3), np.float32)

# 所有通道共用一个参考值：各通道分别归一化会把亮度拉平，颜色就洗成灰白
allv = np.concatenate([raw[k][raw[k] > 0] for k in range(NC)])
REF = np.percentile(allv, 99.5) if allv.size else 1.0

for k in range(NC):
    v = np.clip(raw[k] / max(REF, 1e-6), 0, 1) ** 0.8
    rgb = scene["colors"][k] if k < len(scene["colors"]) else [150, 150, 150]
    for c in range(3):
        acc[:, :, c] += v * (rgb[c] / 255.0)

# 软压高光：直接相加会在多通道重叠处截断成白色，这里按亮度做色调映射，
# 保留色相，只压缩动态范围（类似胶片曲线）
s = acc.sum(axis=2, keepdims=True) + 1e-6
tone = 1.0 - np.exp(-2.2 * s)
rgb = acc / s * tone
img = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
img = Image.fromarray(img, "RGB").resize((W, H), Image.BICUBIC)

# ---------------------------------------------------------------- 静态元素
d = ImageDraw.Draw(img, "RGBA")
OX, OY = W // 2, H // 2


def X(v):
    return v + OX


def Y(v):
    return v + OY


def fmt_q(q):
    if abs(q) < 0.005:
        return "0"
    return ("+" if q > 0 else "\u2212") + f"{abs(q):.2f}q"


# 平板
pl = scene["plate"]
px, py, plen, prgb = pl["x"], pl["y"], pl["len"], tuple(pl["rgb"])
for i in range(6, 0, -1):
    d.rounded_rectangle(
        [X(px - plen / 2 - i * 3), Y(py - 9 - i * 2),
         X(px + plen / 2 + i * 3), Y(py + 9 + i * 2)],
        radius=8, fill=prgb + (9,),
    )
d.rounded_rectangle(
    [X(px - plen / 2), Y(py - 9), X(px + plen / 2), Y(py + 9)],
    radius=7, fill=(12, 12, 14, 255), outline=prgb + (190,), width=2,
)

f_plus = load_font(FONT_BOLD, 13)
n_plus = max(3, round(plen / 70))
for i in range(n_plus):
    d.text((X(px - plen / 2 + (i + 0.5) * (plen / n_plus)), Y(py)), "+",
           font=f_plus, fill=(196, 182, 172, 200), anchor="mm")

# 电荷
f_lab = load_font(FONT_REG, 20)
for c in scene["charges"]:
    cx, cy, q = c["x"], c["y"], c["q"]
    rgb = tuple(c["rgb"])
    r = 11 + min(abs(q), 2.6) * 6

    for k in range(7, 0, -1):
        rr = r + k * 6.5
        d.ellipse([X(cx - rr), Y(cy - rr), X(cx + rr), Y(cy + rr)], fill=rgb + (11,))

    d.ellipse([X(cx - r), Y(cy - r), X(cx + r), Y(cy + r)], fill=rgb)
    glyph = "+" if q > 0 else ("\u2212" if q < 0 else "\u00b7")
    d.text((X(cx), Y(cy + 1)), glyph,
           font=load_font(FONT_BOLD, int(r * 1.1)), fill=(10, 10, 12), anchor="mm")

    d.text((X(cx + r + 14), Y(cy - r - 10)), fmt_q(q), font=f_lab,
           fill=(168, 162, 155), anchor="lm")

# 平板标签
d.text((X(px + plen / 2 + 22), Y(py)), "\u6709\u9650\u957f\u5e26\u7535\u5e73\u677f",
       font=load_font(FONT_REG, 18), fill=(130, 124, 118), anchor="lm")

# 说明
fa = load_font(FONT_REG, 17)
cap_a = ("\u7535\u573a\u7ebf\u4ece\u6b63\u7535\u8377\u4e0e\u5e73\u677f\u8868\u9762\u6d41\u51fa\uff0c"
         "\u7ec8\u6b62\u4e8e\u8d1f\u7535\u8377\u6216\u5ef6\u4f38\u81f3\u65e0\u7a77\u8fdc")
wa = d.textlength(cap_a, font=fa)
d.rounded_rectangle([24, 20, 24 + wa + 28, 56], radius=9, fill=(0, 0, 0, 190))
d.text((38, 30), cap_a, font=fa, fill=(110, 104, 98), anchor="la")

os.makedirs(DOCS, exist_ok=True)
out = os.path.join(DOCS, "preview.png")
img.save(out, optimize=True)
print("saved", out, img.size, f"channels={NC}")
