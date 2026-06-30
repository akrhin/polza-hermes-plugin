# Polza.ai Hermes Provider Plugin

[🇷🇺 Русский](README.md)

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

### With Provider Routing

Pass Polza's `provider` object via `extra_body` — works in CLI, Gateway,
and WebUI (read as a fallback by the plugin):

```yaml
model:
  provider: polza
  model: deepseek-v4-flash
  extra_body:
    provider:
      only:
        - DeepSeek
        - OpenAI
      sort: price
      allow_fallbacks: true
```

> **Note:** `model.extra_body` is consumed by the Polza plugin directly
> (not by Hermes core). This means it works in all entry points —
> CLI, Telegram, WebUI — with no platform-specific config keys.

Available `provider` fields:

| Field | Type | Description |
|-------|------|-------------|
| `only` | `string[]` | Whitelist — use only these providers |
| `ignore` | `string[]` | Blacklist — exclude these providers |
| `order` | `string[]` | Priority list |
| `sort` | `string` | Sort by `price`, `latency`, or `throughput` |
| `max_price` | `object` | Max price per 1M tokens: `{prompt, completion}` |
| `allow_fallbacks` | `boolean` | Fall back to other providers on error |

### Alias format (@-syntax)

When your client can't send extra_body (e.g. constrained SDKs), pass routing
parameters directly in the model string:

```
model:
  provider: polza
  model: "minimax/minimax-m2.5@provider=DeepInfra&reasoning_effort=high"
```

Supported aliases:

| Alias | Equivalent body field |
|-------|----------------------|
| `@provider=<name>` | `provider.only = [name]` |
| `@reasoning_effort=<level>` | `reasoning.effort = level` |
| `@allow_fallbacks=<bool>` | `provider.allow_fallbacks = bool` |

Multiple aliases can be combined with ``&``:
`model@provider=X&reasoning_effort=high&allow_fallbacks=false`

> **Note:** When alias is present, `model.extra_body.provider` is **skipped**
> to avoid `400` conflict on the Polza side.

### With Web Search

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: web
        max_results: 5
```

### With Response Healing

Automatically fixes invalid JSON in model responses:

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: response-healing
        enabled: true
```

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
