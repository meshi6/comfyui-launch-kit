"""Store capsule compositing (a PIL port of the Launch Kit web app's canvas code)."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter


@dataclass(frozen=True)
class Capsule:
    id: str
    label: str
    platform: str
    w: int
    h: int
    logo: bool
    transparent: bool = False
    icon_only: bool = False


# Steamworks graphical asset sizes (current store layout). Verify on
# partner.steamgames.com before shipping a real store page.
CAPSULES: list[Capsule] = [
    Capsule("steam-header", "Header capsule", "Steam", 920, 430, True),
    Capsule("steam-small", "Small capsule", "Steam", 462, 174, True),
    Capsule("steam-main", "Main capsule", "Steam", 1232, 706, True),
    Capsule("steam-vertical", "Vertical capsule", "Steam", 748, 896, True),
    Capsule("steam-library", "Library capsule", "Steam", 600, 900, True),
    Capsule("steam-hero", "Library hero", "Steam", 3840, 1240, False),
    Capsule("steam-logo", "Library logo", "Steam", 1280, 720, True, transparent=True),
    Capsule("steam-bg", "Page background", "Steam", 1438, 810, False),
    Capsule("itch-cover", "Cover image", "itch.io", 630, 500, True),
    Capsule("app-icon", "App icon", "Mobile", 1024, 1024, False, icon_only=True),
]


def hex_to_rgb(h: str, fallback=(40, 40, 48)) -> tuple[int, int, int]:
    h = (h or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except (ValueError, IndexError):
        return fallback


def trim_alpha(img: Image.Image, pad: int = 8) -> Image.Image:
    """Crop away the transparent border around a cut-out logo."""
    img = img.convert("RGBA")
    bbox = img.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    return img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)))


def _cover(img: Image.Image, w: int, h: int, focus_y: float = 0.45) -> Image.Image:
    s = max(w / img.width, h / img.height)
    dw, dh = round(img.width * s), round(img.height * s)
    r = img.convert("RGB").resize((dw, dh), Image.LANCZOS)
    left = (dw - w) // 2
    top = round((dh - h) * focus_y)
    return r.crop((left, top, left + w, top + h))


def _contain(img: Image.Image, bw: int, bh: int) -> Image.Image:
    s = min(bw / img.width, bh / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def _logo_box(w: int, h: int) -> tuple[float, float, float, float]:
    """Where the logo sits for a given aspect ratio, as fractions of the canvas."""
    a = w / h
    if a > 2.3:
        return (0.1, 0.1, 0.8, 0.8)  # small capsule: logo is everything
    if a >= 1.2:
        return (0.18, 0.12, 0.64, 0.5)  # wide
    if a > 0.9:
        return (0.1, 0.08, 0.8, 0.42)  # ~square
    return (0.07, 0.62, 0.86, 0.3)  # portrait: lower third


def _radial(w: int, h: int, cx: float, cy: float, r: float, inner: tuple, outer: tuple) -> Image.Image:
    """RGBA radial gradient (cheap: draw at low res, then upscale)."""
    sw, sh = max(8, w // 8), max(8, h // 8)
    g = Image.new("RGBA", (sw, sh))
    px = g.load()
    for y in range(sh):
        for x in range(sw):
            d = min(1.0, (((x + 0.5) * 8 - cx) ** 2 + ((y + 0.5) * 8 - cy) ** 2) ** 0.5 / max(r, 1))
            px[x, y] = tuple(round(inner[i] + (outer[i] - inner[i]) * d) for i in range(4))
    return g.resize((w, h), Image.BILINEAR)


def compose(c: Capsule, key_art: Image.Image | None, logo: Image.Image | None, emblem: Image.Image | None, palette: list[str]) -> Image.Image | None:
    w, h = c.w, c.h
    primary = hex_to_rgb(palette[0] if palette else "", (60, 60, 70))
    dark = hex_to_rgb(palette[2] if len(palette) > 2 else "", (17, 17, 20))

    if c.transparent:
        if logo is None:
            return None
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        lg = _contain(logo, round(w * 0.9), round(h * 0.9))
        out.alpha_composite(lg, ((w - lg.width) // 2, (h - lg.height) // 2))
        return out

    if c.icon_only:
        if emblem is None:
            return None
        out = _radial(w, h, w / 2, h * 0.4, w * 0.75, (*primary, 255), (*dark, 255))
        em = _contain(emblem.convert("RGBA"), round(w * 0.72), round(h * 0.72))
        out.alpha_composite(em, ((w - em.width) // 2, (h - em.height) // 2))
        return out

    if key_art is None:
        return None
    out = _cover(key_art, w, h).convert("RGBA")

    if c.logo and logo is not None:
        bx, by, bw, bh = _logo_box(w, h)
        cx, cy = (bx + bw / 2) * w, (by + bh / 2) * h
        # soft scrim behind the logo so it stays legible on busy art
        out.alpha_composite(_radial(w, h, cx, cy, max(bw * w, bh * h) * 0.75, (0, 0, 0, 115), (0, 0, 0, 0)))
        lg = _contain(logo, round(bw * w), round(bh * h))
        lx, ly = round(bx * w + (bw * w - lg.width) / 2), round(by * h + (bh * h - lg.height) / 2)
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sil = Image.new("RGBA", lg.size, (0, 0, 0, 150))
        sil.putalpha(lg.getchannel("A").point(lambda a: a * 150 // 255))
        shadow.paste(sil, (lx, ly), sil)
        out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(max(3, w // 160))))
        out.alpha_composite(lg, (lx, ly))
    return out.convert("RGB")


def search_thumbnail(img: Image.Image, w: int = 120, h: int = 45, scale: int = 4) -> tuple[Image.Image, Image.Image]:
    """The size Steam actually shows in search, plus a pixel-exact upscale for a vision model to judge."""
    small = img.convert("RGB").resize((w, h), Image.LANCZOS)
    return small, small.resize((w * scale, h * scale), Image.NEAREST)
