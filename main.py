#!/usr/bin/env python3
"""news-image-20261126 -- Builders 1 + 2.

Draws one 1024x1024 PNG summing up Thursday 26 November 2026 world news,
entirely in Python 3.13 standard library: own rasterizer, hand-built 5x7
bitmap font, zlib PNG encoder. Deterministic: no network, no randomness,
no clock, no environment input except MAKEFUN_OUTPUT_DIR.

FACTS: only the verified 26 Nov 2026 items in the brief. Nothing from the
DO NOT USE list (Tiangong 25 Nov, Libya 22/24 Nov, FIFA U-17 25 Nov,
Indian bank write-offs 25 Nov, Houthis/Saudi claim 25 Nov) appears here.

LAYOUT (matches the reference composition, drawn not photographed):
  masthead  : THE WORLD TODAY: THURSDAY, NOVEMBER 26, 2026 (gold date, huge)
  top row   : Swiss/Pyongyang | RUSSIA ~500,000 DEAD hero (largest) | US tariffs
  middle row: Ranchi protest | DRAWN WORLD MAP with glowing arcs | Turkey Trot
  bottom row: 5 panels (VP health checks Jakarta, Flipkart CEO,
              Iran Hormuz mines, Cairo tanker fire, Gukesh chess Geneva)
  extra row : 3 slim panels (US stocks fall, Colombia hostages freed,
              Netanyahu charges dropped) -- scale-2 captions, no scene
  bottom    : ticker (3 lines of secondary stories) + source strip

Every caption names PLACE + EVENT in large high-contrast text, legible
when the image is shown ~300px wide. Caption lines are wrapped to fit
their frame: at scale 2 a glyph advances 12px, so a 195px bottom panel
fits at most 15 chars per line and a 328px extra panel at most 26.
"""

import hashlib
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
NAVY = (6, 24, 46)        # page background
PANEL = (11, 36, 64)      # panel background
PANEL_DK = (8, 28, 52)    # darker panel background
GOLD = (255, 211, 77)     # masthead date / accents
GOLD_DK = (201, 154, 30)
WHITE = (255, 255, 255)
INK = (8, 16, 28)         # dark text on light banners
CYAN = (53, 196, 232)     # frame / map glow
CYAN_DK = (24, 90, 122)
CYAN_LT = (127, 231, 255)
RED = (229, 50, 45)       # hero / Swiss red
RED_DK = (92, 18, 18)
RED_MD = (58, 10, 10)
GREEN = (46, 160, 90)
GREY = (178, 196, 210)
MAP_LAND = (42, 122, 160)
MAP_LAND_LT = (74, 164, 204)

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits ('1' = ink). Hand-built for this entry.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ',': ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
}
BLANK = ("00000", "00000", "00000", "00000", "00000", "00000", "00000")


def text_width(s, scale):
    """Pixel width of s at the given font scale (6 px advance per glyph)."""
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def wrap_text(s, scale, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w pixels."""
    lines, cur = [], ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = c
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c):
        self.fill_rect(x, y, w, 1, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err, x, y = dx - dy, x0, y0
        while True:
            self.set(x, y, c)
            if x == x1 and y == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                    self.set(xx, yy, c)

    def circle(self, cx, cy, r, c):
        x, y, d = 0, r, 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y), (cx + x, cy - y),
                           (cx - x, cy - y), (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.set(px, py, c)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def poly_fill(self, pts, c):
        """Scanline fill of a polygon given as [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[k]), y, max(1, int(xs[k + 1]) - int(xs[k])), 1, c)

    def vgrad(self, x, y, w, h, top, bot):
        for i in range(h):
            t = i / max(1, h - 1)
            c = tuple(int(top[j] + (bot[j] - top[j]) * t) for j in range(3))
            self.fill_rect(x, y + i, w, 1, c)

    # -- text -------------------------------------------------------------
    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, BLANK)
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == '1':
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, c)
            cx += 6 * scale

    def text_centered(self, cx, y, s, scale, c):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, c)

    def lines_centered(self, cx, y, lines, scale, c, gap=4):
        yy = y
        for ln in lines:
            self.text_centered(cx, yy, ln, scale, c)
            yy += 7 * scale + gap
        return yy


