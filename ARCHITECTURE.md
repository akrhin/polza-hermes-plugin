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

plugins/polza-balance/
├── __init__.py       # /balance slash command
├── plugin.yaml       # Manifest

plugins/image_gen/polza/
├── __init__.py       # PolzaImageProvider — ImageGenProvider subclass
└── plugin.yaml       # Manifest

tests/
├── test_polza_profile.py   # Unit tests (no API key needed)
├── test_polza_live.py      # Smoke tests (requires POLZA_API_KEY)
├── test_polza_balance.py   # Balance formatting tests
└── test_polza_image_gen.py # Image gen model chain tests
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

### Alias format (@-syntax)

Polza supports passing `provider`, `reasoning_effort`, and `allow_fallbacks` directly
in the model string via ``@``-syntax:

```
<model>@provider=<name>&reasoning_effort=<level>&allow_fallbacks=<bool>
```

**Parsed by**: ``PolzaProfile._parse_model_alias()`` — a static method that
splits on ``@``, then ``&``, then ``=``, and returns a dict with recognised keys.

**Conflict avoidance**: When an alias is detected in ``build_extra_body()``,
both ``provider_preferences`` (layer 1) and config fallback (layer 2) are
**skipped** — otherwise Polza API returns ``400`` for duplicate ``provider``
or ``reasoning`` fields. Same logic applies in ``build_api_kwargs_extras()``:
``@reasoning_effort`` suppresses ``extra_body.reasoning``.

**Identity:** ``_ALIAS_KEYS`` — the recognised alias keys are:
``provider``, ``reasoning_effort``, ``allow_fallbacks``.

### Plugins system

Polza provides server-side plugins via the ``plugins`` array in the request body:

| Plugin ID          | Context key             | Config key                     | Description                                   |
|--------------------|------------------------|--------------------------------|-----------------------------------------------|
| ``web``            | ``polza_web_search``   | ``model.extra_body.plugins[]`` | Internet search augmentation                  |
| ``file-parser``    | ``polza_file_parser``  | ``model.extra_body.plugins[]`` | PDF/DOCX text extraction with engine selection |
| ``response-healing`` | ``polza_response_healing`` | ``model.extra_body.plugins[]`` | Automatic invalid JSON fix in responses    |

**Two-layer resolution:**

1. **Config baseline** — ``_plugins_from_config()`` reads ``model.extra_body.plugins``
   from ``config.yaml`` and returns known plugin entries.
2. **Context override** — if a context key (``polza_web_search``, etc.) is present,
   its value replaces the config entry for that plugin ID.

This means plugins can be enabled globally in ``config.yaml`` and overridden
per-request via agent context — identical pattern to the provider routing.

> **Note:** Plugins from config.yaml run on **every** API request. There is no
> per-message toggle — they are always active once configured.

## Design Decisions

### Plugin-only: no core edits

Hermes auto-discovers model-provider plugins from `~/.hermes/plugins/model-providers/`.
The plugin declares a `ProviderProfile` — no core files are modified.

### Image generation via Polza

`plugins/image_gen/polza/` добавляет бэкенд генерации изображений через Polza.ai. В отличие от штатных бэкендов (OpenRouter, xAI), Polza использует **OpenAI-совместимый `/v2/images/generations`**, а не `/chat/completions` с модальностями:

```
image_gen/polza/__init__.py              # PolzaImageProvider(ImageGenProvider)
  └── generate()                         # POST /v2/images/generations → download ephemeral URL
        └── resolve_runtime_provider("polza") → Polza credentials
```

**Почему не OpenRouterCompatImageProvider:** Polza не поддерживает протокол `/chat/completions` с `modalities: ["image"]`. Её image-модели работают только через стандартный images API. Наследование от `OpenRouterCompatImageProvider` давало `400 BAD_REQUEST` или пустые ответы. Переписан как самостоятельный `ImageGenProvider` с прямой отправкой на `/v2/images/generations`.

**Модели по умолчанию:** `yandex/yandex-art` (2.91 RUB/image), fallback: `seedream/5-pro-text-to-image`.

**Ограничение:** Text-to-image only. Image-to-image / editing не поддерживается.

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

#### Two-layer resolution

The `model.extra_body.provider` value is **not** read automatically by Hermes
core for built-in providers — it's consumed by the Polza plugin itself:

1. **Agent context** (`provider_preferences`, set via `agent.providers_allowed`
   from CLI flags or `/providers` command) — has priority.
2. **Config fallback** — `PolzaProfile._extra_body_provider_from_config()`
   reads `model.extra_body.provider` from `config.yaml` when no context-level
   preferences are set.

This two-layer design means:

| Entry point | Source of routing | How it reaches Polza API |
|-------------|-----------------|--------------------------|
| CLI (`--provider polza --providers-only DeepSeek`) | `agent.providers_allowed` → `provider_preferences` | Context (layer 1) |
| Telegram, WebUI, Discord | `model.extra_body.provider` from config.yaml | Config fallback (layer 2) |
| `/providers` runtime command | `agent.providers_allowed/ignored/order` | Context (layer 1, overrides config) |

The `build_extra_body()` hook in the profile also crosses `provider_preferences`
from `providers:` / `provider_routing:` into `extra_body.provider` — but the
direct `extra_body` approach is simpler and recommended for most setups.

#### Why not top-level config keys

The top-level `providers:` key works only in CLI mode; `provider_routing:` only
in Gateway/WebUI mode. `model.extra_body.provider` is a single source of truth
that hits both because the plugin reads it as a fallback.

### Reasoning

Hermes `reasoning_config` dict maps directly to Polza's `reasoning` object.
No transformation needed — `PolzaProfile` passes it through.

### Web search

Polza uses a non-standard `plugins: [{id: "web", ...}]` field.
This is activated via `build_extra_body()` when context includes
`polza_web_search`, or via `model.extra_body.plugins` in config.yaml.

### File parser and response healing

Same plugin mechanism — see the [Plugins system](#plugins-system) section above.
