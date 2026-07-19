"""Pure helper functions for Polza image gen — no Hermes dependencies.

These are extracted so unit tests can import them without pulling in
the full Hermes agent stack (agent.image_gen_provider, etc.).
"""

from __future__ import annotations

from urllib.parse import urljoin

_POLZA_DEFAULT = "yandex/yandex-art"
_POLZA_FALLBACK = "seedream/5-pro-text-to-image"


def _build_images_endpoint(base_url: str) -> str:
    """Build the /v2/images/generations endpoint URL from the base API URL.

    Examples:
      https://polza.ai/api/v1  →  https://polza.ai/api/v2/images/generations
      https://polza.ai/api     →  https://polza.ai/api/v2/images/generations
    """
    base = base_url.rstrip("/")
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")] + "/api"
    return urljoin(base + "/", "v2/images/generations")


def _dedupe_models(models: list[str]) -> list[str]:
    """Deduplicate a model list preserving order, stripping whitespace."""
    out: list[str] = []
    seen: set[str] = set()
    for model in models:
        m = (model or "").strip()
        if not m or m in seen:
            continue
        seen.add(m)
        out.append(m)
    return out
