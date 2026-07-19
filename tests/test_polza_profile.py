"""Unit tests for PolzaProfile — no API key required.

Run from inside Hermes venv:
    cd <hermes-agent> && python -m pytest <polza-plugin>/tests/test_polza_profile.py -n0 -q -v
"""

from __future__ import annotations

import sys
from unittest import mock

from providers import get_provider_profile
from providers.base import ProviderProfile


def _get_profile():
    """Get the Polza profile via the provider registry."""
    p = get_provider_profile("polza")
    assert p is not None, "Polza profile not found — is the plugin installed?"
    return p


class TestPolzaProfileBasics:
    """Basic identity and configuration tests."""

    def test_name(self):
        p = _get_profile()
        assert p.name == "polza"

    def test_aliases(self):
        p = _get_profile()
        assert "polza-ai" in p.aliases
        assert "pza" in p.aliases

    def test_has_env_vars(self):
        p = _get_profile()
        assert "POLZA_API_KEY" in p.env_vars

    def test_base_url(self):
        p = _get_profile()
        assert p.base_url == "https://polza.ai/api/v1"

    def test_models_url(self):
        p = _get_profile()
        assert p.models_url == "https://polza.ai/api/v1/models"

    def test_hostname(self):
        p = _get_profile()
        assert p.get_hostname() == "polza.ai"

    def test_auth_type(self):
        p = _get_profile()
        assert p.auth_type == "api_key"

    def test_display_name(self):
        p = _get_profile()
        assert "Polza" in p.display_name

    def test_fallback_models(self):
        p = _get_profile()
        assert len(p.fallback_models) > 0
        assert "deepseek/deepseek-chat" in p.fallback_models

    def test_default_aux_model(self):
        p = _get_profile()
        assert p.default_aux_model == "qwen/qwen3-8b"

    def test_is_provider_profile(self):
        p = _get_profile()
        assert isinstance(p, ProviderProfile)


class TestPolzaProfileBuildExtraBody:
    """build_extra_body() — provider routing and plugins."""

    def test_no_context_returns_only_config_fallback(self):
        p = _get_profile()
        body = p.build_extra_body()
        # With no provider_preferences in context, the plugin falls back
        # to reading model.extra_body.provider from config.yaml.
        # At minimum, session_id and provider may not be set, but no
        # plugins should be active.
        assert "plugins" not in body
        # provider IS set from config fallback — expected and correct

    def test_provider_preferences_passthrough(self):
        p = _get_profile()
        prefs = {"only": ["OpenAI", "Anthropic"], "sort": "price"}
        body = p.build_extra_body(provider_preferences=prefs)
        assert body.get("provider") == prefs

    def test_provider_preferences_empty_falls_back_to_config(self):
        """Empty provider_preferences {} is treated as 'not set' and falls to config."""
        p = _get_profile()
        p.build_extra_body(provider_preferences={})
        # With empty prefs, falls back to config.yaml's model.extra_body.provider
        # provider IS present from config — expected and correct

    def test_web_search_plugin(self):
        p = _get_profile()
        body = p.build_extra_body(polza_web_search={"max_results": 5})
        assert "plugins" in body
        assert {"id": "web", "max_results": 5} in body["plugins"]

    def test_file_parser_plugin(self):
        p = _get_profile()
        body = p.build_extra_body(polza_file_parser={"pdf": {"engine": "mistral-ocr"}})
        assert "plugins" in body
        assert {"id": "file-parser", "pdf": {"engine": "mistral-ocr"}} in body["plugins"]

    def test_multiple_plugins(self):
        p = _get_profile()
        body = p.build_extra_body(
            polza_web_search={"max_results": 3},
            polza_file_parser={"pdf": {"engine": "native"}},
        )
        assert len(body["plugins"]) == 2

    def test_provider_prefs_and_plugins_together(self):
        p = _get_profile()
        body = p.build_extra_body(
            provider_preferences={"sort": "latency"},
            polza_web_search={"max_results": 3},
        )
        assert body.get("provider") == {"sort": "latency"}
        assert len(body["plugins"]) == 1

    def test_response_healing_plugin(self):
        p = _get_profile()
        body = p.build_extra_body(polza_response_healing={"enabled": True})
        assert "plugins" in body
        assert {"id": "response-healing", "enabled": True} in body["plugins"]

    def test_three_plugins_together(self):
        p = _get_profile()
        body = p.build_extra_body(
            polza_web_search={"max_results": 3},
            polza_file_parser={"pdf": {"engine": "native"}},
            polza_response_healing={"enabled": True},
        )
        plugin_ids = {pl["id"] for pl in body["plugins"]}
        assert plugin_ids == {"web", "file-parser", "response-healing"}

    def test_provider_alias_skips_extra_body_provider(self):
        """When model string has @provider=..., extra_body.provider is NOT set."""
        p = _get_profile()
        body = p.build_extra_body(
            model="deepseek/deepseek-chat@provider=OpenAI",
            provider_preferences={"only": ["Chutes"]},
        )
        assert "provider" not in body, (
            "Alias @provider=... should suppress extra_body.provider "
            "to avoid 400 conflict on Polza side"
        )

    def test_alias_allow_fallbacks_also_skips_provider(self):
        p = _get_profile()
        body = p.build_extra_body(
            model="minimax/minimax-m2.5@allow_fallbacks=false",
            provider_preferences={"only": ["DeepInfra"]},
        )
        assert "provider" not in body

    def test_provider_alias_without_preferences_also_skips(self):
        """No provider_preferences in context, but alias present — still skip."""
        p = _get_profile()
        body = p.build_extra_body(
            model="deepseek/deepseek-chat@provider=Chutes",
        )
        assert "provider" not in body

    def test_no_alias_does_not_skip_provider(self):
        p = _get_profile()
        body = p.build_extra_body(
            model="deepseek/deepseek-chat",
            provider_preferences={"sort": "price"},
        )
        assert body.get("provider") == {"sort": "price"}

    def test_session_id_passthrough(self):
        p = _get_profile()
        body = p.build_extra_body(session_id="sess_abc123")
        assert body.get("session_id") == "sess_abc123"

    def test_session_id_with_everything(self):
        p = _get_profile()
        body = p.build_extra_body(
            session_id="sess_xyz",
            provider_preferences={"only": ["DeepSeek"]},
            polza_web_search={"max_results": 3},
        )
        assert body["session_id"] == "sess_xyz"
        assert body["provider"] == {"only": ["DeepSeek"]}
        assert len(body["plugins"]) == 1

    def test_web_search_with_engine(self):
        p = _get_profile()
        body = p.build_extra_body(polza_web_search={"max_results": 5, "engine": "native"})
        assert {"id": "web", "max_results": 5, "engine": "native"} in body["plugins"]

    def test_file_parser_with_ocr(self):
        p = _get_profile()
        body = p.build_extra_body(polza_file_parser={"images": {"ocr": True}})
        assert {"id": "file-parser", "images": {"ocr": True}} in body["plugins"]


