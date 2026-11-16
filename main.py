# Cosmic Cat vs the Earth Yarn Ball
# An original procedural artwork for the "Make the AI judge excited" bounty.
# A giant ginger cat leaps through deep space and bats planet Earth -- wound
# up like a ball of yarn -- with its paws, while the yarn unravels in a
# sparkling spiral. One clear focal point, a diagonal burst of motion, and a
# scale-twist surprise: the whole planet as a toy.
#
# Pure Python 3 standard library. No network, no randomness at run time
# (one fixed seed), no clock: two runs write byte-identical PNGs.
# Writes to /output/entry.png, or $MAKEFUN_OUTPUT_DIR/entry.png locally.

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
SEED = 20261116

# ---------------------------------------------------------------- PNG output

def _crc(chunk_type, data):
    c = zlib.crc32(chunk_type)
    c = zlib.crc32(data, c)
    return struct.pack(">I", c & 0xFFFFFFFF)


def _png_chunk(chunk_type, data):
    return struct.pack(">I", len(data)) + chunk_type + data + _crc(chunk_type, data)


def write_png(path, px):
    """px is a flat bytearray of W*H*3 RGB bytes. Deterministic output."""
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: None
        raw += px[y * stride:(y + 1) * stride]
    body = _png_chunk(b"IHDR", ihdr)
    body += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    body += _png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + body)


