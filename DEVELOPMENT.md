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

### Provider routing

Hermes already collects `provider_preferences` from `config.yaml` (fields:
`providers.only`, `providers.ignore`, `providers.order`, `providers.sort`)
and passes them as `provider_preferences` dict to `build_extra_body()`.

PolzaProfile forwards this directly as `provider: {only: [...], sort: "price"}`.

### Reasoning

Hermes `reasoning_config` dict maps directly to Polza's `reasoning` object.
No transformation needed.

### Web search

Polza uses a non-standard `plugins: [{id: "web", ...}]` field.
This is activated via `build_extra_body()` when context includes
`polza_web_search`.

## Testing

```bash
# Unit tests (no key required)
python -m pytest tests/test_polza_profile.py -n0 -q -v

# Live smoke test (requires POLZA_API_KEY in environment)
POLZA_API_KEY=pza_... python -m pytest tests/test_polza_live.py -n0 -q -v -x
```

## Roadmap

### Phase 1 — Core plugin ✅ (current)
- [x] ProviderProfile with all hooks
- [x] Public model catalog fetch
- [x] Provider routing (build_extra_body)
- [x] Reasoning passthrough (build_api_kwargs_extras)

### Phase 2 — Testing & polish
- [ ] Unit tests for all profile hooks
- [ ] Live smoke test
- [ ] GitHub CI integration

### Phase 3 — Extended features
- [ ] Balance check via `hermes doctor`
- [ ] Web search plugin support
- [ ] File parser plugin support
- [ ] Summary routing (chat_completion_helpers.py fix)

### Phase 4 — Upstream (future)
- [ ] PR to hermes-agent repo as bundled provider