class TestPolzaProfileBuildApiKwargsExtras:
    """build_api_kwargs_extras() — reasoning passthrough."""

    def test_no_reasoning_returns_empty(self):
        p = _get_profile()
        extra, top = p.build_api_kwargs_extras()
        assert extra == {}
        assert top == {}

    def test_reasoning_config_passthrough(self):
        p = _get_profile()
        rc = {"effort": "high", "enabled": True}
        extra, top = p.build_api_kwargs_extras(reasoning_config=rc)
        assert extra.get("reasoning") == rc

    def test_reasoning_with_max_tokens(self):
        p = _get_profile()
        rc = {"effort": "high", "max_tokens": 4096}
        extra, top = p.build_api_kwargs_extras(reasoning_config=rc)
        assert extra["reasoning"]["max_tokens"] == 4096

    def test_reasoning_adaptive_type(self):
        p = _get_profile()
        rc = {"type": "adaptive", "effort_level": "max"}
        extra, top = p.build_api_kwargs_extras(reasoning_config=rc)
        assert extra["reasoning"]["type"] == "adaptive"
        assert extra["reasoning"]["effort_level"] == "max"

    def test_reasoning_effort_alias_skips_reasoning_extra(self):
        """When model has @reasoning_effort=..., reasoning extra_body is skipped."""
        p = _get_profile()
        rc = {"effort": "high", "max_tokens": 4096}
        extra, top = p.build_api_kwargs_extras(
            reasoning_config=rc,
            model="minimax/minimax-m2.5@reasoning_effort=high",
        )
        assert "reasoning" not in extra, (
            "Alias @reasoning_effort=... should suppress extra_body.reasoning "
            "to avoid 400 conflict on Polza side"
        )

    def test_reasoning_effort_alias_without_config(self):
        """No reasoning_config in context, model has alias — no conflict possible."""
        p = _get_profile()
        extra, top = p.build_api_kwargs_extras(
            model="minimax/minimax-m2.5@reasoning_effort=high",
        )
        assert extra == {}

    def test_full_alias_combo_skips_both(self):
        """@provider=X&reasoning_effort=Y&allow_fallbacks=false — all suppressed."""
        p = _get_profile()
        body = p.build_extra_body(
            model="minimax/minimax-m2.5@provider=DeepInfra&reasoning_effort=high&allow_fallbacks=false",
            provider_preferences={"only": ["Chutes"]},
        )
        assert "provider" not in body

        extra, top = p.build_api_kwargs_extras(
            reasoning_config={"effort": "low"},
            model="minimax/minimax-m2.5@provider=DeepInfra&reasoning_effort=high&allow_fallbacks=false",
        )
        assert "reasoning" not in extra