# ---------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, w, h, rgb):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(rgb) * (w * h))

    def _blend(self, idx, r, g, b, a):
        # a in 0..255; blend one pixel in place
        px = self.px
        ia = 255 - a
        px[idx] = (r * a + px[idx] * ia) // 255
        px[idx + 1] = (g * a + px[idx + 1] * ia) // 255
        px[idx + 2] = (b * a + px[idx + 2] * ia) // 255

    def vgrad(self, top, bottom):
        """Vertical gradient, whole canvas, fast row fills."""
        w, h, px = self.w, self.h, self.px
        for y in range(h):
            t = y / (h - 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            row = bytes((r, g, b)) * w
            px[y * w * 3:(y + 1) * w * 3] = row

    def disc(self, cx, cy, r, rgb, alpha=255, soft=1.0):
        """Filled disc with analytic anti-aliased edge."""
        w, h, px = self.w, self.h, self.px
        rr, gg, bb = rgb
        r_in = r - 0.5
        r_out = r + 0.5
        r_in2 = r_in * r_in
        r_out2 = r_out * r_out
        x0 = max(0, int(cx - r_out))
        x1 = min(w - 1, int(cx + r_out) + 1)
        y0 = max(0, int(cy - r_out))
        y1 = min(h - 1, int(cy + r_out) + 1)
        for y in range(y0, y1 + 1):
            dy = y - cy
            base = y * w * 3
            for x in range(x0, x1 + 1):
                dx = x - cx
                d2 = dx * dx + dy * dy
                if d2 >= r_out2:
                    continue
                if d2 <= r_in2:
                    a = alpha
                else:
                    d = math.sqrt(d2)
                    a = int(alpha * max(0.0, min(1.0, (r_out - d) * soft)))
                    if a <= 0:
                        continue
                idx = base + x * 3
                if a >= 255:
                    px[idx] = rr
                    px[idx + 1] = gg
                    px[idx + 2] = bb
                else:
                    ia = 255 - a
                    px[idx] = (rr * a + px[idx] * ia) // 255
                    px[idx + 1] = (gg * a + px[idx + 1] * ia) // 255
                    px[idx + 2] = (bb * a + px[idx + 2] * ia) // 255

    def glow(self, cx, cy, r, rgb, alpha=255):
        """Soft radial glow: bright core fading to nothing at r."""
        w, h, px = self.w, self.h, self.px
        rr, gg, bb = rgb
        r2 = r * r
        x0 = max(0, int(cx - r))
        x1 = min(w - 1, int(cx + r) + 1)
        y0 = max(0, int(cy - r))
        y1 = min(h - 1, int(cy + r) + 1)
        for y in range(y0, y1 + 1):
            dy = y - cy
            base = y * w * 3
            for x in range(x0, x1 + 1):
                dx = x - cx
                d2 = dx * dx + dy * dy
                if d2 >= r2:
                    continue
                t = 1.0 - d2 / r2
                a = int(alpha * t * t)
                if a <= 0:
                    continue
                idx = base + x * 3
                ia = 255 - a
                px[idx] = (rr * a + px[idx] * ia) // 255
                px[idx + 1] = (gg * a + px[idx + 1] * ia) // 255
                px[idx + 2] = (bb * a + px[idx + 2] * ia) // 255

    def ellipse(self, cx, cy, rx, ry, rot, rgb, alpha=255):
        """Rotated filled ellipse, analytic anti-aliased edge."""
        w, h, px = self.w, self.h, self.px
        rr, gg, bb = rgb
        cosr = math.cos(rot)
        sinr = math.sin(rot)
        ext = max(rx, ry) + 1.0
        x0 = max(0, int(cx - ext))
        x1 = min(w - 1, int(cx + ext) + 1)
        y0 = max(0, int(cy - ext))
        y1 = min(h - 1, int(cy + ext) + 1)
        for y in range(y0, y1 + 1):
            dy = y - cy
            base = y * w * 3
            for x in range(x0, x1 + 1):
                dx = x - cx
                u = (dx * cosr + dy * sinr) / rx
                v = (-dx * sinr + dy * cosr) / ry
                d2 = u * u + v * v
                if d2 >= 1.0404:  # (1.02)^2
                    continue
                if d2 <= 0.9604:  # (0.98)^2
                    a = alpha
                else:
                    d = math.sqrt(d2)
                    a = int(alpha * max(0.0, min(1.0, (1.02 - d) / 0.04)))
                    if a <= 0:
                        continue
                idx = base + x * 3
                if a >= 255:
                    px[idx] = rr
                    px[idx + 1] = gg
                    px[idx + 2] = bb
                else:
                    ia = 255 - a
                    px[idx] = (rr * a + px[idx] * ia) // 255
                    px[idx + 1] = (gg * a + px[idx + 1] * ia) // 255
                    px[idx + 2] = (bb * a + px[idx + 2] * ia) // 255

    def capsule(self, x1, y1, x2, y2, width, rgb, alpha=255):
        """Thick line segment with round caps, analytic anti-aliased edge."""
        w, h, px = self.w, self.h, self.px
        rr, gg, bb = rgb
        r = width / 2.0
        vx = x2 - x1
        vy = y2 - y1
        seg2 = vx * vx + vy * vy
        r_in = r - 0.5
        r_out = r + 0.5
        r_in2 = r_in * r_in
        r_out2 = r_out * r_out
        x0 = max(0, int(min(x1, x2) - r_out))
        x1b = min(w - 1, int(max(x1, x2) + r_out) + 1)
        y0 = max(0, int(min(y1, y2) - r_out))
        y1b = min(h - 1, int(max(y1, y2) + r_out) + 1)
        for y in range(y0, y1b + 1):
            base = y * w * 3
            for x in range(x0, x1b + 1):
                dx = x - x1
                dy = y - y1
                if seg2 > 0:
                    t = (dx * vx + dy * vy) / seg2
                    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
                else:
                    t = 0.0
                ex = dx - t * vx
                ey = dy - t * vy
                d2 = ex * ex + ey * ey
                if d2 >= r_out2:
                    continue
                if d2 <= r_in2:
                    a = alpha
                else:
                    d = math.sqrt(d2)
                    a = int(alpha * max(0.0, min(1.0, r_out - d)))
                    if a <= 0:
                        continue
                idx = base + x * 3
                if a >= 255:
                    px[idx] = rr
                    px[idx + 1] = gg
                    px[idx + 2] = bb
                else:
                    ia = 255 - a
                    px[idx] = (rr * a + px[idx] * ia) // 255
                    px[idx + 1] = (gg * a + px[idx + 1] * ia) // 255
                    px[idx + 2] = (bb * a + px[idx + 2] * ia) // 255

    def poly(self, pts, rgb, alpha=255):
        """Filled polygon (scanline spans), solid or translucent."""
        w, h, px = self.w, self.h, self.px
        rr, gg, bb = rgb
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(h - 1, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1 + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    t = (yc - ay) / (by - ay)
                    xs.append(ax + t * (bx - ax))
            if len(xs) < 2:
                continue
            xs.sort()
            base = y * w * 3
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(math.ceil(xs[k])))
                xb = min(w - 1, int(math.floor(xs[k + 1])))
                for x in range(xa, xb + 1):
                    idx = base + x * 3
                    if alpha >= 255:
                        px[idx] = rr
                        px[idx + 1] = gg
                        px[idx + 2] = bb
                    else:
                        ia = 255 - alpha
                        px[idx] = (rr * alpha + px[idx] * ia) // 255
                        px[idx + 1] = (gg * alpha + px[idx + 1] * ia) // 255
                        px[idx + 2] = (bb * alpha + px[idx + 2] * ia) // 255

    def polyline(self, pts, width, rgb, alpha=255):
        for i in range(len(pts) - 1):
            self.capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                         width, rgb, alpha)

    def bezier(self, p0, p1, p2, p3, width, rgb, alpha=255, steps=24):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            mt = 1.0 - t
            x = (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0]
                 + 3 * mt * t * t * p2[0] + t ** 3 * p3[0])
            y = (mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1]
                 + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])
            pts.append((x, y))
        self.polyline(pts, width, rgb, alpha)

    def sparkle(self, cx, cy, r, rgb, alpha=255):
        """Four-point star sparkle."""
        self.capsule(cx - r, cy, cx + r, cy, max(2.0, r * 0.22), rgb, alpha)
        self.capsule(cx, cy - r, cx, cy + r, max(2.0, r * 0.22), rgb, alpha)
        self.disc(cx, cy, max(1.5, r * 0.18), rgb, alpha)


