from dataclasses import dataclass
from typing import Optional, Tuple, List, Callable
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, random, hashlib, os

# ------------------ Data model ------------------
@dataclass
class TeamSpec:
    location: str
    mascot: str
    primary: Optional[str] = None   # e.g. "#0A3161"
    secondary: Optional[str] = None # e.g. "#C8102E"
    abbrev: Optional[str] = None    # e.g. "NYC"
    template: str = "circle"        # "circle" | "shield" | "cap"
    field_background: bool = True   # faint diamond behind the mark
    seed: int | None = None         # optional seed for deterministic logos

# ------------------ Utilities ------------------
def _hex_to_rgb(h: str) -> Tuple[int,int,int]:
    h = h.strip().lstrip('#')
    if len(h) == 3: h = ''.join(ch*2 for ch in h)
    if len(h) != 6: raise ValueError(f"Bad color: {h}")
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def _blend(c1, c2, t: float):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))

def _contrast_color(rgb):
    r,g,b = rgb
    lum = 0.2126*r + 0.7152*g + 0.0722*b
    return (20,20,20) if lum > 180 else (240,240,240)

def _seed_from_name(*parts) -> int:
    h = hashlib.sha1('||'.join(p.lower() for p in parts if p).encode('utf-8')).hexdigest()
    return int(h[:8], 16)

def _categorize(mascot: str) -> str:
    m = mascot.lower()
    if any(k in m for k in ["eagle","hawk","falcon","bird","owl","raven","phoenix"]): return "bird"
    if any(k in m for k in ["tiger","lion","panther","cougar","wildcat","jaguar","bear","grizzly","wolf","fox","coyote","bulldog","husky"]): return "beast"
    if any(k in m for k in ["shark","marlin","dolphin","whale","piranh","sting","ray"]): return "sea"
    if any(k in m for k in ["dragon","knight","wizard","sorcer","witch","demon"]): return "mythic"
    if any(k in m for k in ["bolt","thunder","lightning","storm"]): return "storm"
    if any(k in m for k in ["rebel","raider","ranger","guardian","soldier","warrior","samurai","ninja"]): return "human"
    if any(k in m for k in ["robot","gear","machine","steampunk","mech"]): return "machine"
    if any(k in m for k in ["diamond","royal","king","queen","ace","joker","card"]): return "royal"
    return "classic"

PALETTES = {
    "bird":    [("#0a3161","#c8102e"),("#004c54","#a5acaf"),("#14213d","#fca311")],
    "beast":   [("#1d3557","#e63946"),("#22223b","#f2e9e4"),("#0b132b","#6fffe9")],
    "sea":     [("#003049","#669bbc"),("#001219","#94d2bd"),("#023047","#8ecae6")],
    "mythic":  [("#2b2d42","#ef233c"),("#3a0ca3","#f72585"),("#111827","#8b5cf6")],
    "storm":   [("#111827","#f59e0b"),("#0f172a","#38bdf8"),("#1f2937","#a3e635")],
    "human":   [("#1f2937","#f97316"),("#2f3e46","#cad2c5"),("#3730a3","#f59e0b")],
    "machine": [("#0f172a","#94a3b8"),("#1e293b","#22d3ee"),("#111827","#9ca3af")],
    "royal":   [("#2c3e50","#f1c40f"),("#3d0066","#ffd60a"),("#1b1b3a","#e43d40")],
    "classic": [("#0a3161","#c8102e"),("#00274c","#ffcb05"),("#004225","#ffdd00")]
}

def choose_colors(spec: TeamSpec, rnd: random.Random):
    if spec.primary and spec.secondary:
        return _hex_to_rgb(spec.primary), _hex_to_rgb(spec.secondary)
    cat = _categorize(spec.mascot)
    pal = rnd.choice(PALETTES[cat])
    return _hex_to_rgb(pal[0]), _hex_to_rgb(pal[1])

# ------------------ Drawing primitives ------------------
def _draw_radial_gradient(img: Image.Image, inner_rgb, outer_rgb):
    w,h = img.size; cx, cy = w//2, h//2; max_r = (cx**2 + cy**2) ** 0.5
    px = img.load()
    for y in range(h):
        for x in range(w):
            r = ((x-cx)**2 + (y-cy)**2) ** 0.5 / max_r
            px[x,y] = _blend(inner_rgb, outer_rgb, min(1.0, r))

