#!/usr/bin/env python3
"""Generate icon.png for TobaccoTown (run once; output is committed to the repo)."""

from PIL import Image, ImageDraw, ImageFilter
import math

SIZE = 1024

BG      = ( 26,  25,  23, 255)   # #1a1917
GOLD    = (196, 122,  46, 255)   # #C47A2E  — app accent
GOLD_HI = (230, 162,  72, 255)   # highlight / veins
GOLD_DK = (132,  76,  16, 255)   # midrib / shadow


def _leaf_polygon(cx: int, cy: int, L: int, W: int, N: int = 180):
    """
    Parametric tobacco-leaf polygon.
    t = –π/2  →  tip  (top,  cy–L)
    t = +π/2  →  base (bottom, cy+L)
    Leaf is widest slightly below the midpoint (realistic for Nicotiana tabacum).
    """
    pts = []
    for i in range(N):
        t = -math.pi / 2 + 2 * math.pi * i / N

        sin_t = math.sin(t)
        cos_t = math.cos(t)

        # Width modifier: leaf is ~22% wider in the lower half
        w_mod = 1.0 + 0.22 * max(0.0, sin_t)
        x = W * cos_t * w_mod

        # Slight vertical stretch to keep tip sharp
        y = L * sin_t

        pts.append((cx + x, cy + y))

    return [(int(p[0]), int(p[1])) for p in pts]


def make_icon(size: int) -> Image.Image:
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # ── Background ────────────────────────────────────────────────────
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, s - 1, s - 1], radius=int(s * 0.215), fill=BG
    )

    cx, cy = s // 2, s // 2
    L = int(s * 0.330)   # half-height of leaf
    W = int(s * 0.240)   # max half-width

    # ── Leaf drawn on its own canvas, then rotated ────────────────────
    leaf_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d        = ImageDraw.Draw(leaf_img)

    # Leaf body
    poly = _leaf_polygon(cx, cy, L, W)
    d.polygon(poly, fill=GOLD)

    # Highlight — thin bright region on the upper-left face
    hi_poly = _leaf_polygon(cx - int(s * 0.025), cy, int(L * 0.96), int(W * 0.30))
    d.polygon(hi_poly, fill=GOLD_HI)

    # Re-draw the full leaf to clean up the highlight edges
    # (keep highlight only as a thin crescent on the left)
    mid_poly = _leaf_polygon(cx + int(s * 0.012), cy, int(L * 0.97), int(W * 0.90))
    d.polygon(mid_poly, fill=GOLD)

    # ── Midrib (central vein) ─────────────────────────────────────────
    midrib_w = max(4, int(s * 0.013))
    d.line([(cx, cy - L + int(s * 0.01)),
            (cx, cy + L - int(s * 0.01))],
           fill=GOLD_DK, width=midrib_w)

    # ── Lateral veins (branch at angle off the midrib) ────────────────
    vein_w = max(2, int(s * 0.005))
    for frac in [0.22, 0.38, 0.54, 0.68, 0.80]:
        my = cy - L + int(2 * L * frac)
        # Width of the leaf at this height
        t_here = math.asin((frac * 2 - 1))          # maps frac in [0,1] → [-π/2, π/2]
        w_here = W * math.cos(t_here) * (1 + 0.22 * max(0.0, math.sin(t_here))) * 0.88
        for sign in (-1, 1):
            vx = int(cx + sign * w_here)
            vy = my - int(L * 0.09)                  # veins angle slightly upward
            d.line([(cx, my), (vx, vy)], fill=GOLD_DK, width=vein_w)

    # ── Petiole (short stem at leaf base) ────────────────────────────
    pet_len = int(L * 0.22)
    pet_w   = max(4, int(s * 0.018))
    d.line([(cx, cy + L - int(s * 0.005)),
            (cx, cy + L + pet_len)],
           fill=GOLD_DK, width=pet_w)

    # ── Slight rotation for elegance ──────────────────────────────────
    rotated = leaf_img.rotate(-14, resample=Image.BICUBIC, center=(cx, cy))
    img.alpha_composite(rotated)

    # ── Very faint glow around the leaf for depth ─────────────────────
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    gd.polygon(_leaf_polygon(cx, cy, int(L * 1.06), int(W * 1.08)),
               fill=(196, 122, 46, 28))
    glow = glow.rotate(-14, resample=Image.BICUBIC, center=(cx, cy))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=int(s * 0.025)))
    img.alpha_composite(glow)

    return img


if __name__ == "__main__":
    make_icon(SIZE).save("icon.png")
    print("Wrote assets/icon.png")
