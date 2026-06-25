# Polza.ai Hermes Provider Plugin

[![Русская версия](docs/assets/ru-flag.svg)](README_RU.md)

> **Unified API for 200+ AI models** with RUB billing, provider routing,
> reasoning tokens, and web search — now a first-class Hermes Agent provider.

---

## Features

- **OpenAI-compatible** — standard Chat Completions, Tools, Structured Output, Streaming
- **Provider routing** — choose upstream providers by priority, price, or latency
- **Reasoning tokens** — native support for o-series, DeepSeek R1, Claude Opus 4.7+, Grok
- **Web search** — real-time internet access for any model
- **Public model catalog** — `GET /v1/models` requires no API key (free!)
- **RUB billing** — prices in rubles, `cost_rub` in every response
- **Balance tracking** — `GET /v1/balance` for spending monitoring
- **Plugins** — file parser, response healing, and more

## Installation

```bash
# Clone into Hermes user plugins directory
git clone https://github.com/akrhin/polza-hermes-plugin.git
mkdir -p ~/.hermes/plugins/model-providers
ln -sf "$(pwd)/polza-hermes-plugin/plugins/model-providers/polza" \
       ~/.hermes/plugins/model-providers/polza
```

Or copy the `plugins/model-providers/polza/` directory directly into
`~/.hermes/plugins/model-providers/`.

### 2. Add API Key

**Option A — Environment variable** (recommended for single keys):

```bash
echo 'POLZA_API_KEY=pza_your_key_here' >> ~/.hermes/.env
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

### With Provider Routing

```yaml
model:
  provider: polza
  model: anthropic/claude-sonnet-4

providers:
  only: [OpenAI, Anthropic]
  sort: price
```

For details, see [Polza provider selection docs](https://polza.ai/docs/gaidy/provider-selection).

### With Reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

See [Polza reasoning docs](https://polza.ai/docs/osobennosti/reasoning-tokens).

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
