"""
Polza.ai provider profile for Hermes Agent.

Supports provider routing, reasoning tokens, web search,
and public model catalog.
"""

from __future__ import annotations

import logging
import os
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

        Provider routing priority:
          1. ``provider_preferences`` from the Hermes agent context
             (set via agent.providers_allowed/ignored/order/provider_sort)
          2. ``model.extra_body.provider`` from config.yaml (fallback)
             — allows users to set provider filtering in config.yaml
               without needing CLI flags or agent-level attrs.
        """
        body: dict[str, Any] = {}

        # ── Session ID ──────────────────────────────────────────
        # Forwards Hermes session_id to Polza for request correlation.
        if session_id:
            body["session_id"] = session_id

        # ── Provider routing ────────────────────────────────────
        # Priority 1: Hermes agent context (provider_preferences)
        # Priority 2: model.extra_body.provider from config (fallback)
        prefs = context.get("provider_preferences")
        if not prefs:
            prefs = self._extra_body_provider_from_config()
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

    @staticmethod
    def _extra_body_provider_from_config() -> dict[str, Any] | None:
        """Read ``model.extra_body.provider`` from config.yaml.

        Returns the ``provider`` dict inside ``model.extra_body`` when
        present and valid, or None if no config-based routing is defined.

        This allows users to set provider filtering in a single place
        (the ``model`` section) that works for **all** entry points:
        CLI, WebUI, Telegram, Discord — without needing per-platform
        agent-level attrs.
        """
        try:
            import yaml

            with open(os.path.expanduser("~/.hermes/config.yaml")) as f:
                cfg = yaml.safe_load(f)
            model_cfg = cfg.get("model", {})
            if not isinstance(model_cfg, dict):
                return None
            extra_body = model_cfg.get("extra_body")
            if not isinstance(extra_body, dict):
                return None
            provider = extra_body.get("provider")
            if isinstance(provider, dict) and provider:
                return dict(provider)
        except Exception:
            logger.debug("Could not read model.extra_body.provider from config", exc_info=True)
        return None

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
    description="Polza.ai — unified API for 200+ models",
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
