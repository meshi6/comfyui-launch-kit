"""Launch Kit nodes for ComfyUI: a game's storefront, built from one style guide."""

from __future__ import annotations

import base64
import io
import json
import os
import re

import numpy as np
import torch
from PIL import Image

from .launch_kit.compose import CAPSULES, compose, search_thumbnail, trim_alpha
from .launch_kit.prompts import AISLES, LEGIBILITY_PROMPT, STYLE_GUIDE_SYSTEM
from .launch_kit.router import RouterError, auth_headers, claude, extract_json

try:  # available inside ComfyUI
    import folder_paths
except ImportError:  # unit tests outside ComfyUI
    folder_paths = None

CATEGORY = "Launch Kit"
HIDDEN_AUTH = {"auth_token": "AUTH_TOKEN_COMFY_ORG", "api_key": "API_KEY_COMFY_ORG"}


# ---------- tensor <-> PIL ----------

def tensor_to_pil(images: torch.Tensor, mask: torch.Tensor | None = None) -> Image.Image:
    """First image of an IMAGE batch ([B,H,W,C], 0..1). A LoadImage MASK (1 = transparent) becomes alpha."""
    arr = (images[0].cpu().numpy().clip(0, 1) * 255).astype(np.uint8)
    img = Image.fromarray(arr[..., :3], "RGB")
    if mask is not None:
        m = mask[0] if mask.dim() == 3 else mask
        alpha = ((1.0 - m.cpu().numpy().clip(0, 1)) * 255).astype(np.uint8)
        a = Image.fromarray(alpha, "L")
        if a.size != img.size:
            a = a.resize(img.size, Image.BILINEAR)
        img = img.convert("RGBA")
        img.putalpha(a)
    return img


def knock_out_white(img: Image.Image, soft: int = 40) -> Image.Image:
    """No mask given: treat a flat white background as transparent (text-to-image logos come on white)."""
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    dist = (255 - rgb).max(axis=2)  # 0 = pure white
    alpha = np.clip(dist * (255 / max(soft, 1)), 0, 255).astype(np.uint8)
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray(alpha, "L"))
    return out


def pil_to_tensor(img: Image.Image) -> torch.Tensor:
    arr = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


def png_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def parse_palette(text: str) -> list[str]:
    return re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", text or "")


# ---------- nodes ----------

class LaunchKitStyleGuide:
    """Game name + pitch → one style guide, plus ready prompts for any image or video node."""

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("style_guide_json", "key_art_prompt", "logo_prompt", "emblem_prompt", "trailer_prompt", "palette", "store_copy")
    DESCRIPTION = "Writes a game's brand style guide with Claude (via Comfy Router) and turns it into matching prompts, so every asset looks like one game."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "game_name": ("STRING", {"default": "Frostbound"}),
                "pitch": ("STRING", {"multiline": True, "default": AISLES["Fantasy RPG"]["example_pitch"]}),
                "aisle": (list(AISLES.keys()), {"default": "Fantasy RPG"}),
            },
            "optional": {
                "extra_direction": ("STRING", {"multiline": True, "default": ""}),
            },
            "hidden": HIDDEN_AUTH,
        }

    def run(self, game_name, pitch, aisle, extra_direction="", auth_token=None, api_key=None):
        headers = auth_headers(api_key, auth_token)
        name = game_name.strip()
        direction = " ".join(x for x in [AISLES.get(aisle, {}).get("direction", ""), (extra_direction or "").strip()] if x)
        prompt = f'Game name: "{name}"\nPitch: {pitch.strip()}' + (f"\nArt direction (store aisle the developer picked): {direction}" if direction else "")

        brief, last = None, None
        for attempt in range(2):  # the guide is long; retry once on invalid JSON
            text = claude(
                prompt if attempt == 0 else prompt + "\n\nReturn strictly valid JSON. Inside string values never use double quotes; use single quotes instead.",
                headers,
                system=STYLE_GUIDE_SYSTEM,
            )
            try:
                brief = extract_json(text)
                break
            except (ValueError, RouterError) as e:
                last = e
        if brief is None:
            raise RouterError(f"Style guide came back as invalid JSON twice: {last}")
        brief["title"] = name

        pal = brief.get("palette") or []
        colors = ", ".join(f"{p.get('name', '')} {p.get('hex', '')}".strip() for p in pal)
        style = brief.get("artStyle", "")
        key_art = (
            f'Key art for the video game "{name}" ({brief.get("genre", "")}). {brief.get("keyArtPrompt", "")}. Style: {style}. '
            f'Mood: {brief.get("mood", "")}. Dominant palette: {", ".join(p.get("hex", "") for p in pal)}. Cinematic wide composition, premium store-page quality. '
            "Keep the upper-center calm (open sky or soft background, never a box, panel or frame) so a title logo can sit there. "
            "All characters are original designs. ABSOLUTELY NO text, letters, numbers, logos, watermarks or UI."
        )
        logo = (
            f'Video game title logo that reads exactly "{name}". {brief.get("logoPrompt", "")}. Lettering: {brief.get("fontVibe", "")}. '
            f"Colors: {colors}. {style}. Centered, isolated on a flat solid plain white background, crisp edges, no other text, no scene."
        )
        emblem = f'Game app icon emblem for "{name}": {brief.get("emblemPrompt", "")}. {style}. Bold, simple, centered, reads clearly at 64px, no text, no letters.'
        shots = [s.strip(" ;.") for s in re.split(r"\s*\d\)\s*", brief.get("trailerPrompt", "")) if s.strip()][:4]
        times = ["0–3s", "3–6s", "6–9s", "9–12s"]
        shot_list = " HARD CUT TO ".join(f"SHOT {i + 1} ({times[i]}): {s}." for i, s in enumerate(shots)) or brief.get("trailerPrompt", "")
        trailer = (
            f'A 12-second video game trailer for "{name}" ({brief.get("genre", "")}) made of separate shots joined by hard cuts. {shot_list} '
            "HARD CUT TO FINAL SHOT (last 2s): the title logo, centered, sharp and legible, on a dark background with a light flare. "
            f'Style: {style}. Mood: {brief.get("mood", "")}. Epic trailer music with a hit on every cut. '
            f'A deep trailer narrator voice says: "{brief.get("trailerLine") or brief.get("tagline", "")}". Original characters only.'
        )
        palette = " ".join(p.get("hex", "") for p in pal)
        store_copy = brief.get("storeBlurb", "") + "\n\n" + "\n".join(f"• {f}" for f in brief.get("features", []))
        return (json.dumps(brief, indent=2, ensure_ascii=False), key_art, logo, emblem, trailer, palette, store_copy)


