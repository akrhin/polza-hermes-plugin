"""
Polza.ai image generation backend via OpenAI-compatible /v2/images/generations.

Polza's image models use the standard OpenAI images API (POST /v2/images/generations),
NOT the chat-completions-with-modalities protocol that OpenRouter uses.
This provider calls the images endpoint directly, downloads the result,
and saves it locally.

Default models (cheapest on Polza):
  - yandex/yandex-art          — 2.91 RUB/image  (fast, reliable)
  - seedream/5-pro-text-to-image — varies         (fallback)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    save_url_image,
    success_response,
)

logger = logging.getLogger(__name__)

# Cheap image models on Polza (per-request RUB prices)
_POLZA_DEFAULT = "yandex/yandex-art"                    # 2.91 RUB — verified working
_POLZA_FALLBACK = "seedream/5-pro-text-to-image"         # fallback

# Timeout per image generation request
_REQUEST_TIMEOUT = 120.0

# Supported aspect ratio -> size strings for /v2/images/generations
_SIZES = {
    "square": "1024x1024",
    "landscape": "1792x1024",
    "portrait": "1024x1792",
}


def _load_image_gen_config() -> Dict[str, Any]:
    """Read the ``image_gen`` section from config.yaml (``{}`` on failure)."""
    try:
        from hermes_cli.config import load_config  # noqa: PLC0415 — late import avoids hermetic dep

        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else None
        return section if isinstance(section, dict) else {}
    except ImportError:
        logger.debug("could not import hermes_cli.config")
        return {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("could not load image_gen config: %s", exc)
        return {}


def _build_images_endpoint(base_url: str) -> str:
    """Build the /v2/images/generations endpoint URL from the base API URL.

    The images endpoint lives at a different path from the chat completions API.
    Examples:
      https://polza.ai/api/v1  →  https://polza.ai/api/v2/images/generations
      https://polza.ai/api     →  https://polza.ai/api/v2/images/generations
    """
    base = base_url.rstrip("/")
    # If base_url ends with /api/v1, images live at /api/v2/...
    if base.endswith("/api/v1"):
        base = base[:-len("/api/v1")] + "/api"
    return urljoin(base + "/", "v2/images/generations")


def _dedupe_models(models: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for model in models:
        m = (model or "").strip()
        if not m or m in seen:
            continue
        seen.add(m)
        out.append(m)
    return out


class PolzaImageProvider(ImageGenProvider):
    """Image generation via Polza.ai OpenAI-compatible /v2/images/generations.

    Polza exposes image models through the standard OpenAI images API, not
    through chat completions with modalities. This provider hits the dedicated
    endpoint, downloads the ephemeral URL, and saves the result locally.
    """

    def __init__(
        self,
        *,
        provider_name: str,
        display_name: str,
        runtime_name: str,
        config_key: str,
        model_env_var: str,
        setup_schema: Dict[str, Any],
    ) -> None:
        self._name = provider_name
        self._display = display_name
        self._runtime_name = runtime_name
        self._config_key = config_key
        self._model_env_var = model_env_var
        self._setup_schema = setup_schema

    # -- required ImageGenProvider interface ---------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._display

    def is_available(self) -> bool:
        try:
            runtime = self._resolve_runtime()
        except (ImportError, KeyError, TypeError):
            return False
        except Exception:  # noqa: BLE001 — resolve_runtime can fail in unexpected ways
            logger.debug("is_available: unexpected error", exc_info=True)
            return False
        return bool(str(runtime.get("api_key") or "").strip())

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text"],
            "max_reference_images": 0,
        }

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "yandex/yandex-art",
                "display": "Yandex ART",
                "strengths": "Fast, reliable, 2.91 RUB/image",
                "price": "2.91 RUB",
            },
            {
                "id": "seedream/5-pro-text-to-image",
                "display": "Seedream 5 Pro",
                "strengths": "High quality fallback",
                "price": "varies",
            },
            {
                "id": "qwen/image",
                "display": "Qwen Image",
                "strengths": "LLM-based, complex text",
                "price": "2.25-3.00 RUB",
            },
        ]

    def default_model(self) -> Optional[str]:
        return self._resolve_model()

    def get_setup_schema(self) -> Dict[str, Any]:
        return dict(self._setup_schema)

    # -- credential resolution ------------------------------------------------

    def _resolve_runtime(self) -> Dict[str, Any]:
        """Resolve ``(base_url, api_key)`` via the shared runtime resolver."""
        from hermes_cli.runtime_provider import resolve_runtime_provider  # noqa: PLC0415

        return resolve_runtime_provider(requested=self._runtime_name)

    # -- model resolution -----------------------------------------------------

    def _resolve_model(self, explicit: Optional[str] = None) -> str:
        """Pick the image model (first of :meth:`_resolve_model_chain`)."""
        return self._resolve_model_chain(explicit)[0]

    def _resolve_model_chain(self, explicit: Optional[str] = None) -> list[str]:
        """Ordered model attempts for this request.

        Precedence: explicit override -> POLZA_IMAGE_MODEL env
        -> image_gen.polza.model -> image_gen.model -> cheap Polza chain.
        """
        if isinstance(explicit, str) and explicit.strip():
            return [explicit.strip()]

        env_override = os.environ.get(self._model_env_var, "").strip()
        if env_override:
            return [env_override]

        cfg = _load_image_gen_config()
        scoped = cfg.get(self._config_key) if isinstance(cfg.get(self._config_key), dict) else {}
        if isinstance(scoped, dict):
            value = scoped.get("model")
            if isinstance(value, str) and value.strip():
                return [value.strip()]

        top = cfg.get("model")
        if isinstance(top, str) and top.strip():
            return [top.strip()]

        return _dedupe_models([_POLZA_DEFAULT, _POLZA_FALLBACK])

    # -- image generation -----------------------------------------------------

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate an image via Polza's /v2/images/generations endpoint.

        Polza's image models use the standard OpenAI images API. The result
        is an ephemeral URL on S3; we download and save it locally.
        Image-to-image / editing is not supported (Polza models are
        text-to-image only).
        """
        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(
                error="Prompt is required",
                error_type="invalid_input",
                provider=self._name,
                prompt="",
                aspect_ratio=aspect_ratio,
            )

        # Polza image models are text-to-image only — reject reference images.
        if image_url or reference_image_urls:
            return error_response(
                error=(
                    f"{self._display} is text-to-image only. "
                    f"Remove image_url / reference_image_urls and try again."
                ),
                error_type="not_supported",
                provider=self._name,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )

        aspect = resolve_aspect_ratio(aspect_ratio)
        size = _SIZES.get(aspect, "1024x1024")
        model_chain = self._resolve_model_chain(kwargs.get("model"))

        try:
            runtime = self._resolve_runtime()
        except Exception as exc:  # noqa: BLE001
            return error_response(
                error=f"Could not resolve {self._display} credentials: {exc}",
                error_type="missing_api_key",
                provider=self._name,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        api_key = str(runtime.get("api_key") or "").strip()
        base_url = str(runtime.get("base_url") or "").strip().rstrip("/")
        if not api_key or not base_url:
            return error_response(
                error=(
                    f"No {self._display} credentials found. "
                    f"Configure {self._display} in `hermes tools`."
                ),
                error_type="missing_api_key",
                provider=self._name,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        images_endpoint = _build_images_endpoint(base_url)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Dict[str, Any]] = None
        for i, model_id in enumerate(model_chain):
            is_last = i == len(model_chain) - 1
            payload = {
                "model": model_id,
                "prompt": prompt,
                "n": 1,
                "size": size,
            }

            try:
                response = requests.post(
                    images_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
            except requests.HTTPError as exc:
                resp = exc.response
                status = resp.status_code if resp is not None else 0
                try:
                    err_msg = resp.json().get("error", {}).get(
                        "message", resp.text[:300]
                    )
                except Exception:
                    err_msg = resp.text[:300] if resp is not None else str(exc)
                logger.error(
                    "%s image gen failed (%d) on %s: %s",
                    self._name, status, model_id, err_msg,
                )
                if not is_last:
                    logger.info(
                        "%s model %s failed; retrying with fallback %s",
                        self._name, model_id, model_chain[i + 1],
                    )
                    continue
                last_error = error_response(
                    error=f"{self._display} image generation failed ({status}): {err_msg}",
                    error_type="api_error",
                    provider=self._name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )
                return last_error
            except requests.Timeout:
                if not is_last:
                    logger.info(
                        "%s model %s timed out; retrying with fallback %s",
                        self._name, model_id, model_chain[i + 1],
                    )
                    continue
                return error_response(
                    error=f"{self._display} image generation timed out "
                    f"({int(_REQUEST_TIMEOUT)}s)",
                    error_type="timeout",
                    provider=self._name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )
            except requests.ConnectionError as exc:
                if not is_last:
                    logger.info(
                        "%s model %s connection error; retrying with fallback %s",
                        self._name, model_id, model_chain[i + 1],
                    )
                    continue
                return error_response(
                    error=f"{self._display} connection error: {exc}",
                    error_type="connection_error",
                    provider=self._name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )

            try:
                result = response.json()
            except Exception as exc:  # noqa: BLE001
                return error_response(
                    error=f"{self._display} returned invalid JSON: {exc}",
                    error_type="invalid_response",
                    provider=self._name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )

            # Extract image URL from response
            data = result.get("data") if isinstance(result, dict) else None
            if not isinstance(data, list) or not data:
                if not is_last:
                    continue
                return error_response(
                    error=f"{self._display} returned no image data.",
                    error_type="empty_response",
                    provider=self._name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )

            first = data[0]
            img_url = first.get("url") if isinstance(first, dict) else None
            if not isinstance(img_url, str) or not img_url.strip():
                if not is_last:
                    continue
                return error_response(
                    error=f"{self._display} returned no image URL.",
                    error_type="empty_response",
                    provider=self._name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )

            # Download the ephemeral URL and save locally
            try:
                saved_path = save_url_image(img_url, prefix=f"{self._name}_gen")
            except Exception as exc:  # noqa: BLE001
                return error_response(
                    error=f"Could not save generated image: {exc}",
                    error_type="io_error",
                    provider=self._name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )

            return success_response(
                image=str(saved_path),
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
                provider=self._name,
            )

        return last_error or error_response(
            error=f"{self._display} image generation failed after trying all models.",
            error_type="api_error",
            provider=self._name,
            model=model_chain[-1] if model_chain else "",
            prompt=prompt,
            aspect_ratio=aspect,
        )


def _build_providers() -> List[PolzaImageProvider]:
    return [
        PolzaImageProvider(
            provider_name="polza",
            display_name="Polza AI (image)",
            runtime_name="polza",
            config_key="polza",
            model_env_var="POLZA_IMAGE_MODEL",
            setup_schema={
                "name": "Polza AI (image)",
                "badge": "paid",
                "tag": "Image generation via Polza.ai — uses POLZA_API_KEY",
                "env_vars": [
                    {
                        "key": "POLZA_API_KEY",
                        "prompt": "Polza API key",
                        "url": "https://polza.ai/dashboard/api-keys",
                    }
                ],
            },
        ),
    ]


def register(ctx: Any) -> None:
    """Register the Polza AI image gen provider."""
    for provider in _build_providers():
        ctx.register_image_gen_provider(provider)