def _draw_field_background(img: Image.Image, color=(255,255,255), alpha=40, scale=0.65) -> Image.Image:
    if img.mode != "RGBA": base = img.convert("RGBA")
    else: base = img
    w,h = base.size; cx, cy = w//2, int(h*0.55); size = int(min(w,h)*0.45*scale)
    pts = [(cx, cy-size), (cx+size, cy), (cx, cy+size), (cx-size, cy)]
    fill = (*color, alpha)
    overlay = Image.new("RGBA", (w,h), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.polygon(pts, outline=fill, width=max(2, size//20))
    s2 = int(size*0.6)
    pts2 = [(cx, cy-int(s2)), (cx+int(s2), cy), (cx, cy+int(s2)), (cx-int(s2), cy)]
    od.polygon(pts2, outline=fill, width=max(2, size//24))
    b = max(3, size//25)
    for px,py in pts2: od.rectangle([px-b, py-b, px+b, py+b], fill=fill)
    od.arc([cx-size, cy-size, cx+size, cy+size], start=200, end=340, fill=fill, width=max(2, size//24))
    od.ellipse([cx-b, cy-b, cx+b, cy+b], fill=fill)
    base.alpha_composite(overlay)
    if img is not base: return base.convert("RGB")
    return base

def _stroke_text(draw, xy, text, font, fill, stroke_fill, stroke_width):
    x,y = xy
    for dx in range(-stroke_width, stroke_width+1):
        for dy in range(-stroke_width, stroke_width+1):
            if dx*dx+dy*dy <= stroke_width*stroke_width:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_fill)
    draw.text((x,y), text, font=font, fill=fill)

def _center_text(draw, w, text, font):
    bbox = draw.textbbox((0,0), text, font=font); text_w = bbox[2]-bbox[0]
    return (w - text_w)//2

def _load_font(preferred: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    candidates = []
    if preferred and os.path.exists(preferred): candidates.append(preferred)
    candidates += [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try: return ImageFont.truetype(path, size=size)
        except Exception: continue
    return ImageFont.load_default()

# ------------------ Templates ------------------
def _render_circle_badge(spec: TeamSpec, rnd: random.Random, size=1024, font_path: Optional[str]=None) -> Image.Image:
    primary, secondary = choose_colors(spec, rnd)
    img = Image.new("RGB", (size,size))
    _draw_radial_gradient(img, _blend(primary,(0,0,0),0.2), _blend(primary,(0,0,0),0.6))
    w,h = img.size; draw = ImageDraw.Draw(img, 'RGBA')
    center = (w//2, h//2); radius = int(min(w,h)*0.45)
    draw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius],
                 outline=secondary, width=int(size*0.04))
    r2 = int(radius*0.82)
    draw.ellipse([center[0]-r2, center[1]-r2, center[0]+r2, center[1]+r2],
                 outline=(255,255,255,100), width=int(size*0.01))
    if spec.field_background:
        img = _draw_field_background(img, color=(255,255,255), alpha=36, scale=0.62)
        draw = ImageDraw.Draw(img, 'RGBA')
    stripe_h = int(size*0.18)
    draw.rectangle([0, center[1]-stripe_h//2, w, center[1]+stripe_h//2], fill=(*secondary, 200))
    city = spec.location.upper(); nick = spec.mascot.upper()
    monogram = (spec.abbrev or (city[:1] + nick[:1])).upper()
    f_mono = _load_font(font_path, int(size*0.42))
    f_city = _load_font(font_path, int(size*0.12))
    f_nick = _load_font(font_path, int(size*0.16))
    tcolor = _contrast_color(secondary)
    mx = _center_text(draw, w, monogram, f_mono); my = center[1] - int(size*0.28)
    _stroke_text(draw, (mx, my), monogram, f_mono, fill=tcolor, stroke_fill=(0,0,0,200), stroke_width=max(2, int(size*0.01)))
    cx = _center_text(draw, w, city, f_city)
    _stroke_text(draw, (cx, center[1]-int(f_city.size*0.6)), city, f_city, fill=_contrast_color(secondary), stroke_fill=(0,0,0,180), stroke_width=max(2,int(size*0.005)))
    nx = _center_text(draw, w, nick, f_nick)
    _stroke_text(draw, (nx, center[1]+int(f_city.size*0.1)), nick, f_nick, fill=(255,255,255), stroke_fill=(0,0,0,200), stroke_width=max(2,int(size*0.006)))
    gloss = Image.new("L", (w,h), 0); gdraw = ImageDraw.Draw(gloss)
    gdraw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]], fill=80)
    gloss = gloss.filter(ImageFilter.GaussianBlur(radius=int(size*0.04)))
    img = Image.composite(Image.new("RGB",(w,h),(255,255,255)), img, gloss.point(lambda p: int(p*0.4)))
    return img

def _render_shield(spec: TeamSpec, rnd: random.Random, size=1024, font_path: Optional[str]=None) -> Image.Image:
    primary, secondary = choose_colors(spec, rnd)
    base = Image.new("RGB", (size,size))
    _draw_radial_gradient(base, _blend(primary,(0,0,0),0.15), _blend(primary,(0,0,0),0.55))
    w,h = base.size; draw = ImageDraw.Draw(base, 'RGBA')
    top = int(h*0.18); mid = int(h*0.52); bot = int(h*0.86); pad = int(w*0.18)
    shield = [(pad, top), (w-pad, top), (w-pad-int(w*0.03), mid), (w//2, bot), (pad+int(w*0.03), mid)]
    draw.polygon(shield, fill=(*secondary, 220), outline=(0,0,0,200))
    draw.line(shield+[shield[0]], fill=(0,0,0,200), width=int(size*0.01))
    if spec.field_background:
        base = _draw_field_background(base, color=(255,255,255), alpha=32, scale=0.6)
        draw = ImageDraw.Draw(base, 'RGBA')
    inset = [(x+(w*0.02 if x<w//2 else -w*0.02), y+(h*0.02)) for (x,y) in shield]
    draw.polygon(inset, outline=(255,255,255,140), width=int(size*0.008))
    city = spec.location.upper(); nick = spec.mascot.upper()
    monogram = (spec.abbrev or (city[:1] + nick[:1])).upper()
    f_mono = _load_font(font_path, int(size*0.40))
    f_city = _load_font(font_path, int(size*0.12))
    f_nick = _load_font(font_path, int(size*0.18))
    tcolor = _contrast_color(secondary)
    mx = _center_text(draw, w, monogram, f_mono); my = int(h*0.27)
    _stroke_text(draw, (mx,my), monogram, f_mono, fill=tcolor, stroke_fill=(0,0,0,220), stroke_width=int(size*0.012))
    ribbon_y = int(h*0.52)
    draw.rectangle([int(w*0.18), ribbon_y-int(size*0.06), int(w*0.82), ribbon_y+int(size*0.02)], fill=(*primary, 220))
    cx = _center_text(draw, w, city, f_city)
    _stroke_text(draw, (cx, ribbon_y-int(f_city.size*0.85)), city, f_city, fill=_contrast_color(primary), stroke_fill=(0,0,0,200), stroke_width=int(size*0.006))
    nx = _center_text(draw, w, nick, f_nick)
    _stroke_text(draw, (nx, int(h*0.60)), nick, f_nick, fill=(255,255,255), stroke_fill=(0,0,0,220), stroke_width=int(size*0.008))
    return base

def _render_cap(spec: TeamSpec, rnd: random.Random, size=1024, font_path: Optional[str]=None) -> Image.Image:
    primary, secondary = choose_colors(spec, rnd)
    img = Image.new("RGB", (size,size), primary)
    if spec.field_background:
        img = _draw_field_background(img, color=(255,255,255), alpha=22, scale=0.7)
    draw = ImageDraw.Draw(img, 'RGBA')
    monogram = (spec.abbrev or (spec.location[:1] + spec.mascot[:1])).upper()
    f_mono = _load_font(font_path, int(size*0.58))
    x = _center_text(draw, size, monogram, f_mono); y = int(size*0.18)
    _stroke_text(draw, (x,y), monogram, f_mono, fill=secondary, stroke_fill=(0,0,0,200), stroke_width=int(size*0.04))
    draw.rectangle([int(size*0.2), int(size*0.78), int(size*0.8), int(size*0.80)], fill=(*_contrast_color(primary), 140))
    return img

# ------------------ Public API ------------------
def generate_logo(
    spec: TeamSpec,
    size: int = 1024,
    font_path: Optional[str] = None,
    rnd: Optional[random.Random] = None,
) -> Image.Image:
    seed = spec.seed or _seed_from_name(spec.location, spec.mascot)
    rnd = rnd or random.Random(seed)
    t = (spec.template or "circle").lower()
    if t == "auto":
        t = rnd.choice(["circle", "shield", "cap"])
    if t == "circle":
        return _render_circle_badge(spec, rnd, size=size, font_path=font_path)
    if t == "shield":
        return _render_shield(spec, rnd, size=size, font_path=font_path)
    if t == "cap":
        return _render_cap(spec, rnd, size=size, font_path=font_path)
    raise ValueError(f"Unknown template: {spec.template}")

def save_logo(img: Image.Image, out_path: str, dpi: int=300):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, format="PNG", dpi=(dpi,dpi))

def batch_generate(
    teams: List[TeamSpec],
    out_dir: str,
    size: int = 1024,
    font_path: Optional[str] = None,
    callback: Optional[Callable[[TeamSpec, str], None]] = None,
):
    os.makedirs(out_dir, exist_ok=True)
    for t in teams:
        seed = t.seed or _seed_from_name(t.location, t.mascot)
        rnd = random.Random(seed)
        img = generate_logo(t, size=size, font_path=font_path, rnd=rnd)
        filename = f"{(t.abbrev or (t.location+' '+t.mascot)).replace(' ', '_').lower()}.png"
        path = os.path.join(out_dir, filename)
        save_logo(img, path)
        if callback:
            callback(t, path)
