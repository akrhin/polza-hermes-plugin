# Architecture

## How it works

This plugin declares a `ProviderProfile` that Hermes discovers automatically.
Every integration point — auth, model catalog, CLI picker, health checks,
auxiliary tasks — reads from the profile. No core files are modified.

## Structure

```
plugins/model-providers/polza/
├── __init__.py       # PolzaProfile — ProviderProfile subclass
├── plugin.yaml       # Manifest (name, kind, version)

tests/
├── test_polza_profile.py   # Unit tests (no API key needed)
└── test_polza_live.py      # Smoke tests (requires POLZA_API_KEY)
```

## Auto-wired layers

| Layer | Auto-wired? |
|-------|:-----------:|
| Auth (`PROVIDER_REGISTRY`) | ✅ |
| Model picker (`CANONICAL_PROVIDERS`) | ✅ |
| CLI `--provider` choices | ✅ |
| Live model fetch | ✅ |
| Hostname → provider mapping | ✅ |
| Auxiliary model selection | ✅ |
| Doctor health checks | ✅ |
| Transport kwargs | ✅ |

## Design Decisions

### Plugin-only: no core edits

Hermes auto-discovers model-provider plugins from `~/.hermes/plugins/model-providers/`.
The plugin declares a `ProviderProfile` — no core files are modified.

### Provider routing

**Use `model.extra_body.provider` in `config.yaml`** — works identically in CLI,
Gateway, and WebUI:

```yaml
model:
  provider: polza
  model: deepseek/deepseek-v4-flash
  extra_body:
    provider:
      only: [DeepSeek, OpenAI]
      sort: price
      allow_fallbacks: true
```

This is provider-specific and unambiguous. The top-level `providers:` key works
only in CLI mode; `provider_routing:` only in Gateway/WebUI mode. `extra_body`
works in both.

The `build_extra_body()` hook in the profile also crosses `provider_preferences`
from `providers:` / `provider_routing:` into `extra_body.provider` — but the
direct `extra_body` approach is simpler and recommended.

### Reasoning

Hermes `reasoning_config` dict maps directly to Polza's `reasoning` object.
No transformation needed — `PolzaProfile` passes it through.

### Web search

Polza uses a non-standard `plugins: [{id: "web", ...}]` field.
This is activated via `build_extra_body()` when context includes
`polza_web_search`, or directly via `model.extra_body.plugins`.
