# Development Plan — Polza.ai Hermes Provider Plugin

## Architecture Overview

```
plugins/model-providers/polza/
├── __init__.py       # PolzaProfile — ProviderProfile subclass
├── plugin.yaml       # Manifest (name, kind, version)

tests/
├── test_polza_profile.py   # Unit tests (no API key needed)
└── test_polza_live.py      # Smoke tests (requires POLZA_API_KEY)
```

## Design Decisions

### Plugin-only: no core edits

Hermes auto-discovers model-provider plugins from `~/.hermes/plugins/model-providers/`.
The following layers auto-wire from the profile:

| Layer | File | Auto-wired? |
|-------|------|:-----------:|
| Auth (PROVIDER_REGISTRY) | `auth.py:440` | ✅ |
| Model picker (CANONICAL_PROVIDERS) | `models.py:1040` | ✅ |
| CLI --provider choices | `models.py` → `CANONICAL_PROVIDERS` | ✅ |
| Live model fetch | `models.py:2388` (profile-based) | ✅ |
| Hostname → provider mapping | `model_metadata.py:451` | ✅ |
| Auxiliary model | `auxiliary_client.py:318` (reads `default_aux_model`) | ✅ |
| Doctor health checks | `doctor.py` (reads PROVIDER_REGISTRY) | ✅ |
| Transport kwargs | `chat_completions.py:527` (calls profile hooks) | ✅ |

### Provider routing: recommended approach

**Use `model.extra_body.provider` in `config.yaml`** — it works in CLI, Gateway,
and WebUI modes identically:

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
No transformation needed — PolzaProfile passes it through.

### Web search

Polza uses a non-standard `plugins: [{id: "web", ...}]` field.
This is activated via `build_extra_body()` when context includes
`polza_web_search`, or directly via `model.extra_body.plugins`.

## Testing

```bash
# Unit tests (no key required)
python -m pytest tests/test_polza_profile.py -q -v

# Live smoke test (requires POLZA_API_KEY in environment)
POLZA_API_KEY=*** python -m pytest tests/test_polza_live.py -q -v -x
```

## Roadmap

### Phase 1 — Core plugin ✅ (done)
- [x] ProviderProfile with all hooks
- [x] Public model catalog fetch (no API key needed)
- [x] Provider routing (build_extra_body)
- [x] Reasoning passthrough (build_api_kwargs_extras)
- [x] Session ID correlation (build_extra_body → Polza `session_id`)
- [x] Unit tests: 30 tests covering identity, hooks, context combinations
- [x] Live smoke test: chat, streaming, tools, provider routing, reasoning

### Phase 2 — Extended features ✅
- [x] Session ID passthrough (session_id → Polza)
- [x] Balance check method (PolzaProfile.check_balance())
- [x] Web search plugin support (polza_web_search context)
- [x] File parser plugin support (polza_file_parser context)

### Phase 3 — Polish & upstream ✅
- [x] Balance display via `scripts/polza-doctor.py`
- [x] Summary routing fix — `_has_aggregator_profile()` in `chat_completion_helpers.py`
- [x] GitHub CI — `.github/workflows/test.yml`
- [ ] PR to hermes-agent repo as bundled provider (deferred)
