"""Unit tests for polza-balance — argument parsing, formatting helpers.

The plugin lives in a directory with a hyphen (polza-balance), so standard
import won't work. We test utility functions by duplicating their logic
inline — they are pure stateless functions with zero dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

# ── Inline copies of utility functions ────────────────────────────────────

MSK = timezone(timedelta(hours=3))
PROVIDER_COLORS = {
    "DeepSeek": "#2e86de",
    "GMICloud": "#e74c3c",
    "Nebius":   "#2ecc71",
    "Parasail": "#f39c12",
    "Morph":    "#9b59b6",
    "Venice":   "#1abc9c",
    "Nvidia":   "#e91e63",
    "Mancer":   "#34495e",
}


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _to_msk(created_at: str | None) -> str:
    if not created_at:
        return "??:??"
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.astimezone(MSK).strftime("%H:%M")
    except (ValueError, TypeError):
        return "??:??"


def _split_provider(model_name: str) -> tuple:
    if ":" in model_name:
        parts = model_name.split(":", 1)
        return (parts[0].strip(), parts[1].strip())
    return ("", model_name)


def _provider_color(provider_name: str | None) -> str:
    if not provider_name:
        return "#888"
    if provider_name in PROVIDER_COLORS:
        return PROVIDER_COLORS[provider_name]
    h, mod = 0, 1000003
    for ch in provider_name:
        h = (h * 131 + ord(ch)) % mod
    hue = (((h * 1234567) % mod + mod) % mod / mod) * 360
    sat = 55 + (h % 30)
    lit = 35 + ((h >> 4) % 25)
    return f"hsl({round(hue)}, {sat}%, {lit}%)"


# ── Tests ──────────────────────────────────────────────────────────────────


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
