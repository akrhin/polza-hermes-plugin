"""
Polza.ai provider profile for Hermes Agent.

Supports provider routing, reasoning tokens, web search,
public model catalog, and RUB billing with balance tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from providers import register_provider
from providers.base import ProviderProfile

logger = logging.getLogger(__name__)


class PolzaProfile(ProviderProfile):
    """Polza.ai aggregator — provider routing, reasoning, plugins passthrough."""

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Fetch Polza.ai model catalog — public endpoint, no auth required.

        The GET /v1/models endpoint returns the full catalog without
        authentication, so we skip the API key to keep it zero-cost.
        """
        return super().fetch_models(api_key=None, base_url=base_url, timeout=timeout)

    def build_extra_body(
        self, *, session_id: str | None = None, **context: Any
    ) -> dict[str, Any]:
        """Build Polza‑specific extra_body fields.

        Currently handles:
          - Provider routing (``provider: {only, ignore, order, sort, ...}``)
          - Web search plugin (``plugins: [{id: "web", ...}]``)
          - File parser plugin (``plugins: [{id: "file-parser", ...}]``)
        """
        body: dict[str, Any] = {}

        # ── Provider routing ────────────────────────────────────
        # Maps Hermes ``provider_preferences`` → Polza ``provider`` object.
        # Fields: only, ignore, order, sort, max_price, allow_fallbacks.
        prefs = context.get("provider_preferences")
        if prefs:
            body["provider"] = prefs

        # ── Plugins ─────────────────────────────────────────────
        # Web search:  body["plugins"] = [{"id": "web", "max_results": 5}]
        # File parser: body["plugins"] = [{"id": "file-parser", "pdf": {"engine": "mistral-ocr"}}]
        plugins: list[dict[str, Any]] = []

        web_search = context.get("polza_web_search")
        if web_search:
            plugins.append({"id": "web", **web_search})

        file_parser = context.get("polza_file_parser")
        if file_parser:
            plugins.append({"id": "file-parser", **file_parser})

        if plugins:
            body["plugins"] = plugins

        return body

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        **context: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Polza passes reasoning config directly as extra_body.reasoning.

        The ``reasoning`` object supports:
          - effort: none | minimal | low | medium | high | xhigh | max
          - max_tokens: int (hard budget for explicit models)
          - summary: auto | concise | detailed
          - type: adaptive (for Claude Opus 4.7+)
          - effort_level: low | medium | high | max (adaptive models)
          - enabled: bool
          - exclude: bool

        Polza accepts the full reasoning_config dict as-is from Hermes.
        """
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}

        if reasoning_config is not None:
            extra_body["reasoning"] = dict(reasoning_config)

        return extra_body, top_level


polza = PolzaProfile(
    name="polza",
    aliases=("polza-ai", "pza"),
    display_name="PolzaAI",
    description="Polza.ai — unified API for 200+ models, RUB billing",
    signup_url="https://polza.ai/dashboard/api-keys",
    env_vars=("POLZA_API_KEY",),
    base_url="https://polza.ai/api/v1",
    models_url="https://polza.ai/api/v1/models",
    hostname="polza.ai",
    auth_type="api_key",
    default_aux_model="qwen/qwen3-8b",
    fallback_models=(
        "deepseek/deepseek-chat",
        "openai/gpt-4o-mini",
        "qwen/qwen3-8b",
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-flash",
    ),
)

register_provider(polza)
