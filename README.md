# Polza.ai Hermes Provider Plugin

[🇷🇺 Русский](README_RU.md)

> **Unified API for 200+ AI models** with RUB billing, provider routing,
> reasoning tokens, and web search — now a first-class Hermes Agent provider.

---

## Features

- **OpenAI-compatible** — standard Chat Completions, Tools, Structured Output, Streaming
- **Provider routing** — choose upstream providers by priority, price, or latency
- **Reasoning tokens** — native support for o-series, DeepSeek R1, Claude Opus 4.7+, Grok
- **Web search** — real-time internet access for any model
- **Public model catalog** — `GET /v1/models` requires no API key
- **RUB billing** — prices in rubles, `cost_rub` in every response
- **Balance tracking** — `GET /v1/balance` for spending monitoring
- **Plugins** — file parser, response healing, and more

## Installation

### 1. Clone plugin into Hermes

```bash
git clone https://github.com/akrhin/polza-hermes-plugin.git
mkdir -p ~/.hermes/plugins/model-providers
ln -sf "$(pwd)/polza-hermes-plugin/plugins/model-providers/polza" \
       ~/.hermes/plugins/model-providers/polza
```

Or copy the `plugins/model-providers/polza/` directory directly into
`~/.hermes/plugins/model-providers/`.

### 2. Add API Key

**Option A ��� Environment variable** (recommended for a single key):

```bash
echo 'POLZA_API_KEY=pza_yo...ere' >> ~/.hermes/.env
```

**Option B — Credential pool** (multiple keys with rotation):

```bash
hermes auth add polza --type api-key --api-key pza_your_key_here
hermes auth add polza --type api-key --api-key pza_second_key
```

With rotation strategy in `config.yaml`:

```yaml
credential_pool_strategies:
  polza: round_robin  # or fill_first, least_used
```

### 3. Configure Hermes

Set `polza` as your provider in `config.yaml`:

```yaml
model:
  provider: polza
  model: deepseek/deepseek-chat
```

## Configuration

### Basic

```yaml
model:
  provider: polza
  model: openai/gpt-4o-mini
```

### With Provider Routing (recommended)

Pass Polza's `provider` object directly via `extra_body`. This works in all
modes (CLI, Gateway, WebUI) and mirrors the Polza API format:

```yaml
model:
  provider: polza
  model: deepseek/deepseek-v4-flash
  extra_body:
    provider:
      only:
        - DeepSeek
        - OpenAI
        - Anthropic
      sort: price
      allow_fallbacks: true
```

Available `provider` fields (see [Polza docs](https://polza.ai/docs/gaidy/provider-selection)):

| Field | Type | Description |
|-------|------|-------------|
| `only` | `string[]` | Whitelist — use only these providers |
| `ignore` | `string[]` | Blacklist — exclude these providers |
| `order` | `string[]` | Priority list |
| `sort` | `string` | Sort by `price`, `latency`, or `throughput` |
| `max_price` | `object` | Max price per 1M tokens: `{prompt, completion}` |
| `allow_fallbacks` | `boolean` | Fall back to other providers on error |

**Why `extra_body` over top-level `providers:`?** The extra_body approach is
provider-specific, unambiguous, and survives the CLI↔Gateway config split.
Top-level `providers:` works only in CLI mode; `provider_routing:` works only
in Gateway/WebUI mode. `extra_body` works in both.

### With Reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

See [Polza reasoning docs](https://polza.ai/docs/osobennosti/reasoning-tokens).

### With Web Search

Polza supports web search via the `plugins` field. Add it to `extra_body`:

```yaml
model:
  extra_body:
    plugins:
      - id: web
        max_results: 5
```

## Verification

After installation, check that Hermes recognises the provider:

```bash
hermes model  # Should show "polza" in the provider list
hermes doctor # Should include Polza health check
```

## How it works

This plugin declares a `ProviderProfile` that Hermes discovers automatically.
Every integration point — auth, model catalog, CLI picker, health checks,
auxiliary tasks — reads from the profile. No core files are modified.

See [`DEVELOPMENT.md`](DEVELOPMENT.md) for implementation details.
