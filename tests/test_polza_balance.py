"""Unit tests for polza-balance — argument parsing, formatting helpers.

The plugin lives in a directory with a hyphen (polza-balance), so standard
import won't work.  We load it via importlib and import the pure utility
functions from production code.
"""

from __future__ import annotations

from tests.helpers import polza_balance

# ── Import pure functions from production code ─────────────────────────

_fmt_num = polza_balance._fmt_num
_to_msk = polza_balance._to_msk
_split_provider = polza_balance._split_provider
_provider_color = polza_balance._provider_color
PROVIDER_COLORS = polza_balance.PROVIDER_COLORS

# ── Tests ──────────────────────────────────────────────────────────────


class TestFmtNum:
    def test_zero(self):
        assert _fmt_num(0) == "0"

    def test_small(self):
        assert _fmt_num(42) == "42"

    def test_thousands(self):
        assert _fmt_num(1_234) == "1.2K"

    def test_millions(self):
        assert _fmt_num(1_234_567) == "1.2M"

    def test_exact_thousand(self):
        assert _fmt_num(1_000) == "1.0K"


class TestToMsk:
    def test_valid_iso(self):
        result = _to_msk("2026-07-18T10:00:00Z")
        assert result == "13:00"

    def test_empty(self):
        assert _to_msk("") == "??:??"

    def test_invalid(self):
        assert _to_msk("not-a-date") == "??:??"

    def test_none(self):
        assert _to_msk(None) == "??:??"


class TestSplitProvider:
    def test_with_provider(self):
        prov, model = _split_provider("DeepSeek: deepseek-chat")
        assert prov == "DeepSeek"
        assert model == "deepseek-chat"

    def test_without_provider(self):
        prov, model = _split_provider("gpt-4o-mini")
        assert prov == ""
        assert model == "gpt-4o-mini"

    def test_multi_colon(self):
        prov, model = _split_provider("OpenAI: gpt-4o:extended")
        assert prov == "OpenAI"
        assert model == "gpt-4o:extended"

    def test_empty(self):
        prov, model = _split_provider("")
        assert prov == ""
        assert model == ""


class TestProviderColor:
    def test_known_provider(self):
        c = _provider_color("DeepSeek")
        assert c == PROVIDER_COLORS["DeepSeek"]

    def test_unknown_provider_returns_hsl(self):
        c = _provider_color("SomeUnknownProvider")
        assert c.startswith("hsl(")

    def test_empty(self):
        c = _provider_color("")
        assert c == "#888"

    def test_none(self):
        c = _provider_color(None)
        assert c == "#888"

    def test_all_known(self):
        for name in PROVIDER_COLORS:
            c = _provider_color(name)
            assert c == PROVIDER_COLORS[name], f"color mismatch for {name}"