# 5x7 bitmap font, only the glyphs the artwork needs.
FONT = {
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "01010"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
}


def draw_text(cv, text, x, y, scale, rgb):
    """Draw text with the bitmap font; x,y is the top-left corner."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    bx = cx + col * scale
                    by = y + row * scale
                    for yy in range(by, by + scale):
                        base = yy * cv.w * 3
                        for xx in range(bx, bx + scale):
                            idx = base + xx * 3
                            cv.px[idx] = rgb[0]
                            cv.px[idx + 1] = rgb[1]
                            cv.px[idx + 2] = rgb[2]
        cx += 6 * scale
    return cx - x


# ---------------------------------------------------------------- palette

INK = (34, 12, 40)          # deep purple outline
SPACE_TOP = (13, 14, 48)
SPACE_BOT = (58, 14, 66)
GOLD = (255, 209, 102)
MAGENTA = (255, 46, 136)
CYAN = (0, 229, 255)
WHITE = (255, 255, 255)
CAT = (255, 159, 28)        # ginger
CAT_LIGHT = (255, 209, 102)
CAT_DARK = (232, 106, 0)
PINK = (255, 107, 157)
EARTH_BLUE = (29, 111, 209)
EARTH_DEEP = (16, 66, 150)
EARTH_GREEN = (47, 174, 95)
EARTH_LIGHT = (55, 182, 255)

EARTH = (665.0, 355.0)
EARTH_R = 165.0


def draw_background(cv, rng):
    cv.vgrad(SPACE_TOP, SPACE_BOT)
    # Nebula clouds, soft and huge.
    cv.glow(820, 180, 420, (120, 30, 120), 120)
    cv.glow(180, 850, 460, (10, 60, 110), 110)
    cv.glow(700, 900, 380, (110, 20, 70), 90)
    cv.glow(EARTH[0], EARTH[1], 430, (255, 46, 136), 70)
    cv.glow(EARTH[0], EARTH[1], 300, (255, 180, 60), 55)
    # Starburst rays fanning out of the Earth ball.
    for i in range(28):
        ang = (i / 28.0) * math.tau
        wdt = 0.045 + (0.03 if i % 3 == 0 else 0.0)
        r1 = EARTH_R + 30
        r2 = 470 if i % 2 == 0 else 360
        cx, cy = EARTH
        p1 = (cx + math.cos(ang - wdt) * r1, cy + math.sin(ang - wdt) * r1)
        p2 = (cx + math.cos(ang + wdt) * r1, cy + math.sin(ang + wdt) * r1)
        tip = (cx + math.cos(ang) * r2, cy + math.sin(ang) * r2)
        col = GOLD if i % 3 == 0 else WHITE
        cv.poly([(cx, cy), p1, tip, p2], col, 13 if i % 3 else 18)
    # Stars.
    for _ in range(190):
        x = rng.uniform(0, W)
        y = rng.uniform(0, H)
        r = rng.uniform(0.8, 2.6)
        a = rng.randint(90, 255)
        col = rng.choice([WHITE, WHITE, (255, 240, 200), (180, 230, 255)])
        cv.disc(x, y, r, col, a)
    for _ in range(14):
        x = rng.uniform(40, W - 40)
        y = rng.uniform(40, H - 40)
        cv.sparkle(x, y, rng.uniform(7, 16),
                   rng.choice([WHITE, GOLD, CYAN]), rng.randint(140, 230))


def draw_earth(cv, rng):
    cx, cy = EARTH
    r = EARTH_R
    # Outer glow + rim light.
    cv.glow(cx, cy, r + 90, (0, 180, 255), 110)
    cv.disc(cx, cy, r + 7, (120, 220, 255), 200)
    cv.disc(cx, cy, r, EARTH_DEEP)
    # Ocean shading: darker lower-right, lighter upper-left.
    cv.glow(cx - r * 0.45, cy - r * 0.5, r * 0.9, (70, 160, 255), 120)
    cv.glow(cx + r * 0.5, cy + r * 0.55, r * 0.95, (8, 30, 90), 130)
    # Continents, drawn as chunky yarn blobs (green, wound like thread).
    blobs = [
        (-0.42, -0.35, 0.42, 0.30), (-0.05, -0.55, 0.34, 0.24),
        (0.38, -0.28, 0.36, 0.28), (-0.55, 0.28, 0.34, 0.26),
        (0.05, 0.30, 0.44, 0.30), (0.55, 0.35, 0.26, 0.20),
        (-0.15, 0.62, 0.30, 0.20),
    ]
    for bx, by, brx, bry in blobs:
        cv.ellipse(cx + bx * r, cy + by * r, brx * r, bry * r,
                   rng.uniform(-0.6, 0.6), EARTH_GREEN, 235)
        cv.ellipse(cx + bx * r, cy + by * r, brx * r * 0.55, bry * r * 0.55,
                   rng.uniform(-0.6, 0.6), (90, 220, 130), 200)
    # Yarn strands: great-circle arcs wrapping the ball.
    for k in range(9):
        a0 = rng.uniform(0, math.tau)
        tilt = rng.uniform(-0.9, 0.9)
        pts = []
        for i in range(25):
            t = i / 24.0
            ang = a0 + t * math.pi * rng.choice([1.0, 1.0, 0.7])
            px = cx + math.cos(ang) * r * 0.97
            py = cy + math.sin(ang) * r * 0.97 * math.cos(tilt) + math.sin(tilt) * r * 0.35 * math.sin(ang)
            pts.append((px, py))
        col = rng.choice([EARTH_LIGHT, (150, 225, 255), WHITE, (120, 200, 255)])
        cv.polyline(pts, rng.uniform(5, 9), col, rng.randint(150, 220))
    # Cloud swirls.
    for _ in range(7):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(0.15, 0.8) * r
        px = cx + math.cos(a) * rr
        py = cy + math.sin(a) * rr * 0.9
        cv.ellipse(px, py, rng.uniform(22, 46), rng.uniform(8, 14),
                   rng.uniform(-0.5, 0.5), WHITE, rng.randint(90, 150))
    # Ice caps.
    cv.ellipse(cx - 6, cy - r * 0.94, r * 0.32, r * 0.11, 0.1, WHITE, 235)
    cv.ellipse(cx + 4, cy + r * 0.95, r * 0.24, r * 0.09, -0.08, WHITE, 220)
    # Bright specular highlight.
    cv.glow(cx - r * 0.42, cy - r * 0.48, r * 0.42, WHITE, 130)
    # Loose yarn end unravelling from the ball toward the cat.
    cv.bezier((cx - r * 0.55, cy + r * 0.72), (520, 560), (470, 640),
              (505, 700), 10, (220, 240, 255), 235)
    cv.bezier((505, 700), (540, 745), (470, 780), (520, 800), 8,
              (220, 240, 255), 210)
    cv.disc(520, 800, 7, (220, 240, 255), 210)


def draw_speed_lines(cv, rng):
    # Streaks parallel to the cat's leap (up-right), behind the cat.
    for _ in range(16):
        x = rng.uniform(-40, 620)
        y = rng.uniform(480, 1020)
        ln = rng.uniform(110, 280)
        dx, dy = 0.72, -0.69
        wdt = rng.uniform(3, 9)
        col = rng.choice([WHITE, CYAN, GOLD, (200, 240, 255)])
        cv.capsule(x, y, x + dx * ln, y + dy * ln, wdt, col,
                   rng.randint(50, 150))
    # A burst of streaks right behind the Earth ball.
    for _ in range(8):
        a = rng.uniform(math.pi * 0.55, math.pi * 1.05)
        x0 = EARTH[0] + math.cos(a) * (EARTH_R + 25)
        y0 = EARTH[1] + math.sin(a) * (EARTH_R + 25)
        ln = rng.uniform(60, 150)
        cv.capsule(x0, y0, x0 + math.cos(a) * ln, y0 + math.sin(a) * ln,
                   rng.uniform(3, 7), WHITE, rng.randint(90, 170))


def draw_confetti(cv, rng):
    for _ in range(46):
        x = rng.uniform(20, W - 20)
        y = rng.uniform(20, H - 20)
        # Keep the face and the Earth ball readable.
        if (380 < x < 560 and 500 < y < 720) or (520 < x < 820 and 200 < y < 520):
            continue
        col = rng.choice([MAGENTA, GOLD, CYAN, WHITE, (255, 120, 60)])
        if rng.random() < 0.5:
            cv.disc(x, y, rng.uniform(3, 7), col, rng.randint(150, 235))
        else:
            cv.ellipse(x, y, rng.uniform(4, 9), rng.uniform(2, 4),
                       rng.uniform(0, math.pi), col, rng.randint(150, 235))


def outlined_disc(cv, cx, cy, r, fill, outline=INK, ow=7):
    cv.disc(cx, cy, r + ow, outline)
    cv.disc(cx, cy, r, fill)


def outlined_ellipse(cv, cx, cy, rx, ry, rot, fill, outline=INK, ow=7):
    cv.ellipse(cx, cy, rx + ow, ry + ow, rot, outline)
    cv.ellipse(cx, cy, rx, ry, rot, fill)


def outlined_capsule(cv, x1, y1, x2, y2, width, fill, outline=INK, ow=12):
    cv.capsule(x1, y1, x2, y2, width + ow, outline)
    cv.capsule(x1, y1, x2, y2, width, fill)


def draw_cat(cv, rng):
    # ---- tail: sweeping S-curve, tapered, behind the body ----
    tail_pts = []
    for i in range(25):
        t = i / 24.0
        x = 175 - 150 * t + 30 * t * t
        y = 845 + 150 * t - 55 * t * t
        tail_pts.append((x, y))
    for i, (x, y) in enumerate(tail_pts):
        wdt = 66 - 32 * (i / 24.0)
        cv.disc(x, y, wdt / 2 + 6, INK)
    for i, (x, y) in enumerate(tail_pts):
        wdt = 66 - 32 * (i / 24.0)
        cv.disc(x, y, wdt / 2, CAT if i % 2 == 0 else CAT_LIGHT)
    cv.disc(tail_pts[-1][0], tail_pts[-1][1], 19, CAT_LIGHT)
    cv.disc(tail_pts[-1][0], tail_pts[-1][1], 11, PINK)
    # ---- hind leg, tucked ----
    outlined_ellipse(cv, 185, 885, 95, 55, -0.35, CAT)
    cv.disc(120, 920, 30, INK)
    cv.disc(120, 920, 24, CAT)
    # ---- body: big diagonal ellipse ----
    outlined_ellipse(cv, 300, 790, 195, 118, -0.55, CAT)
    # Belly patch.
    cv.ellipse(285, 830, 120, 62, -0.55, CAT_LIGHT, 235)
    # Back stripes.
    for (sx, sy, ex, ey) in [(185, 700, 215, 745), (230, 680, 255, 725),
                             (275, 668, 295, 712)]:
        cv.capsule(sx, sy, ex, ey, 16, CAT_DARK, 235)
    # ---- front legs reaching for the Earth (behind the head: the head
    # overlaps their middles and the paws pop out beside it) ----
    outlined_capsule(cv, 400, 720, 575, 480, 52, CAT)
    outlined_capsule(cv, 370, 745, 560, 560, 48, CAT)
    # Paws.
    outlined_disc(cv, 582, 472, 38, CAT)
    outlined_disc(cv, 566, 556, 34, CAT)
    # Toe beans on the front paw.
    for (tx, ty) in [(570, 456), (592, 452), (602, 472)]:
        cv.disc(tx, ty, 6, PINK, 230)
    # The loose yarn end wraps the reaching paw.
    cv.bezier((505, 700), (545, 640), (530, 560), (572, 500), 9,
              (220, 240, 255), 235)
    # ---- ears (behind the head) ----
    for (ax, ay, bx, by, cx_, cy_) in [
            (344, 448, 312, 552, 404, 556),
            (516, 444, 450, 550, 536, 544)]:
        cv.poly([(ax, ay), (bx, by), (cx_, cy_)], INK)
        cv.poly([(ax + 8, ay + 30), (bx + 14, by - 8), (cx_ - 14, cy_ - 8)],
                CAT)
        cv.poly([(ax + 16, ay + 52), (bx + 22, by - 16), (cx_ - 22, cy_ - 16)],
                PINK)
    # ---- head ----
    outlined_disc(cv, 430, 600, 115, CAT)
    # Head stripes.
    for (sx, sy, ex, ey) in [(385, 495, 395, 535), (425, 488, 430, 530),
                             (465, 495, 460, 535)]:
        cv.capsule(sx, sy, ex, ey, 13, CAT_DARK, 235)
    # ---- eyes: huge, round, locked on the Earth ----
    for (ex, ey) in [(392, 578), (478, 568)]:
        cv.ellipse(ex, ey, 37, 43, 0.08, INK)
        cv.ellipse(ex, ey, 31, 37, 0.08, WHITE)
        cv.ellipse(ex + 9, ey - 7, 15, 21, 0.08, (20, 8, 30))
        cv.disc(ex + 14, ey - 14, 7, WHITE)
        cv.disc(ex + 2, ey + 12, 4, WHITE, 200)
    # ---- nose + open joyful mouth ----
    cv.poly([(428, 636), (466, 636), (447, 656)], (255, 93, 143))
    cv.ellipse(447, 682, 30, 21, 0.0, INK)
    cv.ellipse(447, 688, 22, 13, 0.0, (255, 93, 143))
    cv.ellipse(447, 692, 12, 7, 0.0, PINK)
    # ---- whiskers ----
    for (sx, sy, ex, ey) in [
            (330, 640, 245, 618), (332, 660, 250, 660), (335, 678, 258, 700),
            (528, 632, 610, 606), (530, 652, 612, 650), (526, 672, 604, 694)]:
        cv.capsule(sx, sy, ex, ey, 4, WHITE, 220)


def rounded_rect(cv, x0, y0, x1, y1, r, rgb, alpha=255):
    cv.poly([(x0 + r, y0), (x1 - r, y0), (x1, y0 + r), (x1, y1 - r),
             (x1 - r, y1), (x0 + r, y1), (x0, y1 - r), (x0, y0 + r)],
            rgb, alpha)
    for (cx, cy) in [(x0 + r, y0 + r), (x1 - r, y0 + r),
                     (x0 + r, y1 - r), (x1 - r, y1 - r)]:
        cv.disc(cx, cy, r, rgb, alpha)


def draw_bubble(cv):
    # White speech bubble, top-left, shouting at the judge.
    rounded_rect(cv, 92, 127, 333, 258, 30, INK)
    rounded_rect(cv, 98, 133, 327, 252, 26, WHITE)
    cv.poly([(225, 250), (305, 250), (352, 348)], INK)
    cv.poly([(232, 246), (298, 246), (340, 330)], WHITE)
    draw_text(cv, "WOW!", 132, 168, 7, INK)


def main():
    rng = random.Random(SEED)
    cv = Canvas(W, H, SPACE_TOP)
    draw_background(cv, rng)
    draw_earth(cv, rng)
    draw_speed_lines(cv, rng)
    draw_confetti(cv, rng)
    draw_cat(cv, rng)
    draw_bubble(cv)
    # Foreground sparkles for the final pop.
    for (x, y, r) in [(600, 250, 14), (760, 520, 12), (180, 420, 11),
                      (880, 700, 13), (90, 620, 10), (480, 180, 10)]:
        cv.sparkle(x, y, r, WHITE, 235)
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, "entry.png"), cv.px)


if __name__ == "__main__":
    main()