def bezier_arc(cv, p0, p1, p2, glow, core, r_glow=4, r_core=2):
    """Glowing quadratic-bezier route arc: wide dim pass, then bright core."""
    pts = []
    steps = 48
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) * (1 - t) * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) * (1 - t) * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((int(x), int(y)))
    for (x, y) in pts:
        cv.disc(x, y, r_glow, glow)
    for (x, y) in pts:
        cv.disc(x, y, r_core, core)


# ---------------------------------------------------------------- layout
# Columns: left 8..318, centre 326..698 (hero/map are widest), right 706..1016.
TOP_Y, TOP_H = 148, 230
MID_Y, MID_H = 386, 230
BOT_Y, BOT_H = 624, 200
EXTRA_Y, EXTRA_H = 832, 72
TICK_Y, TICK_H = 912, 104
COLS = {"L": (8, 310), "C": (326, 372), "R": (706, 310)}
BOT_COLS = [(8, 195), (211, 195), (414, 195), (617, 195), (820, 195)]


def panel(cv, x, y, w, h, accent=CYAN, border=2):
    cv.fill_rect(x, y, w, h, PANEL)
    cv.rect(x, y, w, h, accent, border)
    cv.fill_rect(x, y, w, 4, accent)


def kicker(cv, x, y, w, s, scale=1, color=GREY):
    cv.text_centered(x + w // 2, y, s, scale, color)


def caption_banner(cv, x, y, w, h, lines, scale=2, bg=RED, fg=WHITE):
    """Bottom caption block: solid banner, large centred lines (PLACE + EVENT)."""
    cv.fill_rect(x, y, w, h, bg)
    cv.hline(x, y, w, GOLD)
    total = len(lines) * (7 * scale + 4) - 4
    yy = y + (h - total) // 2
    cv.lines_centered(x + w // 2, yy, lines, scale, fg, gap=4)


# ---------------------------------------------------------------- masthead
def draw_masthead(cv):
    cv.fill_rect(8, 8, 1008, 132, (10, 30, 60))
    cv.rect(8, 8, 1008, 132, GOLD, 2)
    cv.hline(8, 140 - 6, 1008, GOLD_DK)
    # Title, then the DATE in huge gold -- the most prominent text after the hero.
    cv.text_centered(512, 22, "THE WORLD TODAY", 4, WHITE)
    cv.text_centered(512, 62, "THURSDAY, NOVEMBER 26, 2026", 4, GOLD)
    cv.hline(212, 104, 600, GOLD)
    cv.disc(212, 104, 4, GOLD)
    cv.disc(812, 104, 4, GOLD)
    cv.text_centered(512, 112, "ONE DAY. EVERY REGION. WHAT HAPPENED.", 1, GREY)


# ---------------------------------------------------------------- top row
def draw_top_left_swiss(cv):
    x, w = COLS["L"]
    y, h = TOP_Y, TOP_H
    panel(cv, x, y, w, h, accent=RED)
    kicker(cv, x, y + 10, w, "DIPLOMATIC TENSION", 1, WHITE)
    kicker(cv, x, y + 24, w, "PYONGYANG, NORTH KOREA", 1, GOLD)
    # Drawn scene: Swiss flag (red square, white cross) beside a dark
    # diplomatic building whose gate is barred shut.
    cv.fill_rect(x + 28, y + 48, 92, 62, RED)
    cv.fill_rect(x + 62, y + 58, 24, 42, WHITE)
    cv.fill_rect(x + 46, y + 70, 56, 18, WHITE)
    cv.fill_rect(x + 168, y + 48, 114, 62, (20, 44, 74))
    cv.fill_rect(x + 168, y + 48, 114, 10, GOLD_DK)
    for bx in range(4):
        cv.fill_rect(x + 178 + bx * 28, y + 66, 12, 44, (120, 140, 165))
    cv.fill_rect(x + 168, y + 96, 114, 6, RED)
    cv.fill_rect(x + 168, y + 104, 114, 6, RED)
    cv.text_centered(x + w // 2, y + 118, "GATE BARRED - OFFICE SHUT", 1, GREY)
    caption_banner(cv, x, y + 140, w, 90,
                   ["SWISS DIPLOMATIC", "OFFICE CLOSED",
                    "PYONGYANG ORDERS", "SWISS OUT"],
                   scale=2, bg=RED, fg=WHITE)


def draw_top_hero_russia(cv):
    """HERO -- the largest panel, strongest visual: Russia's own figures,
    nearly 500,000 dead in the Ukraine war. Biggest type on the page."""
    x, w = COLS["C"]
    y, h = TOP_Y, TOP_H
    cv.fill_rect(x, y, w, h, RED_MD)
    cv.vgrad(x, y, w, 118, RED_DK, RED_MD)
    cv.rect(x, y, w, h, GOLD, 3)
    cv.rect(x + 5, y + 5, w - 10, h - 10, RED, 1)
    # Dark-red glow band behind the toll -- flat, so the gold numerals
    # stay high-contrast and nothing sits on top of the digits.
    cv.fill_rect(x + 12, y + 80, w - 24, 52, (120, 16, 16))
    cv.hline(x + 12, y + 80, w - 24, RED)
    cv.hline(x + 12, y + 131, w - 24, RED)
    kicker(cv, x, y + 10, w, "RUSSIA'S OWN FIGURES", 2, GOLD)
    kicker(cv, x, y + 32, w, "MOSCOW'S OWN COUNT", 1, WHITE)
    # "NEARLY" above the number, so it reads top to bottom:
    # NEARLY 500,000 DEAD IN UKRAINE WAR.
    cv.text_centered(x + w // 2, y + 54, "NEARLY", 3, WHITE)
    # The number itself, scale 6 -- the biggest numerals in the image.
    cv.text_centered(x + w // 2, y + 82, "500,000", 6, GOLD)
    # Row of memorial crosses along the bottom of the scene.
    for i in range(9):
        cx = x + 34 + i * 38
        cv.fill_rect(cx - 2, y + 148, 4, 18, (220, 220, 220))
        cv.fill_rect(cx - 8, y + 152, 16, 4, (220, 220, 220))
    caption_banner(cv, x, y + 172, w, 58,
                   ["DEAD IN UKRAINE WAR"], scale=3, bg=(20, 8, 8), fg=WHITE)


def draw_top_right_tariffs(cv):
    x, w = COLS["R"]
    y, h = TOP_Y, TOP_H
    panel(cv, x, y, w, h, accent=CYAN)
    kicker(cv, x, y + 10, w, "TRADE WAR", 1, WHITE)
    kicker(cv, x, y + 24, w, "WASHINGTON, USA", 1, GOLD)
    # Drawn scene: rising tariff bars with a % sign, over US stripes.
    for i in range(7):
        cv.fill_rect(x + 28 + i * 36, y + 104, 30, 6, RED if i % 2 else WHITE)
    bars = [18, 26, 22, 38, 34, 52, 66]
    for i, bh in enumerate(bars):
        cv.fill_rect(x + 34 + i * 36, y + 110 - bh, 22, bh,
                     RED if i == 6 else CYAN)
    cv.text_centered(x + w // 2, y + 118, "TARIFFS RISE - 15% ON TAIWAN", 1, GREY)
    caption_banner(cv, x, y + 140, w, 90,
                   ["TRUMP ANNOUNCES", "NEW TARIFFS",
                    "CHINA, JAPAN, EU HIT", "TAIWAN 15%"],
                   scale=2, bg=(10, 30, 60), fg=WHITE)


# ---------------------------------------------------------------- middle row
def draw_world_map(cv):
    """Central DRAWN world map with glowing route arcs (middle row, centre)."""
    x, w = COLS["C"]
    y, h = MID_Y, MID_H
    panel(cv, x, y, w, h, accent=CYAN)
    cv.text_centered(x + w // 2, y + 10, "WORLD MAP", 2, WHITE)
    cv.text_centered(x + w // 2, y + 28, "26 NOV 2026 - EVERY REGION", 1, GOLD)
    mx, my, mw, mh = x + 10, y + 46, w - 20, h - 56
    cv.fill_rect(mx, my, mw, mh, (7, 32, 58))
    # Faint graticule.
    for gx in range(1, 6):
        cv.hline(mx, my + gx * mh // 6, mw, (16, 52, 84))
        cv.fill_rect(mx + gx * mw // 6, my, 1, mh, (16, 52, 84))
    # Simplified continents, normalised coords inside the map box.
    continents = [
        [(0.02, 0.18), (0.10, 0.08), (0.22, 0.06), (0.28, 0.14), (0.24, 0.24),
         (0.18, 0.30), (0.12, 0.34), (0.05, 0.30)],                       # N America
        [(0.24, 0.42), (0.30, 0.40), (0.34, 0.48), (0.30, 0.62), (0.26, 0.58)],  # S America
        [(0.46, 0.14), (0.51, 0.10), (0.54, 0.16), (0.52, 0.24), (0.47, 0.22)],  # Europe
        [(0.46, 0.30), (0.54, 0.28), (0.58, 0.36), (0.55, 0.52), (0.50, 0.56),
         (0.47, 0.42)],                                                   # Africa
        [(0.62, 0.10), (0.74, 0.06), (0.87, 0.10), (0.92, 0.18), (0.88, 0.28),
         (0.78, 0.30), (0.70, 0.26), (0.63, 0.20)],                       # Asia
        [(0.80, 0.58), (0.88, 0.56), (0.92, 0.62), (0.86, 0.68), (0.80, 0.64)],  # Australia
    ]
    for poly in continents:
        pts = [(mx + int(px * mw), my + int(py * mh)) for (px, py) in poly]
        cv.poly_fill(pts, MAP_LAND)
        for i in range(len(pts)):
            cv.line(pts[i][0], pts[i][1], pts[(i + 1) % len(pts)][0],
                    pts[(i + 1) % len(pts)][1], MAP_LAND_LT)

    def pt(fx, fy):
        return (mx + int(fx * mw), my + int(fy * mh))

    # Glowing arcs between the day's places: Washington-Beijing,
    # Pyongyang-Geneva, Moscow-Kyiv, Jakarta-Cairo, Cairo-Hormuz.
    bezier_arc(cv, pt(0.12, 0.22), pt(0.45, 0.02), pt(0.84, 0.18),
               (18, 70, 100), CYAN_LT)
    bezier_arc(cv, pt(0.86, 0.16), pt(0.68, 0.02), pt(0.50, 0.18),
               (90, 70, 20), GOLD)
    bezier_arc(cv, pt(0.58, 0.12), pt(0.56, 0.06), pt(0.54, 0.16),
               (90, 20, 20), RED)
    bezier_arc(cv, pt(0.82, 0.48), pt(0.66, 0.60), pt(0.53, 0.32),
               (18, 70, 100), CYAN_LT)
    bezier_arc(cv, pt(0.53, 0.32), pt(0.60, 0.22), pt(0.66, 0.30),
               (90, 70, 20), GOLD)
    for (fx, fy) in [(0.12, 0.22), (0.84, 0.18), (0.86, 0.16), (0.50, 0.18),
                     (0.58, 0.12), (0.82, 0.48), (0.53, 0.32), (0.66, 0.30)]:
        px, py = pt(fx, fy)
        cv.disc(px, py, 5, GOLD)
        cv.disc(px, py, 3, WHITE)


# -- middle row, bottom row, extra row, ticker, source strip -------------
def draw_slot_ranchi(cv):
    # Ranchi tree-felling protest: "STOP TREE FELLING" /
    # "RANCHI POLICE DETAIN PROTESTERS". Signs: STOP TREE FELLING,
    # SAVE OUR FORESTS. Drawn scene: trees at left, crowd with placards.
    x, w = COLS["L"]
    y, h = MID_Y, MID_H
    panel(cv, x, y, w, h, accent=GREEN)
    kicker(cv, x, y + 10, w, "ENVIRONMENTAL PROTEST", 1, WHITE)
    kicker(cv, x, y + 24, w, "RANCHI, INDIA", 1, GOLD)
    # Trees, left: trunks + canopies.
    for tx, tr in ((x + 44, 22), (x + 88, 18)):
        cv.fill_rect(tx - 3, y + 96, 6, 28, (120, 80, 40))
        cv.disc(tx, y + 78, tr, (34, 120, 60))
        cv.disc(tx - 9, y + 86, tr - 8, (46, 150, 80))
    # Placards on sticks, held above the crowd.
    cv.fill_rect(x + 148, y + 48, 116, 22, WHITE)
    cv.rect(x + 148, y + 48, 116, 22, (14, 80, 44), 2)
    cv.text_centered(x + 206, y + 55, "STOP TREE FELLING", 1, (14, 80, 44))
    cv.fill_rect(x + 206, y + 70, 4, 34, (120, 80, 40))
    cv.fill_rect(x + 142, y + 76, 108, 22, (14, 80, 44))
    cv.rect(x + 142, y + 76, 108, 22, WHITE, 2)
    cv.text_centered(x + 196, y + 83, "SAVE OUR FORESTS", 1, WHITE)
    cv.fill_rect(x + 194, y + 98, 4, 8, (120, 80, 40))
    # Crowd: five protesters, heads + shoulders, below the placards.
    for i, c in enumerate((RED, GOLD, CYAN, WHITE, GREEN)):
        cx = x + 146 + i * 34
        cv.disc(cx, y + 104, 6, (220, 180, 140))
        cv.fill_rect(cx - 8, y + 110, 16, 14, c)
    cv.fill_rect(x + 16, y + 124, w - 32, 3, (30, 90, 50))
    caption_banner(cv, x, y + 140, w, 90,
                   ["STOP TREE FELLING", "RANCHI POLICE DETAIN",
                    "PROTESTERS"],
                   scale=2, bg=(14, 80, 44), fg=WHITE)


def draw_slot_turkey_trot(cv):
    # 51st Annual Alexandria Turkey Trot: "51ST ANNUAL TURKEY TROT" /
    # "HONORING 9/11 VICTIMS - 2,977 NAMES". Thanksgiving Day, Alexandria,
    # Virginia. Drawn scene: orange finish banner over a road of runners.
    x, w = COLS["R"]
    y, h = MID_Y, MID_H
    panel(cv, x, y, w, h, accent=GOLD)
    kicker(cv, x, y + 10, w, "THANKSGIVING TRADITION", 1, WHITE)
    kicker(cv, x, y + 24, w, "ALEXANDRIA, VIRGINIA, USA", 1, GOLD)
    # Autumn leaves drifting above the course.
    for lx, ly, lc in ((x + 40, y + 46, GOLD), (x + 96, y + 42, (255, 120, 40)),
                       (x + 200, y + 44, GOLD), (x + 262, y + 48, (255, 120, 40)),
                       (x + 150, y + 40, (255, 120, 40))):
        cv.disc(lx, ly, 3, lc)
    # Finish-line banner on two poles.
    cv.fill_rect(x + 24, y + 50, 4, 84, GREY)
    cv.fill_rect(x + 282, y + 50, 4, 84, GREY)
    cv.fill_rect(x + 28, y + 56, 254, 22, (200, 90, 10))
    cv.rect(x + 28, y + 56, 254, 22, GOLD, 2)
    cv.text_centered(x + w // 2, y + 63, "51ST ANNUAL TURKEY TROT", 1, WHITE)
    # Road + five runners in bright shirts.
    cv.fill_rect(x + 16, y + 118, w - 32, 16, (60, 70, 85))
    for i, c in enumerate((RED, GREEN, CYAN, GOLD, WHITE)):
        cx = x + 50 + i * 50
        cv.disc(cx, y + 106, 5, (220, 180, 140))
        cv.fill_rect(cx - 6, y + 111, 12, 15, c)
        cv.fill_rect(cx - 6, y + 126, 4, 8, (30, 30, 40))
        cv.fill_rect(cx + 2, y + 126, 4, 8, (30, 30, 40))
    caption_banner(cv, x, y + 140, w, 90,
                   ["51ST ANNUAL TURKEY TROT", "HONORING 9/11 VICTIMS",
                    "2,977 NAMES"],
                   scale=2, bg=(150, 70, 10), fg=WHITE)


# Bottom row: 5 panels, each 195px wide. At scale 2 a glyph advances
# 12px, so every caption line is at most 15 chars -- all lines below
# are wrapped to that limit so nothing spills past its frame. Uniform
# geometry: kickers at y+10/y+24, scene y+42..y+106, caption banner
# y+110..y+200 (90px, up to 5 lines).
def draw_bottom_vp(cv):
    # VP candidates undergo health checks: AMRAN AND SUGIONO AT RSPAD
    # JAKARTA. Scene: hospital cross sign + two candidates in white.
    x, w = BOT_COLS[0]
    y, h = BOT_Y, BOT_H
    panel(cv, x, y, w, h, accent=GREEN)
    kicker(cv, x, y + 10, w, "POLITICAL VETTING", 1, WHITE)
    kicker(cv, x, y + 24, w, "JAKARTA, INDONESIA", 1, GOLD)
    cv.fill_rect(x + 18, y + 52, 64, 52, WHITE)
    cv.fill_rect(x + 46, y + 60, 8, 36, RED)
    cv.fill_rect(x + 32, y + 72, 36, 8, RED)
    for cx in (x + 118, x + 158):
        cv.disc(cx, y + 66, 7, (220, 180, 140))
        cv.fill_rect(cx - 10, y + 74, 20, 30, WHITE)
        cv.fill_rect(cx - 2, y + 74, 4, 30, (40, 60, 90))
    cv.fill_rect(x + 16, y + 104, w - 32, 2, GREY)
    caption_banner(cv, x, y + 110, w, 90,
                   ["VP HEALTH", "CHECKS", "AMRAN, SUGIONO",
                    "RSPAD JAKARTA"],
                   scale=2, bg=(14, 80, 44), fg=WHITE)


def draw_bottom_flipkart(cv):
    # Flipkart CEO steps down: KRISHNAMURTHY TO LEAVE IN DECEMBER.
    # Scene: blue shopping bag + red down arrow.
    x, w = BOT_COLS[1]
    y, h = BOT_Y, BOT_H
    panel(cv, x, y, w, h, accent=CYAN)
    kicker(cv, x, y + 10, w, "BUSINESS TRANSITION", 1, WHITE)
    kicker(cv, x, y + 24, w, "BENGALURU, INDIA", 1, GOLD)
    cv.fill_rect(x + 78, y + 40, 4, 14, GOLD)
    cv.fill_rect(x + 113, y + 40, 4, 14, GOLD)
    cv.fill_rect(x + 78, y + 40, 39, 4, GOLD)
    cv.fill_rect(x + 60, y + 52, 75, 52, (20, 80, 180))
    cv.rect(x + 60, y + 52, 75, 52, CYAN_LT, 2)
    cv.text_centered(x + 97, y + 72, "FLIPKART", 1, GOLD)
    cv.fill_rect(x + 158, y + 52, 8, 40, RED)
    cv.poly_fill([(x + 150, y + 92), (x + 174, y + 92), (x + 162, y + 106)], RED)
    caption_banner(cv, x, y + 110, w, 90,
                   ["FLIPKART CEO", "STEPS DOWN", "KRISHNAMURTHY",
                    "OUT IN DECEMBER"],
                   scale=2, bg=(16, 60, 140), fg=WHITE)


def draw_bottom_iran(cv):
    # Iran: ships hit mines in Hormuz; TEHRAN WARNS SHIPS TO COORDINATE.
    # Scene: ship on the strait, two spiked mines in the water.
    x, w = BOT_COLS[2]
    y, h = BOT_Y, BOT_H
    panel(cv, x, y, w, h, accent=RED)
    kicker(cv, x, y + 10, w, "CONFLICT AT SEA", 1, WHITE)
    kicker(cv, x, y + 24, w, "STRAIT OF HORMUZ", 1, GOLD)
    cv.fill_rect(x + 14, y + 70, w - 28, 34, (16, 70, 110))
    cv.hline(x + 14, y + 78, w - 28, (40, 110, 160))
    cv.hline(x + 14, y + 90, w - 28, (40, 110, 160))
    cv.fill_rect(x + 40, y + 56, 90, 16, (60, 70, 85))
    cv.fill_rect(x + 110, y + 48, 16, 8, (60, 70, 85))
    cv.fill_rect(x + 90, y + 44, 14, 12, RED)
    cv.fill_rect(x + 70, y + 40, 2, 16, GREY)
    cv.poly_fill([(x + 72, y + 40), (x + 72, y + 48), (x + 84, y + 44)], RED)
    for mx, my in ((x + 155, y + 88), (x + 45, y + 92)):
        for dx, dy in ((0, -11), (0, 11), (-11, 0), (11, 0),
                       (-8, -8), (8, -8), (-8, 8), (8, 8)):
            cv.line(mx, my, mx + dx, my + dy, GREY)
        cv.disc(mx, my, 7, (20, 20, 20))
        cv.disc(mx, my, 3, (90, 90, 90))
    caption_banner(cv, x, y + 110, w, 90,
                   ["IRAN: SHIPS HIT", "MINES IN HORMUZ", "TEHRAN WARNS",
                    "COORDINATE"],
                   scale=2, bg=(20, 60, 60), fg=WHITE)


def draw_bottom_cairo(cv):
    # 31 killed in Cairo tanker fire: FUEL TANKER CRASH ON HIGHWAY.
    # Scene: tanker truck on a highway, flames above it.
    x, w = BOT_COLS[3]
    y, h = BOT_Y, BOT_H
    panel(cv, x, y, w, h, accent=(255, 120, 40))
    kicker(cv, x, y + 10, w, "DEADLY CRASH", 1, WHITE)
    kicker(cv, x, y + 24, w, "CAIRO, EGYPT", 1, GOLD)
    cv.fill_rect(x + 14, y + 92, w - 28, 12, (50, 55, 65))
    for dx in range(0, w - 28, 24):
        cv.fill_rect(x + 18 + dx, y + 97, 12, 2, WHITE)
    cv.poly_fill([(x + 56, y + 62), (x + 68, y + 40), (x + 80, y + 62)], GOLD)
    cv.poly_fill([(x + 86, y + 62), (x + 98, y + 36), (x + 110, y + 62)], RED)
    cv.poly_fill([(x + 114, y + 62), (x + 124, y + 44), (x + 134, y + 62)], GOLD)
    cv.disc(x + 76, y + 34, 5, (120, 120, 120))
    cv.disc(x + 104, y + 30, 6, (100, 100, 100))
    cv.fill_rect(x + 40, y + 62, 90, 22, (180, 190, 200))
    cv.rect(x + 40, y + 62, 90, 22, GREY, 1)
    cv.fill_rect(x + 132, y + 68, 26, 16, RED)
    for wx in (x + 52, x + 84, x + 116, x + 144):
        cv.disc(wx, y + 88, 5, (15, 15, 15))
        cv.disc(wx, y + 88, 2, GREY)
    caption_banner(cv, x, y + 110, w, 90,
                   ["31 KILLED", "IN CAIRO FIRE", "TANKER CRASH",
                    "ON HIGHWAY"],
                   scale=2, bg=(120, 40, 10), fg=WHITE)


def draw_bottom_gukesh(cv):
    # Gukesh vs Sindarov: WORLD CHESS CHAMPIONSHIP, GENEVA.
    # Scene: 8x8 chessboard with the two kings.
    x, w = BOT_COLS[4]
    y, h = BOT_Y, BOT_H
    panel(cv, x, y, w, h, accent=CYAN)
    kicker(cv, x, y + 10, w, "GLOBAL SPORT", 1, WHITE)
    kicker(cv, x, y + 24, w, "GENEVA, SWITZERLAND", 1, GOLD)
    bx, by = x + 69, y + 44
    for r in range(8):
        for c in range(8):
            col = (220, 200, 160) if (r + c) % 2 == 0 else (40, 50, 70)
            cv.fill_rect(bx + c * 7, by + r * 7, 7, 7, col)
    cv.rect(bx, by, 56, 56, GOLD, 1)
    cv.disc(bx + 10, by + 10, 5, WHITE)
    cv.disc(bx + 45, by + 45, 5, (15, 15, 15))
    cv.circle(bx + 45, by + 45, 6, GOLD)
    caption_banner(cv, x, y + 110, w, 90,
                   ["GUKESH", "VS SINDAROV", "WORLD CHESS",
                    "CHAMPIONSHIP", "GENEVA"],
                   scale=2, bg=(30, 30, 60), fg=WHITE)


def draw_bottom_slots(cv):
    # Bottom row of 5: VP health checks Jakarta; Flipkart CEO steps down;
    # Iran Hormuz mines; Cairo tanker fire, 31 killed; Gukesh vs Sindarov,
    # World Chess Championship, Geneva. Each caption names PLACE + EVENT.
    for fn in (draw_bottom_vp, draw_bottom_flipkart, draw_bottom_iran,
               draw_bottom_cairo, draw_bottom_gukesh):
        fn(cv)


def draw_extra_row(cv):
    """Slim extra row of 3 verified secondary stories (832..904).

    Text-led panels: place kicker + 2 caption lines at scale 2, the same
    size as every other caption, so they stay legible at ~300px. Stories
    are the strongest secondaries: US stocks fall (Nasdaq down ~4% on AI
    fears), Colombia police free 20 hostages held 17 hours, Israeli
    judges recommend dropping the most serious Netanyahu charges.
    """
    panels = [
        ((8, 328), RED, "WALL STREET, USA",
         ["US STOCKS FALL", "NASDAQ DOWN 4 PCT"]),
        ((344, 328), GREEN, "BOGOTA, COLOMBIA",
         ["POLICE FREE 20 HOSTAGES", "AFTER 17 HOUR STANDOFF"]),
        ((680, 328), CYAN, "JERUSALEM, ISRAEL",
         ["JUDGES: DROP NETANYAHU", "MOST SERIOUS CHARGES"]),
    ]
    for (x, w), accent, place, lines in panels:
        panel(cv, x, EXTRA_Y, w, EXTRA_H, accent=accent)
        kicker(cv, x, EXTRA_Y + 10, w, place, 1, GOLD)
        cv.lines_centered(x + w // 2, EXTRA_Y + 26, lines, 2, WHITE, gap=4)


def draw_ticker_slot(cv):
    # Bottom ticker (912..1016): 3 lines of secondary 26 Nov stories that
    # are NOT already panels above, plus the source strip. Scale 1 text:
    # each line is checked to fit the 952px usable width (max ~158 chars).
    cv.fill_rect(8, TICK_Y, 1008, TICK_H, PANEL_DK)
    cv.rect(8, TICK_Y, 1008, TICK_H, CYAN, 2)
    cv.text_centered(512, TICK_Y + 10, "ALSO TODAY - MORE FROM 26 NOVEMBER", 1, GOLD)
    cv.hline(28, TICK_Y + 24, 952, (40, 80, 120))
    cv.text(28, TICK_Y + 32,
            "AUSTRALIA AND SOLOMON ISLANDS SIGN LANDMARK SECURITY PACT - "
            "JAPAN-EUROPE MISSION REACHES MERCURY AFTER 8 YEARS",
            1, WHITE)
    cv.text(28, TICK_Y + 46,
            "XI GRAFT PROBE SHAKES SHANGHAI - INDIA MARKS CONSTITUTION DAY - "
            "NEPAL GETS RS 15,000 CRORE PACKAGE - BANGLADESH RAISES "
            "GARMENT WAGE 36 PCT",
            1, WHITE)
    cv.text(28, TICK_Y + 60,
            "IPL 2027 AUCTION: 1,220 PLAYERS - COLOMBIA MARKS 10 YEARS OF "
            "PEACE DEAL - VENEZUELA DEBT 237.5 BILLION USD - PETROBRAS "
            "122 BILLION USD PLAN",
            1, WHITE)
    cv.hline(28, TICK_Y + 76, 952, (40, 80, 120))
    cv.text_centered(512, TICK_Y + 84,
                     "SOURCES: ANTARA - AP - INDIAN EXPRESS - JAGRANJOSH - "
                     "EUR RADIO - THE ZEBRA - ALXNOW - SELFSTUDYS - "
                     "LIBRE NEWS - M.LAMEDITERRANEE",
                     1, GREY)


# ---------------------------------------------------------------- PNG out
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(w, h, px):
    raw = bytearray()
    stride = w * 3
    for yy in range(h):
        raw.append(0)
        raw += px[yy * stride:(yy + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def build():
    cv = Canvas(W, H, NAVY)
    cv.rect(0, 0, W, H, (2, 10, 20), 8)
    draw_masthead(cv)
    draw_top_left_swiss(cv)
    draw_top_hero_russia(cv)
    draw_top_right_tariffs(cv)
    draw_slot_ranchi(cv)
    draw_world_map(cv)
    draw_slot_turkey_trot(cv)
    draw_bottom_slots(cv)
    draw_extra_row(cv)
    draw_ticker_slot(cv)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "./output")
    os.makedirs(out_dir, exist_ok=True)
    png = encode_png(W, H, build().px)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s %d bytes sha256=%s" %
          (path, len(png), hashlib.sha256(png).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
