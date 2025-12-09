# ⟶̽ जय श्री ༢།म > 𝟑🙏🚩
import os
import re
import math
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL

# -------------------
# Config / Cache
# -------------------
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

CANVAS_W, CANVAS_H = 1280, 720
LEFT_W = CANVAS_W // 2
RIGHT_W = CANVAS_W - LEFT_W

# Fonts
def load_font(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

title_font = load_font("RiteshMusic/assets/thumb/font2.ttf", 44)
meta_font = load_font("RiteshMusic/assets/thumb/font.ttf", 22)
duration_font = load_font("RiteshMusic/assets/thumb/font2.ttf", 30)

# -------------------
# Helpers
# -------------------
def clean_text(t): return re.sub(r"\s+", " ", (t or "")).strip()

def fit_and_fill(im, target_w, target_h):
    iw, ih = im.size
    target_ratio = target_w / target_h
    img_ratio = iw / ih
    if img_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        left = (iw - new_w) // 2
        im = im.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        top = (ih - new_h) // 2
        im = im.crop((0, top, iw, top + new_h))
    return im.resize((target_w, target_h), Image.LANCZOS)

def average_color(img, box=None):
    try:
        crop = img.crop(box) if box else img
        stat = ImageStat.Stat(crop.convert("RGB"))
        return tuple(int(x) for x in stat.mean)
    except: return (100,100,120)

def overlay_tint(img, color=(10,20,40), alpha=60):
    overlay = Image.new("RGBA", img.size, (color[0], color[1], color[2], alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay)

# -------------------
# Visual Effects
# -------------------
def cinematic_grade(img):
    img = img.convert("RGBA")
    img = ImageEnhance.Color(img).enhance(1.35)
    img = ImageEnhance.Contrast(img).enhance(1.18)
    img = ImageEnhance.Brightness(img).enhance(1.02)
    tint = Image.new("RGBA", img.size, (6,14,35,64))
    return Image.alpha_composite(img, tint)

def adaptive_neon_glow(base, sample_box=None, intensity=40):
    r,g,b = average_color(base, sample_box)
    glow = base.copy().filter(ImageFilter.GaussianBlur(20))
    overlay_color = (min(255,r+70), min(255,g//2+100), min(255,b+40), intensity)
    overlay = Image.new("RGBA", base.size, overlay_color)
    return Image.alpha_composite(glow.convert("RGBA"), overlay)

def anime_outline(img, threshold=30):
    try:
        edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
        edges = ImageEnhance.Contrast(edges).enhance(3.2)
        edges = edges.point(lambda p: 255 if p > threshold else 0)
        edge_rgba = Image.new("RGBA", img.size, (0,0,0,0))
        edge_rgba.paste(edges.convert("RGBA"), (0,0), mask=edges)
        color_edge = overlay_tint(edge_rgba, color=(10,10,20), alpha=180)
        return Image.alpha_composite(img.convert("RGBA"), color_edge)
    except: return img

def glass_panel(w,h):
    panel = Image.new("RGBA",(w,h),(255,255,255,48))
    blur = Image.new("RGBA",(w,h),(255,255,255,90)).filter(ImageFilter.GaussianBlur(18))
    panel = Image.alpha_composite(panel, blur)
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle((6,6,w-6,h-6), radius=28, outline=(255,255,255,60), width=2)
    return panel

def floating_thumbnail_shadows(img):
    base = Image.new("RGBA", img.size, (0,0,0,0))
    big = ImageEnhance.Brightness(img.copy().filter(ImageFilter.GaussianBlur(44))).enhance(0.28)
    med = ImageEnhance.Brightness(img.copy().filter(ImageFilter.GaussianBlur(22))).enhance(0.35)
    rim = overlay_tint(img.copy().filter(ImageFilter.GaussianBlur(12)), color=(120,40,160), alpha=60)
    base.alpha_composite(big,(18,36))
    base = Image.alpha_composite(base, med)
    base = Image.alpha_composite(base, rim)
    return base

def canvas_gradient_overlay(w,h):
    grad = Image.new("RGBA",(w,h),(0,0,0,0))
    draw = ImageDraw.Draw(grad)
    for i in range(h):
        t = i/h
        r = int(12+(1-t)*20)
        g = int(10+(1-t)*18)
        b = int(22+t*60)
        alpha = int(28+(1-abs(t-0.45))*40)
        draw.line([(0,i),(w,i)],fill=(r,g,b,alpha))
    vign = Image.new("L",(w,h),0)
    for y in range(h):
        for x in range(w):
            dx=(x-w/2)/(w/2)
            dy=(y-h/2)/(h/2)
            d=math.sqrt(dx*dx+dy*dy)
            val=int(max(0,min(255,(d-0.45)*350)))
            vign.putpixel((x,y),val)
    vign = vign.filter(ImageFilter.GaussianBlur(40))
    grad.putalpha(vign)
    return grad

def left_panel_glow(panel):
    glow = panel.filter(ImageFilter.GaussianBlur(18))
    overlay = Image.new("RGBA", panel.size, (255,255,255,35))
    return Image.alpha_composite(glow, overlay)

# -------------------
# Main thumbnail generator
# -------------------
async def get_thumb(videoid: str) -> str:
    out_path = os.path.join(CACHE_DIR, f"{videoid}_final.png")
    if os.path.exists(out_path): return out_path

    # fetch YouTube info
    try:
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        data = await results.next()
        info = data.get("result",[{}])[0]
        title = clean_text(info.get("title","Unknown Title"))
        thumb = info.get("thumbnails",[{}])[0].get("url",YOUTUBE_IMG_URL)
        duration = info.get("duration")
        views = info.get("viewCount",{}).get("short","Unknown Views")
        channel = info.get("channel",{}).get("name","")
    except: title, thumb = "Unknown Title", YOUTUBE_IMG_URL; duration, views, channel = None, "Unknown Views", ""

    duration_text = "LIVE" if not duration or str(duration).lower() in ["","live","live now"] else duration

    temp_thumb = os.path.join(CACHE_DIR, f"temp_{videoid}.png")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb) as resp:
                if resp.status==200:
                    async with aiofiles.open(temp_thumb,"wb") as f: await f.write(await resp.read())
                else: temp_thumb=None
    except: temp_thumb=None

    base = Image.new("RGBA",(CANVAS_W,CANVAS_H),(6,8,12,255))
    right_img = Image.open(temp_thumb).convert("RGBA") if temp_thumb and os.path.exists(temp_thumb) else Image.new("RGBA",(RIGHT_W,CANVAS_H),(50,50,60,255))
    right_img = fit_and_fill(right_img,RIGHT_W,CANVAS_H)
    sample_box=(max(0,RIGHT_W//3), CANVAS_H//3, RIGHT_W-10, CANVAS_H-CANVAS_H//3)
    right_img = cinematic_grade(right_img)
    right_img = anime_outline(right_img,threshold=35)
    shadow = floating_thumbnail_shadows(right_img)
    base.alpha_composite(shadow,(LEFT_W-18,28))
    base.alpha_composite(right_img,(LEFT_W,0))

    left = glass_panel(LEFT_W,CANVAS_H)
    left = left_panel_glow(left)
    base.alpha_composite(left,(0,0))

    grad = canvas_gradient_overlay(CANVAS_W,CANVAS_H)
    base = Image.alpha_composite(base,grad)

    draw = ImageDraw.Draw(base)
    padding = 56
    text_x = padding
    text_y = padding
    max_w = LEFT_W - padding*2

    words = title.split()
    lines, cur = [], ""
    for w in words:
        test=(cur+" "+w).strip()
        tw,_ = draw.textsize(test,font=title_font)
        if tw<=max_w: cur=test
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    lines=lines[:3]

    for line in lines:
        draw.text((text_x,text_y),line,font=title_font,fill=(255,255,255,255))
        text_y+=title_font.getsize(line)[1]+8

    text_y+=8
    if channel:
        draw.text((text_x,text_y),channel,font=meta_font,fill=(220,220,220,220))
        text_y+=30

    draw.text((text_x,text_y),f"Views: {views}",font=meta_font,fill=(200,200,200,200))
    text_y+=36

    dur_w,dur_h = draw.textsize(duration_text,font=duration_font)
    badge_w,badge_h = dur_w+36,dur_h+22
    badge = Image.new("RGBA",(badge_w,badge_h),(255,255,255,72))
    bd=ImageDraw.Draw(badge)
    bd.rounded_rectangle((0,0,badge_w,badge_h),radius=14,fill=(255,255,255,72))
    base.alpha_composite(badge,(text_x,text_y))
    draw.text((text_x+18,text_y+10),duration_text,font=duration_font,fill=(6,6,6,255))

    sym_box=Image.new("RGBA",(110,48),(255,255,255,28))
    sdraw=ImageDraw.Draw(sym_box)
    sdraw.rounded_rectangle((0,0,110,48),radius=12,fill=(255,255,255,28))
    sdraw.text((12,8),"★ PREMIUM",font=meta_font,fill=(255,232,140,255))
    base.alpha_composite(sym_box,(20,20))

    neon = adaptive_neon_glow(base.crop((LEFT_W,0,CANVAS_W,CANVAS_H)),sample_box=sample_box,intensity=36)
    neon = neon.filter(ImageFilter.GaussianBlur(26))
    neon_layer = Image.new("RGBA",base.size,(0,0,0,0))
    neon_layer.alpha_composite(neon,(LEFT_W-6,0))
    final = Image.alpha_composite(neon_layer,base)
    final = ImageEnhance.Sharpness(final).enhance(1.05)
    final = ImageEnhance.Contrast(final).enhance(1.03)

    try: final.save(out_path)
    except: final.convert("RGB").save(out_path)

    try: 
        if temp_thumb and os.path.exists(temp_thumb): os.remove(temp_thumb)
    except: pass

    return out_path
