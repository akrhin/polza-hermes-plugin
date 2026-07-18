"""Unit tests for PolzaImageGen helpers — URL building, model chain, dedupe.

Pure unit tests — no Hermes imports, no API keys required.
"""

from __future__ import annotations

# ── Inline copies of helper functions ──────────────────────────────────

_POLZA_DEFAULT = "yandex/yandex-art"
_POLZA_FALLBACK = "seedream/5-pro-text-to-image"


def _build_images_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")] + "/api"
    return base + "/v2/images/generations"


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


# ── Tests ──────────────────────────────────────────────────────────────


class TestBuildImagesEndpoint:
    def test_standard_base_url(self):
        result = _build_images_endpoint("https://polza.ai/api/v1")
        assert result == "https://polza.ai/api/v2/images/generations"

    def test_base_url_without_v1(self):
        result = _build_images_endpoint("https://polza.ai/api")
        assert result == "https://polza.ai/api/v2/images/generations"

    def test_custom_base_url(self):
        result = _build_images_endpoint("https://custom.example.com/v1")
        assert result == "https://custom.example.com/v1/v2/images/generations"

    def test_trailing_slash(self):
        result = _build_images_endpoint("https://polza.ai/api/v1/")
        assert result == "https://polza.ai/api/v2/images/generations"

    def test_no_slash(self):
        result = _build_images_endpoint("https://polza.ai")
        assert result == "https://polza.ai/v2/images/generations"


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


class TestModelChainFallbacks:
    """Test the model chain fallback logic — no Hermes imports needed."""

    def test_default_chain_includes_both(self):
        models = _dedupe_models([_POLZA_DEFAULT, _POLZA_FALLBACK])
        assert _POLZA_DEFAULT in models
        assert _POLZA_FALLBACK in models
        assert len(models) == len(set(models))  # no duplicates

    def test_first_model_is_default(self):
        models = _dedupe_models([_POLZA_DEFAULT, _POLZA_FALLBACK])
        assert models[0] == _POLZA_DEFAULT

    def test_fallback_is_second(self):
        models = _dedupe_models([_POLZA_DEFAULT, _POLZA_FALLBACK])
        assert models[-1] == _POLZA_FALLBACK
