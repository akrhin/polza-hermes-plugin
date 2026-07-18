"""Unit tests for PolzaImageProvider — model chain, URL building, helpers.

Run from inside Hermes venv:
    cd <hermes-agent> && python -m pytest <polza-plugin>/tests/test_polza_image_gen.py -n0 -q -v
"""

from __future__ import annotations

from unittest.mock import patch

from plugins.image_gen.polza import (
    _POLZA_DEFAULT,
    _POLZA_FALLBACK,
    _build_images_endpoint,
    _dedupe_models,
)


class TestBuildImagesEndpoint:
    def test_standard_base_url(self):
        """https://polza.ai/api/v1 → https://polza.ai/api/v2/images/generations"""
        result = _build_images_endpoint("https://polza.ai/api/v1")
        assert result == "https://polza.ai/api/v2/images/generations"

    def test_base_url_without_v1(self):
        """https://polza.ai/api → https://polza.ai/api/v2/images/generations"""
        result = _build_images_endpoint("https://polza.ai/api")
        assert result == "https://polza.ai/api/v2/images/generations"

    def test_custom_base_url(self):
        result = _build_images_endpoint("https://custom.example.com/v1")
        assert result == "https://custom.example.com/v1/v2/images/generations"

    def test_trailing_slash(self):
        result = _build_images_endpoint("https://polza.ai/api/v1/")
        assert result == "https://polza.ai/api/v2/images/generations"


class TestDedupeModels:
    def test_empty(self):
        assert _dedupe_models([]) == []

    def test_no_dupes(self):
        assert _dedupe_models(["a", "b", "c"]) == ["a", "b", "c"]

    def test_with_dupes(self):
        assert _dedupe_models(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_with_none_and_empty(self):
        assert _dedupe_models(["a", "", None, "b", ""]) == ["a", "b"]

    def test_whitespace_stripped(self):
        assert _dedupe_models([" a ", "  a  "]) == ["a"]


class TestResolveModelChain:
    """Test the model chain resolution via the actual provider class."""

    def test_explicit_overrides_everything(self):
        from plugins.image_gen.polza import PolzaImageProvider

        prov = PolzaImageProvider(
            provider_name="test",
            display_name="Test",
            runtime_name="polza",
            config_key="polza",
            model_env_var="POLZA_IMAGE_MODEL",
            setup_schema={},
        )
        chain = prov._resolve_model_chain(explicit="custom/model")
        assert chain == ["custom/model"]

    @patch.dict("os.environ", {"POLZA_IMAGE_MODEL": "env/override"})
    def test_env_var_overrides_defaults(self):
        from plugins.image_gen.polza import PolzaImageProvider

        prov = PolzaImageProvider(
            provider_name="test",
            display_name="Test",
            runtime_name="polza",
            config_key="polza",
            model_env_var="POLZA_IMAGE_MODEL",
            setup_schema={},
        )
        chain = prov._resolve_model_chain()
        assert chain == ["env/override"]

    def test_default_chain(self):
        """Without env or config, falls back to default chain."""
        from plugins.image_gen.polza import PolzaImageProvider

        prov = PolzaImageProvider(
            provider_name="test",
            display_name="Test",
            runtime_name="polza",
            config_key="polza",
            model_env_var="POLZA_IMAGE_MODEL",
            setup_schema={},
        )
        chain = prov._resolve_model_chain()
        assert _POLZA_DEFAULT in chain
        assert _POLZA_FALLBACK in chain
        # Default chain is deduped — no duplicates
        assert len(chain) == len(set(chain))