class LaunchKitStoreCapsules:
    """Key art + logo → every Steam, itch.io and app-icon size, saved to the output folder."""

    CATEGORY = CATEGORY
    FUNCTION = "run"
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("main_capsule", "small_capsule", "saved_files")
    DESCRIPTION = "Composites the key art and title logo into all 10 store sizes (8 Steam, itch.io cover, app icon) and saves them. No API calls."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key_art": ("IMAGE",),
                "logo": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "launch-kit/my-game"}),
            },
            "optional": {
                "logo_mask": ("MASK", {"tooltip": "From LoadImage or a background-removal node. Without it, a white background is knocked out."}),
                "emblem": ("IMAGE", {"tooltip": "Square mark for the app icon."}),
                "emblem_mask": ("MASK",),
                "palette": ("STRING", {"default": "", "tooltip": "Hex colors, e.g. from Launch Kit Style Guide. [0] primary, [2] dark."}),
            },
        }

    def run(self, key_art, logo, filename_prefix, logo_mask=None, emblem=None, emblem_mask=None, palette=""):
        art = tensor_to_pil(key_art)
        lg = tensor_to_pil(logo, logo_mask) if logo_mask is not None else knock_out_white(tensor_to_pil(logo))
        lg = trim_alpha(lg)
        em = None
        if emblem is not None:
            em = tensor_to_pil(emblem, emblem_mask) if emblem_mask is not None else tensor_to_pil(emblem).convert("RGBA")
        pal = parse_palette(palette)

        root = folder_paths.get_output_directory() if folder_paths else os.path.abspath("output")
        sub = filename_prefix.strip().strip("/") or "launch-kit"
        out_dir = os.path.join(root, sub)
        os.makedirs(out_dir, exist_ok=True)

        saved, previews, made = [], [], {}
        for c in CAPSULES:
            img = compose(c, art, lg, em, pal)
            if img is None:
                continue
            made[c.id] = img
            ext = "png" if img.mode == "RGBA" or c.icon_only else "jpg"
            fname = f"{c.id}-{c.w}x{c.h}.{ext}"
            path = os.path.join(out_dir, fname)
            if ext == "jpg":
                img.save(path, quality=92)
            else:
                img.save(path)
            saved.append(os.path.relpath(path, root))
            previews.append({"filename": fname, "subfolder": sub, "type": "output"})

        main = made.get("steam-main") or art
        small = made.get("steam-small") or art
        return {"ui": {"images": previews}, "result": (pil_to_tensor(main), pil_to_tensor(small), "\n".join(saved))}


class LaunchKitLegibilityCheck:
    """Shrinks a capsule to Steam's 120×45 search size and asks Claude if the title still reads."""

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("INT", "BOOLEAN", "STRING", "IMAGE")
    RETURN_NAMES = ("score", "readable", "tip", "search_size_preview")
    DESCRIPTION = "Scores 1–10 whether the game title survives Steam's smallest thumbnail, with one concrete fix."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "capsule": ("IMAGE", {"tooltip": "Ideally the small capsule from Launch Kit Store Capsules."}),
                "title": ("STRING", {"default": "Frostbound"}),
            },
            "hidden": HIDDEN_AUTH,
        }

    def run(self, capsule, title, auth_token=None, api_key=None):
        headers = auth_headers(api_key, auth_token)
        _, big = search_thumbnail(tensor_to_pil(capsule))
        text = claude(LEGIBILITY_PROMPT.format(title=title.strip()), headers, image_png_b64=png_b64(big), max_tokens=300)
        r = extract_json(text)
        score = int(max(1, min(10, round(float(r.get("score", 0) or 0)))))
        return (score, bool(r.get("readable", score >= 6)), str(r.get("tip", "")), pil_to_tensor(big))


NODE_CLASS_MAPPINGS = {
    "LaunchKitStyleGuide": LaunchKitStyleGuide,
    "LaunchKitStoreCapsules": LaunchKitStoreCapsules,
    "LaunchKitLegibilityCheck": LaunchKitLegibilityCheck,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LaunchKitStyleGuide": "Launch Kit · Style Guide",
    "LaunchKitStoreCapsules": "Launch Kit · Store Capsules",
    "LaunchKitLegibilityCheck": "Launch Kit · Legibility Check",
}
