# -*- coding: utf-8 -*-
"""将 AI 生成的背景图裁剪为 900x383 公众号封面并叠加标题文字"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = r"C:\Users\T\ZCodeProject\fund-radar\blog\img\Wide_banner_background_for_a_f_2026-09-19T10-45-02.png"
DST = r"C:\Users\T\ZCodeProject\fund-radar\blog\img\cover-900x383.png"
W, H = 900, 383

img = Image.open(SRC).convert("RGB")
sw, sh = img.size
# 居中裁剪到 900:383 比例
target_ratio = W / H
src_ratio = sw / sh
if src_ratio > target_ratio:
    new_w = int(sh * target_ratio)
    left = (sw - new_w) // 2
    img = img.crop((left, 0, left + new_w, sh))
else:
    new_h = int(sw / target_ratio)
    top = (sh - new_h) // 2
    img = img.crop((0, top, sw, top + new_h))
img = img.resize((W, H), Image.LANCZOS)

# 右侧压暗渐变，保证文字可读
overlay = Image.new("L", (W, H), 0)
od = ImageDraw.Draw(overlay)
for x in range(W):
    # 从 x=280 开始向右渐暗
    t = max(0.0, (x - 280) / (W - 280))
    od.line([(x, 0), (x, H)], fill=int(150 * t))
dark = Image.new("RGB", (W, H), (8, 18, 34))
img = Image.composite(dark, img, overlay)

draw = ImageDraw.Draw(img)
f_title = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 92)
f_sub = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 30)
f_tag = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)

def text_with_glow(d, xy, text, font, fill, glow=(0, 255, 170), radius=6):
    # 简易发光：先画多层偏移的半透明光晕
    gx, gy = xy
    for dx in range(-radius, radius + 1, 2):
        for dy in range(-radius, radius + 1, 2):
            d.text((gx + dx, gy + dy), text, font=font, fill=glow)
    d.text(xy, text, font=font, fill=fill)

# 标题（带阴影）
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.text((43, 88), "基金雷达", font=f_title, fill=(0, 0, 0, 200))
shadow = shadow.filter(ImageFilter.GaussianBlur(4))
img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
draw = ImageDraw.Draw(img)
text_with_glow(draw, (40, 85), "基金雷达", f_title, (255, 255, 255))

# 副标题
draw.text((46, 205), "夏普 · 收益 · 限额，一屏筛清", font=f_sub, fill=(255, 215, 100))

# 标签行
draw.text((46, 262), "0 元成本  |  AI 一晚打造  |  手机秒变 App", font=f_tag, fill=(180, 215, 235))

img.save(DST, "PNG")
print("saved:", DST)