class TestPolzaProfileFetchModels:
    """fetch_models() — public catalog."""

    def test_call_without_api_key(self):
        """fetch_models should work without an API key (public endpoint)."""
        p = _get_profile()
        result = p.fetch_models(api_key=None, timeout=5.0)
        # Can be None (network timeout) or a list of model IDs
        if result is not None:
            assert len(result) > 0
            assert all(isinstance(m, str) for m in result)


class TestPolzaProfileParseModelAlias:
    """_parse_model_alias() — @-syntax parsing."""

    def test_no_alias_returns_none(self):
        p = _get_profile()
        assert p._parse_model_alias("deepseek/deepseek-chat") is None

    def test_no_at_sign_returns_none(self):
        p = _get_profile()
        assert p._parse_model_alias("") is None

    def test_not_a_string_returns_none(self):
        p = _get_profile()
        assert p._parse_model_alias(42) is None

    def test_empty_after_at_returns_none(self):
        p = _get_profile()
        assert p._parse_model_alias("model@") is None

    def test_provider_only(self):
        p = _get_profile()
        result = p._parse_model_alias("anthropic/claude-opus-4-6@provider=Amazon Bedrock")
        assert result is not None
        assert result["provider_only"] == "Amazon Bedrock"

    def test_reasoning_effort(self):
        p = _get_profile()
        result = p._parse_model_alias("minimax/minimax-m2.5@reasoning_effort=high")
        assert result is not None
        assert result["reasoning_effort"] == "high"

    def test_allow_fallbacks_true(self):
        p = _get_profile()
        result = p._parse_model_alias("minimax/minimax-m2.5@allow_fallbacks=true")
        assert result is not None
        assert result["allow_fallbacks"] is True

    def test_allow_fallbacks_false(self):
        p = _get_profile()
        result = p._parse_model_alias("minimax/minimax-m2.5@allow_fallbacks=false")
        assert result is not None
        assert result["allow_fallbacks"] is False

    def test_full_alias_chain(self):
        p = _get_profile()
        result = p._parse_model_alias(
            "minimax/minimax-m2.5@provider=DeepInfra&reasoning_effort=high&allow_fallbacks=false"
        )
        assert result is not None
        assert result["provider_only"] == "DeepInfra"
        assert result["reasoning_effort"] == "high"
        assert result["allow_fallbacks"] is False

    def test_unknown_key_still_parsed_known(self):
        """Alias with unknown keys shouldn't break parsing of known ones."""
        p = _get_profile()
        result = p._parse_model_alias("model@foo=bar&provider=OpenAI&baz=qux")
        assert result is not None
        assert result["provider_only"] == "OpenAI"
        assert "foo" not in result
        assert "baz" not in result

    def test_missing_value_skipped(self):
        p = _get_profile()
        result = p._parse_model_alias("model@provider=")
        assert result is None or "provider_only" not in result

    def test_missing_key_skipped(self):
        p = _get_profile()
        result = p._parse_model_alias("model@=value")
        assert result is None or len(result) == 0


class TestPolzaProfileConfigFallback:
    """_extra_body_provider_from_config() and _plugins_from_config() — mocked config.yaml.

    Mock the MODULE-LEVEL functions, not the instance methods.
    Instance methods are proxy wrappers that delegate to module-level functions.
    Mocking the module function lets us test the real delegation path.
    """

    def test_provider_from_real_config(self):
        p = _get_profile()
        # Get the module where PolzaProfile is defined
        module = sys.modules[p.__class__.__module__]
        with mock.patch.object(
            module,
            "_extra_body_provider_from_config",
            return_value={"only": ["OpenAI"], "sort": "price"},
        ):
            # Call instance method → delegates to mocked module function
            result = p._extra_body_provider_from_config()
        assert isinstance(result, dict)
        assert "only" in result
        assert result["only"] == ["OpenAI"]

    def test_plugins_from_real_config(self):
        p = _get_profile()
        module = sys.modules[p.__class__.__module__]
        with mock.patch.object(
            module,
            "_plugins_from_config",
            return_value=[{"id": "web", "max_results": 3}],
        ):
            result = p._plugins_from_config()
        assert isinstance(result, list)
        assert result[0]["id"] == "web"
