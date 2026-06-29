# Polza.ai Hermes Provider Plugin

[🇬🇧 English](README.md)

> **Унифицированный API для сотен AI-моделей** с выбором
> провайдера, reasoning-токенами и веб-поиском — как встроенный провайдер
> Hermes Agent.

---

## Возможности

- **OpenAI-совместимость** — Chat Completions, Tools, Structured Output, Streaming
- **Выбор провайдера** — приоритет, сортировка по цене, белый/чёрный список
- **Reasoning** — o-series, DeepSeek R1, Claude Opus, Grok
- **Веб-поиск** — доступ к реальному интернету для любой модели
- **Публичный каталог моделей** — `GET /v1/models` без API-ключа


## Установка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/akrhin/polza-hermes-plugin.git
mkdir -p ~/.hermes/plugins/model-providers
ln -sf "$(pwd)/polza-hermes-plugin/plugins/model-providers/polza" \
       ~/.hermes/plugins/model-providers/polza
```

Или скопируйте `plugins/model-providers/polza/` в
`~/.hermes/plugins/model-providers/`.

### 2. Добавьте API-ключ

**Вариант А — переменная окружения** (рекомендуется для одного ключа):

```bash
echo 'POLZA_API_KEY=pza_ключ' >> ~/.hermes/.env
```

**Вариант Б — Credential pool** (несколько ключей с ротацией):

```bash
hermes auth add polza --type api-key --api-key pza_ключ1
hermes auth add polza --type api-key --api-key pza_ключ2
```

```yaml
credential_pool_strategies:
  polza: round_robin
```

### 3. Настройте Hermes

```yaml
model:
  provider: polza
  model: deepseek/deepseek-chat
```

## Настройка

### Базовая

```yaml
model:
  provider: polza
  model: openai/gpt-4o-mini
```

### С выбором провайдера (рекомендуется)

Объект `provider` передаётся через `extra_body` — работает в CLI, Gateway и WebUI:

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

Поля объекта `provider`:

| Поле | Тип | Описание |
|------|-----|----------|
| `only` | `string[]` | Белый список — только эти провайдеры |
| `ignore` | `string[]` | Чёрный список — исключить провайдеры |
| `order` | `string[]` | Приоритетный порядок |
| `sort` | `string` | Сортировка: `price`, `latency`, `throughput` |
| `max_price` | `object` | Макс. цена за 1М токенов: `{prompt, completion}` |
| `allow_fallbacks` | `boolean` | Fallback на другие провайдеры при ошибке |

### С reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

### С веб-поиском

```yaml
model:
  extra_body:
    plugins:
      - id: web
        max_results: 5
```

Или через `config.yaml`:

```yaml
polza_web_search:
  max_results: 5
  engine: auto  # auto | native | exa
```

## WebUI

Для Polza.ai есть [Hermes WebUI](https://github.com/nesquena/hermes-webui) с расширением:

- **Виджет баланса и расходов** — плавающий баланс, дневная статистика по моделям, управление API-ключом в браузере
- **Галерея расширений** — установка через Settings → Extensions

Подробнее: [polza-webui-extensions](https://github.com/akrhin/polza-webui-extensions)
