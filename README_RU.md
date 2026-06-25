# Polza.ai Hermes Provider Plugin

[![English version](docs/assets/en-flag.svg)](README.md)

> **Унифицированный API д��я сотен AI-моделей** с оплатой в рублях, выбором
> провайдера, reasoning-токенами и веб-поиском — как встроенный провайдер
> Hermes Agent.

---

## Возможности

- **OpenAI-совместимость** — Chat Completions, Tools, Structured Output, Streaming
- **Выбор провайдера** — приоритет, сортировка по цене, белый/чёрный список
- **Reasoning** — o-series, DeepSeek R1, Claude Opus 4.7+, Grok
- **Веб-поиск** — доступ к реальному интернету для любой модели
- **Публичный каталог моделей** — `GET /v1/models` без API-ключа (бесплатно!)
- **Оплата в рублях** — `cost_rub` в каждом ответе
- **Баланс** — `GET /v1/balance` для контроля расходов
- **Плагины** — file parser, response healing и другие

## Установка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/akrhin/polza-hermes-plugin.git
mkdir -p ~/.hermes/plugins/model-providers
ln -sf "$(pwd)/polza-hermes-plugin/plugins/model-providers/polza" \
       ~/.hermes/plugins/model-providers/polza
```

Или скопируйте директорию `plugins/model-providers/polza/` в
`~/.hermes/plugins/model-providers/`.

### 2. Добавьте API-ключ

**Вариант А — переменная окружения** (рекомендуется для одного ключа):

```bash
echo 'POLZA_API_KEY=pza_ваш_ключ' >> ~/.hermes/.env
```

**Вариант Б — Credential pool** (несколько ключей с ротацией):

```bash
hermes auth add polza --type api-key --api-key pza_ключ1
hermes auth add polza --type api-key --api-key pza_ключ2
```

Стратегия ротации в `config.yaml`:

```yaml
credential_pool_strategies:
  polza: round_robin  # или fill_first, least_used
```

### 3. Настройте Hermes

Укажите `polza` как провайдер в `config.yaml`:

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

### С выбором провайдера

```yaml
model:
  provider: polza
  model: anthropic/claude-sonnet-4

providers:
  only: [OpenAI, Anthropic]
  sort: price
```

Подробнее: [документация Polza по выбору провайдера](https://polza.ai/docs/gaidy/provider-selection).

### С reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

Подробнее: [документация Polza по reasoning](https://polza.ai/docs/osobennosti/reasoning-tokens).

## Проверка

После установки убедитесь, что Hermes видит провайдера:

```bash
hermes model  # Должен показать "polza" в списке
hermes doctor # Должен включить проверку Polza
```

## Как это работает

Плагин объявляет `ProviderProfile`, который Hermes обнаруживает автоматически.
Все точки интеграции — аутентификация, каталог моделей, CLI-пикер, проверки
здоровья, вспомогательные задачи — читают данные из профиля. Ни один core-файл
не из��еняется.

Подробности реализации — в [`DEVELOPMENT.md`](DEVELOPMENT.md).
