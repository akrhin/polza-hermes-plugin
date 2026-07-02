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
      max_price:
        prompt: 10
        completion: 20
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
| `max_price` | `object` | Max price: `{prompt, completion, image, audio, request}` |
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

### Polza Plugins (server-side processing)

Polza provides server-side plugins that process **every** API request.
They are enabled globally via `model.extra_body.plugins`.

> ⚠️ **Important:** Plugins from `model.extra_body.plugins` run on **every**
> request — you can't toggle them for a single message. If you add `web`,
> every request will trigger a web search and consume tokens.
>
> Pricing: model tokens + plugin processing tokens only.
> To disable a plugin: remove it from config.yaml and restart the gateway.

| Plugin | ID | What it does | When useful |
|--------|----|-------------|-------------|
| Web search | `web` | Searches the web, adds results to model context | Models without built-in search (DeepSeek, Gemini) |
| Response healing | `response-healing` | Auto-fixes invalid JSON in responses | When using `response_format: {type: json_schema}` |
| File parser | `file-parser` | Extracts text from PDF/DOCX/TXT | When sending documents in chat |

#### Web search (web)

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: web
        max_results: 5
```

Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `max_results` | `number` | Results count (1–10) |
| `engine` | `string` | Search engine: `auto`, `native`, `exa` |

> For models with native search (OpenAI, Anthropic, xAI) — provider handles it.
> For others (DeepSeek, Gemini) — routed via Exa.

#### Response healing (response-healing)

Auto-fixes invalid JSON. Useful with `strict: true` schemas:

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: response-healing
        enabled: true
```

#### PDF parsing (file-parser)

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: file-parser
        pdf:
          engine: mistral-ocr  # pdf-text | mistral-ocr | native
```

`pdf.engine` options:

| Value | Description |
|-------|-------------|
| `pdf-text` | Text extraction (fast, no OCR) |
| `mistral-ocr` | OCR via Mistral for scanned docs |
| `native` | Provider's built-in processing |

#### Multiple plugins

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: web
        max_results: 3
      - id: response-healing
      - id: file-parser
        pdf:
          engine: mistral-ocr
```

> **Note:** Config-based plugins can be overridden via agent context
> (e.g. `polza_web_search={"max_results": 10}` overrides for that request).
> But you can't fully disable them from chat — only by editing config.yaml.

### With Reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

## WebUI

Polza.ai has a dedicated [Hermes WebUI](https://github.com/nesquena/hermes-webui) with:

- **Balance and cost widget** — floating balance display, daily spending breakdown by model, API key management in browser
- **Extension gallery** — install in Settings → Extensions

See [polza-webui-extensions](https://github.com/akrhin/polza-webui-extensions) for installation and usage.

---

## Updating the Plugin

### 1. Update plugin files

```bash
cd ~/git/polza-hermes-plugin
git pull origin main
```

If you copied instead of symlinked, recopy:

```bash
cp -r ~/git/polza-hermes-plugin/plugins/model-providers/polza ~/.hermes/plugins/model-providers/
```

### 2. Update hermes-agent (auxiliary task support)

Polza is a plugin-based provider. The main model works immediately, but **auxiliary tasks** (vision, history compression, title generation) require a version of `hermes-agent` that supports plugin-based providers via `ProviderProfile` fallback in `resolve_provider_client()`.

Check your version:

```bash
cd ~/git/hermes/hermes-agent
git log --oneline -1 | grep "plugin provider fallback"
```

If no match, update your fork:

```bash
git pull fork main
```

> **What the fix does:** `resolve_provider_client()` no longer fails on providers absent from the hardcoded `PROVIDER_REGISTRY`. When a provider isn't in the built-in dictionary, it falls back to `get_provider_profile()` from the plugin system. The Polza profile supplies `base_url`, `env_vars`, and `default_aux_model`, so the auxiliary client is created correctly.

### 3. Restart Hermes

CLI:

```bash
hermes exit && hermes
```

Gateway (systemd):

```bash
systemctl --user restart hermes-gateway
```

WebUI — reload page or restart the server.

After updating, all auxiliary tasks (auto-titling, history compression, vision) will use Polza instead of failing with `unknown provider`.

