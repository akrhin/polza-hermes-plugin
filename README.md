# Polza.ai Hermes Provider Plugin

[🇷🇺 Русский](README_RU.md)

> **Unified API for 200+ AI models** with provider routing,
> reasoning tokens, and web search — now a first-class Hermes Agent provider.

---

## Features

- **OpenAI-compatible** — Chat Completions, Tools, Structured Output, Streaming
- **Provider routing** — choose upstream providers by priority, price, or latency
- **Reasoning tokens** — native support for o-series, DeepSeek R1, Claude Opus, Grok
- **Web search** — real-time internet access for any model
- **Public model catalog** — `GET /v1/models` requires no API key


## Installation

### 1. Clone plugin into Hermes

```bash
git clone https://github.com/akrhin/polza-hermes-plugin.git
mkdir -p ~/.hermes/plugins/model-providers
ln -sf "$(pwd)/polza-hermes-plugin/plugins/model-providers/polza" \
       ~/.hermes/plugins/model-providers/polza
```

Or copy `plugins/model-providers/polza/` directly into
`~/.hermes/plugins/model-providers/`.

### 2. Add API Key

**Option A — Environment variable** (recommended for a single key):

```bash
echo 'POLZA_API_KEY=pza_yo...ere' >> ~/.hermes/.env
```

**Option B — Credential pool** (multiple keys with rotation):

```bash
hermes auth add polza --type api-key --api-key pza_your_key_here
hermes auth add polza --type api-key --api-key pza_second_key
```

```yaml
credential_pool_strategies:
  polza: round_robin
```

### 3. Configure Hermes

```yaml
model:
  provider: polza
  model: deepseek-chat
```

## Configuration

### Basic

```yaml
model:
  provider: polza
  model: gpt-4o-mini
```

### With Provider Routing (recommended)

Pass Polza's `provider` object via `extra_body` — works in CLI, Gateway, and WebUI:

```yaml
model:
  provider: polza
  model: deepseek-v4-flash
  extra_body:
    provider:
      only:
        - DeepSeek
        - OpenAI
        - Anthropic
      sort: price
      allow_fallbacks: true
```

Available `provider` fields:

| Field | Type | Description |
|-------|------|-------------|
| `only` | `string[]` | Whitelist — use only these providers |
| `ignore` | `string[]` | Blacklist — exclude these providers |
| `order` | `string[]` | Priority list |
| `sort` | `string` | Sort by `price`, `latency`, or `throughput` |
| `max_price` | `object` | Max price per 1M tokens: `{prompt, completion}` |
| `allow_fallbacks` | `boolean` | Fall back to other providers on error |

### With Reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

### With Web Search

```yaml
model:
  extra_body:
    plugins:
      - id: web
        max_results: 5
```

Or via `config.yaml`:

```yaml
polza_web_search:
  max_results: 5
  engine: auto  # auto | native | exa
```

## WebUI

Polza.ai has a dedicated [Hermes WebUI](https://github.com/nesquena/hermes-webui) with:

- **Balance and cost widget** — floating balance display, daily spending breakdown by model, API key management in browser
- **Extension gallery** — install in Settings → Extensions

See [polza-webui-extensions](https://github.com/akrhin/polza-webui-extensions) for installation and usage.
