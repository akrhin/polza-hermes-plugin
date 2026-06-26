"""Unit tests for PolzaProfile — no API key required.

Run from inside Hermes venv:
    cd <hermes-agent> && python -m pytest <polza-plugin>/tests/test_polza_profile.py -n0 -q -v
"""

from __future__ import annotations

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

    def test_no_context_returns_empty(self):
        p = _get_profile()
        body = p.build_extra_body()
        assert body == {}

    def test_provider_preferences_passthrough(self):
        p = _get_profile()
        prefs = {"only": ["OpenAI", "Anthropic"], "sort": "price"}
        body = p.build_extra_body(provider_preferences=prefs)
        assert body.get("provider") == prefs

    def test_provider_preferences_empty(self):
        p = _get_profile()
        body = p.build_extra_body(provider_preferences={})
        assert "provider" not in body

    def test_web_search_plugin(self):
        p = _get_profile()
        body = p.build_extra_body(polza_web_search={"max_results": 5})
        assert "plugins" in body
        assert {"id": "web", "max_results": 5} in body["plugins"]

    def test_file_parser_plugin(self):
        p = _get_profile()
        body = p.build_extra_body(
            polza_file_parser={"pdf": {"engine": "mistral-ocr"}}
        )
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
        body = p.build_extra_body(
            polza_web_search={"max_results": 5, "engine": "native"}
        )
        assert {"id": "web", "max_results": 5, "engine": "native"} in body["plugins"]

    def test_file_parser_with_ocr(self):
        p = _get_profile()
        body = p.build_extra_body(
            polza_file_parser={"images": {"ocr": True}}
        )
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


class TestPolzaProfileCheckBalance:
    """check_balance() — API-less structure tests."""

    def test_has_check_balance_method(self):
        p = _get_profile()
        assert hasattr(p, "check_balance")

    def test_check_balance_returns_none_without_key(self):
        p = _get_profile()
        result = p.check_balance(api_key=None)
        assert result is None

    def test_check_balance_returns_none_with_empty_key(self):
        p = _get_profile()
        result = p.check_balance(api_key="")
        assert result is None
