# avatars.py
import hashlib
import random
from PIL import Image, ImageDraw

def _hex_to_rgb(h):
    h = h.strip().lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(rgb):  # not strictly needed, handy for debugging
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def _clamp(x, lo=0, hi=255):
    return max(lo, min(hi, x))

def _adjust(rgb, f=1.0, add=0):
    return tuple(_clamp(int(c * f + add)) for c in rgb)

def _blend(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

def _linear_gradient(draw, w, h, top_rgb, bot_rgb):
    for y in range(h):
        t = y / (h - 1)
        color = _blend(top_rgb, bot_rgb, t)
        draw.line([(0, y), (w, y)], fill=color)

def _pick(rng, seq):
    return seq[rng.randrange(0, len(seq))]

def _feature_from_hash(name, key, mod):
    # produce a stable int for a feature "bucket"
    h = hashlib.sha256((name + "|" + key).encode("utf-8")).hexdigest()
    return int(h[:8], 16) % mod

def _rng_from_name(name, primary_hex, secondary_hex):
    seed = hashlib.sha256((name + "|" + primary_hex + "|" + secondary_hex).encode("utf-8")).digest()
    # convert first 8 bytes to int for a stable seed
    return random.Random(int.from_bytes(seed[:8], "big"))

def generate_player_headshot(
    player_name: str,
    team_primary_hex: str,
    team_secondary_hex: str,
    size: int = 512,
    with_border: bool = False
) -> Image.Image:
    """
    Generate a deterministic illustrated headshot (chest-up) using name + team colors.
    - player_name: used as deterministic seed for facial features
    - team_primary_hex, team_secondary_hex: influence background/jersey/cap colors
    - size: output is size x size
    """
    rng = _rng_from_name(player_name.strip().lower(), team_primary_hex, team_secondary_hex)
    W = H = size

    primary = _hex_to_rgb(team_primary_hex)
    secondary = _hex_to_rgb(team_secondary_hex)
    bg_top = _blend(_adjust(secondary, 1.05), _adjust(primary, 0.9), 0.35)
    bg_bot = _blend(_adjust(primary, 0.9), _adjust(secondary, 0.8), 0.65)

    img = Image.new("RGB", (W, H), bg_top)
    draw = ImageDraw.Draw(img)
    _linear_gradient(draw, W, H, bg_top, bg_bot)

    # Framing & proportions
    cx, cy = W // 2, int(H * 0.54)
    head_w = int(W * 0.44)
    head_h = int(H * 0.40)
    neck_w = int(head_w * 0.36)
    neck_h = int(head_h * 0.22)
    torso_w = int(head_w * 1.6)
    torso_h = int(H * 0.35)

    # Feature palettes
    skin_tones = [
        (246, 221, 204), (234, 192, 152), (217, 160, 113),
        (186, 130, 94),  (140, 94, 66),   (100, 70, 50)
    ]
    hair_colors = [
        (30, 30, 30), (60, 45, 35), (90, 65, 45), (150, 110, 60),
        (200, 165, 90), (210, 190, 130), (80, 80, 80)
    ]

    # Deterministic feature choices
    skin = skin_tones[_feature_from_hash(player_name, "skin", len(skin_tones))]
    hair = hair_colors[_feature_from_hash(player_name, "hair", len(hair_colors))]
    has_beard = _feature_from_hash(player_name, "beard", 100) < 55
    beard_full = _feature_from_hash(player_name, "beard_style", 100) < 50
    mustache_only = (not beard_full) and has_beard and (_feature_from_hash(player_name, "stache", 100) < 40)
    brow_thick = _feature_from_hash(player_name, "brow", 100) < 50
    eye_sep = rng.uniform(0.18, 0.24)  # relative to head width
    eye_drop = rng.uniform(0.02, 0.035)
    mouth_w = rng.uniform(0.28, 0.36)  # relative to head width
    mouth_smile = rng.uniform(-0.4, 0.6)  # negative=frown, positive=smile
    ear_size = rng.uniform(0.10, 0.16)
    # Cap variations
    brim_depth = rng.uniform(0.08, 0.12)
    cap_crown = rng.uniform(0.24, 0.30)
    cap_two_tone = rng.random() < 0.45

    # Jersey & cap colors from team palette
    jersey_main = primary
    jersey_trim = secondary
    cap_main = primary
    cap_brim = secondary if cap_two_tone else _adjust(primary, 0.8)

    # Draw torso (jersey)
    torso_left = cx - torso_w // 2
    torso_top = H - torso_h
    draw.rounded_rectangle([torso_left, torso_top, torso_left + torso_w, H], radius=int(torso_w * 0.1), fill=jersey_main)
    # Jersey collar and piping
    collar_h = int(torso_h * 0.09)
    draw.rectangle([torso_left, torso_top, torso_left + torso_w, torso_top + collar_h], fill=_adjust(jersey_main, 0.85))
    # vertical piping
    pipe_w = max(2, size // 128)
    pipe_x1 = cx - int(torso_w * 0.12)
    pipe_x2 = cx + int(torso_w * 0.12)
    draw.rectangle([pipe_x1 - pipe_w, torso_top, pipe_x1 + pipe_w, H], fill=jersey_trim)
    draw.rectangle([pipe_x2 - pipe_w, torso_top, pipe_x2 + pipe_w, H], fill=jersey_trim)

    # Neck
    neck_left = cx - neck_w // 2
    neck_top = cy + head_h // 2 - int(neck_h * 0.45)
    draw.rounded_rectangle([neck_left, neck_top, neck_left + neck_w, neck_top + neck_h], radius=neck_w//5, fill=_adjust(skin, 0.98))

    # Head (oval)
    head_left = cx - head_w // 2
    head_top = cy - head_h // 2
    draw.ellipse([head_left, head_top, head_left + head_w, head_top + head_h], fill=skin)

    # Ears
    ear_w = int(head_w * ear_size)
    ear_h = int(head_h * (ear_size + 0.02))
    ear_y = cy - ear_h // 2
    draw.ellipse([head_left - ear_w//2, ear_y, head_left + ear_w//2, ear_y + ear_h], fill=_adjust(skin, 0.95))
    draw.ellipse([head_left + head_w - ear_w//2, ear_y, head_left + head_w + ear_w//2, ear_y + ear_h], fill=_adjust(skin, 0.95))

    # Hairline (under cap)
    hairline_h = int(head_h * 0.2)
    hairline_box = [head_left, head_top, head_left + head_w, head_top + hairline_h]
    draw.pieslice(hairline_box, start=0, end=180, fill=hair)

    # Cap
    cap_h = int(head_h * cap_crown)
    cap_box = [head_left, head_top - int(cap_h * 0.10), head_left + head_w, head_top + cap_h]
    draw.rounded_rectangle(cap_box, radius=int(head_w * 0.15), fill=cap_main)
    # Brim
    brim_h = int(head_h * brim_depth)
    brim_box = [head_left + int(head_w * 0.10), head_top + int(cap_h * 0.6), head_left + int(head_w * 0.90), head_top + int(cap_h * 0.6) + brim_h]
    draw.rounded_rectangle(brim_box, radius=brim_h//2, fill=cap_brim)

    # Eyes
    eye_y = int(cy - head_h * (0.08 - eye_drop))
    eye_dx = int(head_w * eye_sep)
    eye_r = max(2, size // 64)
    # whites
    for x in (cx - eye_dx, cx + eye_dx):
        draw.ellipse([x - eye_r*2, eye_y - eye_r, x + eye_r*2, eye_y + eye_r], fill=(240, 240, 240))
    # pupils
    pupil_r = max(2, size // 90)
    eye_color = (30, 30, 30)
    for x in (cx - eye_dx, cx + eye_dx):
        draw.ellipse([x - pupil_r, eye_y - pupil_r, x + pupil_r, eye_y + pupil_r], fill=eye_color)
    # brows
    brow_y = eye_y - int(head_h * 0.06)
    brow_th = max(2, size // 120) * (2 if brow_thick else 1)
    for x in (cx - eye_dx, cx + eye_dx):
        draw.line([(x - eye_r*2, brow_y), (x + eye_r*2, brow_y - int(head_h * 0.01))], width=int(brow_th), fill=hair)

    # Nose (simple)
    nose_y1 = eye_y + int(head_h * 0.04)
    nose_y2 = nose_y1 + int(head_h * 0.07)
    draw.line([(cx, nose_y1), (cx, nose_y2)], fill=_adjust(skin, 0.7), width=max(2, size // 160))

    # Mouth
    mw = int(head_w * mouth_w)
    mouth_y = nose_y2 + int(head_h * 0.06)
    # curve by sampling line segments
    segments = []
    curv = int((mouth_smile) * head_h * 0.02)
    left = cx - mw // 2
    right = cx + mw // 2
    mid = (left + right) // 2
    for x in range(left, right + 1, max(1, size // 256)):
        # quadratic-ish curve
        t = (x - mid) / (mw / 2)
        y = mouth_y - int(curv * (1 - t * t))
        segments.append((x, y))
    draw.line(segments, fill=(80, 60, 60), width=max(2, size // 160))

    # Facial hair
    if has_beard:
        beard_h = int(head_h * (0.22 if beard_full else 0.12))
        beard_top = mouth_y - int(head_h * 0.03)
        beard_box = [head_left + int(head_w * 0.12), beard_top, head_left + int(head_w * 0.88), beard_top + beard_h]
        draw.rounded_rectangle(beard_box, radius=int(head_w * 0.18), fill=_adjust(hair, 0.95))
    if mustache_only:
        stache_w = int(head_w * 0.32)
        stache_h = int(head_h * 0.06)
        stache_box = [cx - stache_w // 2, mouth_y - int(head_h * 0.09), cx + stache_w // 2, mouth_y - int(head_h * 0.09) + stache_h]
        draw.rounded_rectangle(stache_box, radius=stache_h//2, fill=_adjust(hair, 0.95))

    # Optional subtle border
    if with_border:
        pad = max(2, size // 100)
        draw.rectangle([pad, pad, W - pad, H - pad], outline=_adjust(primary, 0.7), width=max(2, size // 120))

    return img

# ---- PyQt6 helper (optional) ----
def pil_to_qpixmap(pil_img):
    """
    Convert PIL.Image to QPixmap (PyQt6).
    """
    from PyQt6.QtGui import QImage, QPixmap
    import io
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    qimg = QImage.fromData(buf.getvalue(), "PNG")
    return QPixmap.fromImage(qimg)
