"""Minimal Comfy Router client (standard library only).

Auth, in order:
1. the ComfyUI account API key ComfyUI hands to nodes (hidden input),
2. the ComfyUI account login token (hidden input),
3. the COMFY_API_KEY environment variable.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid

ROUTER_BASE = os.environ.get("COMFY_ROUTER_BASE_URL", "https://api.comfy.org").rstrip("/")
CLAUDE_MODEL = "anthropic/claude-sonnet-5-5"
USER_AGENT = "comfyui-launch-kit/1.0"


class RouterError(RuntimeError):
    pass


def auth_headers(api_key: str | None = None, auth_token: str | None = None) -> dict[str, str]:
    key = (api_key or "").strip() or os.environ.get("COMFY_API_KEY", "").strip()
    if key:
        return {"X-API-Key": key}
    if (auth_token or "").strip():
        return {"Authorization": f"Bearer {auth_token.strip()}"}
    raise RouterError(
        "No Comfy API key found. Sign in to your Comfy account in ComfyUI "
        "(Settings → User → API key), or set the COMFY_API_KEY environment variable before starting ComfyUI. "
        "Create a key at https://platform.comfy.org/profile/api-keys"
    )


def run_model(model: str, body: dict, headers: dict[str, str], timeout: float = 180, retries: int = 2) -> dict:
    """POST /v2/models/{model}: waits for the result. Retries 5xx and network errors with the same idempotency key."""
    url = f"{ROUTER_BASE}/v2/models/{model}"
    data = json.dumps(body).encode("utf-8")
    idem = str(uuid.uuid4())
    last: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": idem,
                "User-Agent": USER_AGENT,
                **headers,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            if e.code == 402:
                raise RouterError("Out of Comfy credits: top up your workspace at platform.comfy.org.") from e
            if e.code in (401, 403):
                raise RouterError(f"Comfy rejected the API key ({e.code}). Check it at platform.comfy.org.") from e
            if e.code < 500:
                raise RouterError(f"{model} rejected the request ({e.code}): {detail}") from e
            last = RouterError(f"{model} failed ({e.code}): {detail}")
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RouterError(f"{model} did not respond: {last}")


def claude(prompt: str, headers: dict[str, str], system: str | None = None, image_png_b64: str | None = None, max_tokens: int = 4000) -> str:
    content: list[dict] = []
    if image_png_b64:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_png_b64}})
    content.append({"type": "text", "text": prompt})
    body: dict = {"max_tokens": max_tokens, "messages": [{"role": "user", "content": content}]}
    if system:
        body["system"] = system
    out = run_model(CLAUDE_MODEL, body, headers)
    return "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")


def extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise RouterError("The model did not return JSON.")
    return json.loads(text[start : end + 1])
