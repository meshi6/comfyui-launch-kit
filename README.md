# 👾 Launch Kit for ComfyUI

**Your game's storefront, inside ComfyUI.** Three nodes from the [Launch Kit](https://github.com/meshi6/game-launch-kit-powered-by-comfy) app: one style guide that keeps every asset on-brand, every Steam store size in one step, and a check that your title still reads at Steam's smallest thumbnail.

| Node | What it does | API call |
| --- | --- | --- |
| **Launch Kit · Style Guide** | Game name + pitch + a genre "aisle" → a full brand style guide (palette, art direction, store copy) and ready prompts for **key art, title logo, emblem and a 12-second trailer**. Plug them into any image or video node. | Claude Sonnet 5.5 via [Comfy Router](https://docs.comfy.org/development/comfy-router/quickstart) |
| **Launch Kit · Store Capsules** | Key art + title logo (+ emblem) → all **10 store sizes** (8 Steam, itch.io cover, app icon), logo placed and shadowed for each shape, saved to `output/`. | none |
| **Launch Kit · Legibility Check** | A capsule → shrinks it to Steam's 120×45 search size and returns a **1–10 score**, pass/fail and one concrete fix. | Claude Sonnet 5.5 (vision) |

## How they fit together

```
Style Guide ──key_art_prompt──▶ (any image node) ──▶ key_art ─┐
            ──logo_prompt─────▶ (any image node) ──▶ logo ────┼──▶ Store Capsules ──small_capsule──▶ Legibility Check
            ──palette────────────────────────────────────────┘
            ──trailer_prompt──▶ (any video node, with the key art as reference)
```

The style guide is the point: generate it once, feed it to every model, and the logo, art, icons and trailer read as one game instead of separate AI outputs.

## Install

- **ComfyUI-Manager:** search for "Launch Kit".
- **Manually:** clone into `ComfyUI/custom_nodes/` and restart ComfyUI:
  ```bash
  cd ComfyUI/custom_nodes
  git clone https://github.com/meshi6/comfyui-launch-kit
  ```

No extra Python packages: it uses what ComfyUI already ships (torch, numpy, Pillow) and the standard library.

## API key

Style Guide and Legibility Check call Comfy Router and bill your Comfy credits (about one Claude call each). They use, in order:

1. the API key of the Comfy account you're signed in with in ComfyUI,
2. your Comfy account login,
3. the `COMFY_API_KEY` environment variable, set before starting ComfyUI.

Create a key at [platform.comfy.org](https://platform.comfy.org/profile/api-keys). **Store Capsules needs no key.**

## Notes

- **Logo transparency:** wire the `MASK` from LoadImage or a background-removal node into `logo_mask`. Without one, a plain white background is knocked out automatically.
- **Store sizes** follow the current Steamworks layout. Check [Steamworks](https://partner.steamgames.com/doc/store/assets) before you ship.
- **Originality:** the style-guide prompt keeps designs original, so a pitch that mentions a famous game keeps its genre and mood, not its logo or characters.
- **Disclosure:** Steam asks you to disclose AI-generated content in its content survey.

MIT licensed. Built at the Comfy hackathon.
