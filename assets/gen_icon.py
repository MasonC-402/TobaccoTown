#!/usr/bin/env python3
"""Generate icon.png for TobaccoTown (run once; output is committed to the repo)."""

from PIL import Image, ImageDraw, ImageFilter
import math

SIZE = 1024


def make_icon(size: int) -> Image.Image:
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # ── Rounded-square background ──────────────────────────────────────
    bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle(
        [0, 0, s - 1, s - 1],
        radius=int(s * 0.215),
        fill=(26, 25, 23, 255),
    )
    img.alpha_composite(bg)

    # ── Cigar (drawn flat, then rotated 28°) ──────────────────────────
    cx, cy = s // 2, s // 2
    clen = int(s * 0.70)
    cw   = int(s * 0.115)
    r    = cw // 2

    x0, x1 = cx - clen // 2, cx + clen // 2
    y0, y1 = cy - r, cy + r

    cigar = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(cigar)

    BODY_DK   = (105, 60, 16, 255)   # dark tobacco brown (shadow side)
    BODY_MID  = (138, 84, 28, 255)   # mid tobacco brown
    BODY_HI   = (172, 116, 52, 255)  # highlight (top edge)
    BAND      = (196, 122, 46, 255)  # gold band — matches app accent #C47A2E
    BAND_EDGE = (160, 95, 28, 255)   # darker edge lines on band
    CAP       = (68, 36, 6, 255)     # head/cap end (very dark)
    ASH       = (208, 205, 196, 255) # ash grey
    ASH_TIP   = (228, 225, 218, 255) # lighter ash tip
    EMBER     = (230, 70, 8, 255)    # glowing ember

    # Body base (full cigar shape)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=BODY_MID)

    # Shadow on bottom half — darker strip
    shadow_h = int(cw * 0.42)
    d.rectangle([x0 + r, y1 - shadow_h, x1 - r, y1], fill=BODY_DK)

    # Highlight on top edge — thin bright strip
    hi_h = int(cw * 0.22)
    d.rectangle([x0 + r, y0, x1 - r, y0 + hi_h], fill=BODY_HI)

    # Gold band — ~16% from the cap (left) end
    bx  = x0 + int(clen * 0.14)
    bw  = int(cw * 0.62)
    d.rectangle([bx, y0, bx + bw, y1], fill=BAND)
    # Thin dark lines at band edges for realism
    edge = max(2, int(s * 0.003))
    d.rectangle([bx, y0, bx + edge, y1], fill=BAND_EDGE)
    d.rectangle([bx + bw - edge, y0, bx + bw, y1], fill=BAND_EDGE)

    # Cap end (left) — dark rounded dome
    d.ellipse([x0, y0, x0 + cw, y1], fill=CAP)

    # Ash tip (right)
    ash_w = int(cw * 0.55)
    d.ellipse([x1 - r, y0, x1 + ash_w, y1], fill=ASH)
    # Brighter ash tip centre
    tip_r = int(r * 0.55)
    d.ellipse(
        [x1 + ash_w // 2 - tip_r, cy - tip_r,
         x1 + ash_w // 2 + tip_r, cy + tip_r],
        fill=ASH_TIP,
    )

    # Glowing ember dot
    er = int(r * 0.46)
    ex = x1 + ash_w - er - int(s * 0.004)
    d.ellipse([ex - er, cy - er, ex + er, cy + er], fill=EMBER)

    # Soft glow around ember
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gr = er * 3
    gd.ellipse([ex - gr, cy - gr, ex + gr, cy + gr], fill=(230, 100, 20, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=int(s * 0.018)))
    cigar.alpha_composite(glow)

    # ── Rotate & composite ────────────────────────────────────────────
    rotated = cigar.rotate(28, resample=Image.BICUBIC, center=(cx, cy))
    img.alpha_composite(rotated)

    # ── Subtle smoke wisps above the lit end ──────────────────────────
    # Find where the ember ends up after rotation (approximate)
    angle_rad = math.radians(28)
    dx = (ex - cx) * math.cos(angle_rad) - (cy - cy) * math.sin(angle_rad)
    dy = -(ex - cx) * math.sin(angle_rad)
    ex_r = int(cx + dx)
    ey_r = int(cy + dy)

    smoke = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(smoke)
    sw = int(s * 0.012)
    for i, (ox, oy, alpha) in enumerate([
        (0,    -int(s*0.07), 38),
        (-int(s*0.022), -int(s*0.13), 28),
        (int(s*0.018),  -int(s*0.19), 18),
        (-int(s*0.01),  -int(s*0.25), 10),
    ]):
        sd.ellipse([
            ex_r + ox - sw, ey_r + oy - sw,
            ex_r + ox + sw, ey_r + oy + sw,
        ], fill=(200, 195, 185, alpha))
    smoke = smoke.filter(ImageFilter.GaussianBlur(radius=int(s * 0.014)))
    img.alpha_composite(smoke)

    return img


if __name__ == "__main__":
    icon = make_icon(SIZE)
    icon.save("icon.png")
    print("Wrote assets/icon.png")
