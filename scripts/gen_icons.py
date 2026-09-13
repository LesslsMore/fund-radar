# -*- coding: utf-8 -*-
# 按设计稿 docs/icon-radar-v1.svg 用 PIL 生成全套图标 (与 SVG 视觉一致)
# 产物: frontend/public/icons/{pwa-192,pwa-512,pwa-maskable-512,apple-touch-icon}.png + favicon.svg
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(BASE, "frontend", "public", "icons")
os.makedirs(ICON_DIR, exist_ok=True)

FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT = r"C:\Windows\Fonts\msyh.ttc"


def gradient_bg(d, S):
    top, bot = (30, 111, 224), (12, 61, 128)
    for y in range(S):
        t = y / S
        d.line([(0, y), (S, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))


def draw_radar(canvas, S, sc):
    d = ImageDraw.Draw(canvas)
    cx, cy, R = 256 * sc, 246 * sc, 212 * sc
    w = lambda x: max(1, round(x * sc))
    rings = [(R, w(12), (255, 255, 255, 26)),
             (R, max(1, w(2)), (191, 224, 255, 90)),
             (152 * sc, max(1, w(2)), (255, 255, 255, 40)),
             (92 * sc, max(1, w(2)), (255, 255, 255, 56))]
    for r, lw, color in rings:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=lw)
    # 十字准线
    d.line([30 * sc, cy, 482 * sc, cy], fill=(255, 255, 255, 26), width=max(1, w(1.6)))
    d.line([cx, 20 * sc, cx, 472 * sc], fill=(255, 255, 255, 26), width=max(1, w(1.6)))


def draw_sweep(overlay, S, sc):
    """扫描扇形: 径向渐隐, 用 18 层环带楔形近似"""
    d = ImageDraw.Draw(overlay)
    cx, cy, R = 256 * sc, 246 * sc, 212 * sc
    steps = 18
    a0, a1 = -51, 0  # PIL 角度: -51° -> 0° (右上扇形)
    for i in range(steps):
        r1 = R * i / steps
        r2 = R * (i + 1) / steps
        alpha = int(255 * (0.36 * (1 - r2 / R) + 0.02))
        bbox = [cx - r2, cy - r2, cx + r2, cy + r2]
        d.pieslice(bbox, a0, a1, fill=(255, 255, 255, alpha))


def draw_blip(overlay, S, sc, x, y, r, rgb):
    d = ImageDraw.Draw(overlay)
    cx, cy = x * sc, y * sc
    rr = r * sc
    steps = 26
    for i in range(steps, 0, -1):
        rad = rr * i / steps
        a = int(235 * (1 - i / steps) ** 2)
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=rgb + (a,))
    d.ellipse([cx - rr * 0.22, cy - rr * 0.22, cx + rr * 0.22, cy + rr * 0.22], fill=rgb + (255,))


def draw_text(img, S, sc, with_caption=True):
    d = ImageDraw.Draw(img)
    cx, cy = 256 * sc, 246 * sc
    fs = int(188 * sc)
    font = ImageFont.truetype(FONT_BOLD, fs)
    # 阴影
    bbox = d.textbbox((0, 0), "基", font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    off = max(2, round(6 * sc))
    d.text((cx - w / 2 - bbox[0] + off, cy - h / 2 - bbox[1] + off), "基", font=font,
           fill=(10, 47, 99, 150))
    d.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), "基", font=font, fill=(255, 255, 255, 255))
    if with_caption:
        fs2 = int(42 * sc)
        font2 = ImageFont.truetype(FONT, fs2)
        text = "基金雷达"
        spacing = 10 * sc
        widths = [d.textbbox((0, 0), ch, font=font2)[2] for ch in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = 256 * sc - total / 2
        y = 474 * sc - fs2 * 0.75
        for ch, cw in zip(text, widths):
            d.text((x, y), ch, font=font2, fill=(255, 255, 255, 235))
            x += cw + spacing


def render(size, maskable=False, with_caption=True):
    sc = size / 512
    if maskable:
        # 背景铺满, 内容缩放 78% 居中 (安全区)
        inner = int(size * 0.78)
        tile = render(inner, maskable=False, with_caption=with_caption)
        img = Image.new("RGB", (size, size))
        d = ImageDraw.Draw(img)
        gradient_bg(d, size)
        img.paste(tile, ((size - inner) // 2, (size - inner) // 2))
        return img
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient_bg(ImageDraw.Draw(img), size)
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_radar(overlay, size, sc)
    draw_sweep(overlay, size, sc)
    draw_blip(overlay, size, sc, 352, 128, 46, (125, 255, 212))
    draw_blip(overlay, size, sc, 150, 330, 34, (255, 212, 121))
    img = Image.alpha_composite(img, overlay).convert("RGBA")
    draw_text(img, size, sc, with_caption=True)
    # 圆角裁切
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=round(size * 112 / 512), fill=255)
    img.putalpha(mask)
    return img


render(192).save(os.path.join(ICON_DIR, "pwa-192.png"))
render(512).save(os.path.join(ICON_DIR, "pwa-512.png"))
render(512, maskable=True).save(os.path.join(ICON_DIR, "pwa-maskable-512.png"))
render(180).save(os.path.join(ICON_DIR, "apple-touch-icon.png"))

# favicon.svg: 无底部文字的简化版 (与设计同构)
svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1e6fe0"/><stop offset="0.55" stop-color="#1257b8"/>
      <stop offset="1" stop-color="#0c3d80"/>
    </linearGradient>
    <linearGradient id="sw" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#fff" stop-opacity="0.38"/>
      <stop offset="1" stop-color="#9fd4ff" stop-opacity="0.02"/>
    </linearGradient>
    <clipPath id="r"><rect width="512" height="512" rx="112"/></clipPath>
  </defs>
  <g clip-path="url(#r)">
    <rect width="512" height="512" fill="url(#bg)"/>
    <circle cx="256" cy="246" r="212" fill="none" stroke="#bfe0ff" stroke-opacity="0.35" stroke-width="4"/>
    <circle cx="256" cy="246" r="152" fill="none" stroke="#fff" stroke-opacity="0.16" stroke-width="3"/>
    <circle cx="256" cy="246" r="92" fill="none" stroke="#fff" stroke-opacity="0.22" stroke-width="3"/>
    <path d="M256,246 L468,246 A212,212 0 0 0 385,86 Z" fill="url(#sw)"/>
    <circle cx="352" cy="128" r="40" fill="#7dffd4" opacity="0.3"/>
    <circle cx="352" cy="128" r="11" fill="#8fffd8"/>
    <text x="256" y="246" text-anchor="middle" dominant-baseline="central"
          font-family="Microsoft YaHei,PingFang SC,sans-serif" font-weight="bold"
          font-size="188" fill="#fff">基</text>
  </g>
</svg>'''
open(os.path.join(ICON_DIR, "favicon.svg"), "w", encoding="utf-8").write(svg)

# 同步一份到 docs 供 README 引用
render(256).save(os.path.join(BASE, "docs", "icon-256.png"))
print("icons generated ->", ICON_DIR)
