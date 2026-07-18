"""
Polza.ai provider profile for Hermes Agent.

Supports provider routing, reasoning tokens, web search,
file parser, response healing, and public model catalog.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import yaml
from providers import register_provider
from providers.base import ProviderProfile

logger = logging.getLogger(__name__)

# ── Config helpers (shared between build_extra_body and plugins) ──

_CONFIG_PATH = os.path.expanduser("~/.hermes/config.yaml")


def _read_extra_body_section() -> dict[str, Any] | None:
    """Read ``model.extra_body`` from config.yaml.

    Returns the ``model.extra_body`` dict or ``None`` if the file,
    model section, or extra_body section is missing or invalid.
    """
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        logger.debug("Could not read config.yaml", exc_info=True)
        return None

    if not isinstance(cfg, dict):
        return None
    model_cfg = cfg.get("model")
    if not isinstance(model_cfg, dict):
        return None
    extra_body = model_cfg.get("extra_body")
    return extra_body if isinstance(extra_body, dict) else None


def _extra_body_provider_from_config() -> dict[str, Any] | None:
    """Read ``model.extra_body.provider`` from config.yaml."""
    extra = _read_extra_body_section()
    if extra is None:
        return None
    provider = extra.get("provider")
    return dict(provider) if isinstance(provider, dict) and provider else None


# Known Polza plugin IDs for filtering config entries
_KNOWN_PLUGIN_IDS = frozenset({"web", "file-parser", "response-healing"})


def _plugins_from_config() -> list[dict[str, Any]] | None:
    """Read ``model.extra_body.plugins`` from config.yaml.

    Returns only plugins whose ``id`` matches known Polza plugin IDs.
    """
    extra = _read_extra_body_section()
    if extra is None:
        return None
    plugins = extra.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return None
    return [dict(p) for p in plugins if isinstance(p, dict) and p.get("id") in _KNOWN_PLUGIN_IDS]


class PolzaProfile(ProviderProfile):
    """Polza.ai aggregator — provider routing, reasoning, plugins passthrough."""

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
        """Fetch Polza.ai model catalog — public endpoint, no auth required."""
        return super().fetch_models(api_key=None, base_url=base_url, timeout=timeout)

    # ── Public API: called by Hermes transport ────────────────

    def build_extra_body(
        self, *, session_id: str | None = None, **context: Any
    ) -> dict[str, Any]:
        """Build Polza‑specific extra_body fields.

        Handles provider routing, web search, file parser, and
        response healing plugins.

        See the class docstring and ARCHITECTURE.md for the full
        priority chain and conflict-avoidance rules.
        """
        body: dict[str, Any] = {}

        if session_id:
            body["session_id"] = session_id

        # ── Alias detection ────────────────────────────────────
        model = context.get("model", "")
        alias = self._parse_model_alias(model) if isinstance(model, str) else None
        has_provider_alias = alias is not None and (
            "provider_only" in alias or "allow_fallbacks" in alias
        )

        # ── Provider routing ───────────────────────────────────
        if not has_provider_alias:
            prefs = context.get("provider_preferences")
            if not prefs:
                prefs = _extra_body_provider_from_config()
            if prefs:
                body["provider"] = prefs

        # ── Plugins ────────────────────────────────────────────
        plugins: list[dict[str, Any]] = _plugins_from_config() or []

        for plugin_id, ctx_key in self._PLUGIN_ID_TO_CTX_KEY.items():
            ctx_val = context.get(ctx_key)
            if ctx_val is not None:
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

        When ``model@reasoning_effort=X`` alias is detected, reasoning_config
        is *skipped* to avoid 400 conflict with Polza's alias processing.
        """
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}

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

        Supported keys:
          - ``provider`` → ``provider.only = [value]``
          - ``reasoning_effort`` → ``reasoning.effort = value``
          - ``allow_fallbacks`` → ``provider.allow_fallbacks = boolean``
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
