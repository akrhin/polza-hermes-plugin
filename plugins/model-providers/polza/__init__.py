"""
Polza.ai provider profile for Hermes Agent.

Supports provider routing, reasoning tokens, web search,
file parser, response healing, and public model catalog.
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

    # ── Constants ────────────────────────────────────────────
    _ALIAS_KEYS = frozenset({"provider", "reasoning_effort", "allow_fallbacks"})

    # Maps Polza plugin ID → Hermes context key
    _PLUGIN_ID_TO_CTX_KEY = {
        "web": "polza_web_search",
        "file-parser": "polza_file_parser",
        "response-healing": "polza_response_healing",
    }

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

    # ── Public API: called by Hermes transport ────────────────

    def build_extra_body(
        self, *, session_id: str | None = None, **context: Any
    ) -> dict[str, Any]:
        """Build Polza‑specific extra_body fields.

        Currently handles:
          - Provider routing (``provider: {only, ignore, order, sort, ...}``)
          - Web search plugin (``plugins: [{id: "web", ...}]``)
          - File parser plugin (``plugins: [{id: "file-parser", ...}]``)
          - Response healing plugin (``plugins: [{id: "response-healing", ...}]``)

        Provider routing priority:
          1. Alias format (``model@provider=...``) — parsed from model string
          2. ``provider_preferences`` from the Hermes agent context
             (set via agent.providers_allowed/ignored/order/provider_sort)
          3. ``model.extra_body.provider`` from config.yaml (fallback)

        When alias format is active, ``model.extra_body.provider`` and
        ``provider_preferences`` are *skipped* to avoid 400 conflict with
        Polza's alias server-side processing.

        Plugin loading order:
          1. ``model.extra_body.plugins`` from config.yaml (baseline)
          2. Context keys ``polza_web_search``, ``polza_file_parser``,
             ``polza_response_healing`` — override config by plugin ID
        """
        body: dict[str, Any] = {}

        # ── Session ID ──────────────────────────────────────────
        if session_id:
            body["session_id"] = session_id

        # ── Alias detection ─────────────────────────────────────
        # Polza supports model@provider=X&reasoning_effort=Y syntax.
        # When alias is detected, skip extra_body.provider to avoid
        # 400 conflict (Polza rejects duplicate provider/reasoning).
        model = context.get("model", "")
        alias = self._parse_model_alias(model) if isinstance(model, str) else None
        has_provider_alias = alias is not None and (
            "provider_only" in alias or "allow_fallbacks" in alias
        )

        # ── Provider routing ────────────────────────────────────
        if not has_provider_alias:
            prefs = context.get("provider_preferences")
            if not prefs:
                prefs = self._extra_body_provider_from_config()
            if prefs:
                body["provider"] = prefs

        # ── Plugins ─────────────────────────────────────────────
        # Sources (context overrides config):
        #   1. model.extra_body.plugins from config.yaml (base)
        #   2. context keys polza_web_search / polza_file_parser /
        #      polza_response_healing (override)
        plugins: list[dict[str, Any]] = self._plugins_from_config() or []

        # Apply context-level plugin overrides
        for plugin_id, ctx_key in self._PLUGIN_ID_TO_CTX_KEY.items():
            ctx_val = context.get(ctx_key)
            if ctx_val is not None:
                # Remove config version of this plugin if exists
                plugins = [p for p in plugins if p.get("id") != plugin_id]
                plugins.append({"id": plugin_id, **ctx_val})

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

        When ``model@reasoning_effort=X`` alias is detected, reasoning_config
        is *skipped* to avoid 400 conflict with Polza's alias processing.
        """
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}

        # ── Alias detection ─────────────────────────────────────
        model = context.get("model", "")
        alias = self._parse_model_alias(model) if isinstance(model, str) else None
        has_reasoning_alias = alias is not None and "reasoning_effort" in alias

        if reasoning_config is not None and not has_reasoning_alias:
            extra_body["reasoning"] = dict(reasoning_config)

        return extra_body, top_level

    # ── Internal helpers ──────────────────────────────────────

    @staticmethod
    def _parse_model_alias(model: str) -> dict[str, Any] | None:
        """Parse Polza alias format from the model string.

        Alias format: ``<model>@<key>=<value>&<key>=<value>``

        Supported keys (via Polza docs):
          - ``provider`` — maps to ``provider.only = [value]``
          - ``reasoning_effort`` — maps to ``reasoning.effort = value``
          - ``allow_fallbacks`` — maps to ``provider.allow_fallbacks = boolean``

        Returns a dict with parsed keys, or ``None`` if the model string
        contains no ``@`` or no recognised alias keys.
        """
        if not isinstance(model, str) or "@" not in model:
            return None

        after_at = model.split("@", 1)[1]
        if not after_at:
            return None

        result: dict[str, Any] = {}
        for pair in after_at.split("&"):
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            key, value = key.strip(), value.strip()
            if not key or not value:
                continue
            if key == "provider":
                result["provider_only"] = value
            elif key == "reasoning_effort":
                result["reasoning_effort"] = value
            elif key == "allow_fallbacks":
                result["allow_fallbacks"] = value.lower() == "true"

        return result if result else None

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

    @staticmethod
    def _plugins_from_config() -> list[dict[str, Any]] | None:
        """Read ``model.extra_body.plugins`` from config.yaml.

        Returns a list of plugin dicts (e.g. ``[{"id": "web", "max_results": 5}]``)
        or None if no plugins are defined in config.

        This allows users to enable plugins (web search, file parser, response
        healing) globally in config.yaml — works in all entry points without
        per-platform context keys.
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
            plugins = extra_body.get("plugins")
            if isinstance(plugins, list) and plugins:
                # Filter to known plugin IDs only
                known = PolzaProfile._PLUGIN_ID_TO_CTX_KEY.keys()
                return [dict(p) for p in plugins if isinstance(p, dict) and p.get("id") in known]
        except Exception:
            logger.debug("Could not read model.extra_body.plugins from config", exc_info=True)
        return None


# ── Provider registration ──────────────────────────────────

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
