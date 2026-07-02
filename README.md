# Polza.ai Hermes Provider Plugin

[🇬🇧 English](README_EN.md)

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

### С выбором провайдера

Объект `provider` передаётся через `extra_body` — работает в CLI, Gateway
и WebUI (читается плагином как fallback):

```yaml
model:
  provider: polza
  model: deepseek/deepseek-v4-flash
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

> **Примечание:** `model.extra_body` читается плагином Polza напрямую
> (не ядром Hermes). Поэтому работает во всех точках входа —
> CLI, Telegram, WebUI — без платформо-специфичных ключей в конфиге.

Поля объекта `provider`:

| Поле | Тип | Описание |
|------|-----|----------|
| `only` | `string[]` | Белый список — только эти провайдеры |
| `ignore` | `string[]` | Чёрный список — исключить провайдеры |
| `order` | `string[]` | Приоритетный порядок |
| `sort` | `string` | Сортировка: `price`, `latency`, `throughput` |
| `max_price` | `object` | Макс. цена: `{prompt, completion, image, audio, request}` |
| `allow_fallbacks` | `boolean` | Fallback на другие провайдеры при ошибке |

### Alias-формат (@-синтаксис)

Когда ваш клиент не умеет отправлять `extra_body`, параметры можно передать
прямо в строке модели:

```yaml
model:
  provider: polza
  model: "minimax/minimax-m2.5@provider=DeepInfra&reasoning_effort=high"
```

Поддерживаемые алиасы:

| Алиас | Эквивалент в body |
|-------|-------------------|
| `@provider=<name>` | `provider.only = [name]` |
| `@reasoning_effort=<level>` | `reasoning.effort = level` |
| `@allow_fallbacks=<bool>` | `provider.allow_fallbacks = bool` |

Несколько алиасов через `&`:
`model@provider=X&reasoning_effort=high&allow_fallbacks=false`

> **Важно:** При наличии alias-формата `model.extra_body.provider`
> **не передаётся** — чтобы избежать `400` на стороне Polza.

### Плагины Polza (серверная обработка)

Polza предоставляет серверные плагины, которые обрабатывают **каждый** запрос
к API. Они подключаются глобально через `model.extra_body.plugins`.

> ⚠️ **Важно:** Плагины из `model.extra_body.plugins` работают на **каждый**
> запрос к модели — их нельзя включить/выключить для одного конкретного
> сообщения в чате. Если указать `web` — поиск будет выполняться при каждом
> обращении, и за каждый поиск списываются токены.
>
> Стоимость: только токены модели + токены на обработку плагина.
> Отключить плагин для конкретного запроса нельзя — только убрать из конфига
> и перезапустить gateway.

| Плагин | ID | Что делает | Когда полезен |
|--------|----|-----------|---------------|
| Веб-поиск | `web` | Ищет в интернете, добавляет результаты в контекст модели | Моделям без встроенного поиска (DeepSeek, Gemini) |
| Исправление JSON | `response-healing` | Автоматически чинит невалидный JSON в ответах | При `response_format: {type: json_schema}` |
| Парсинг файлов | `file-parser` | Извлекает текст из PDF/DOCX/TXT | При отправке документов в чат |

#### Веб-поиск (web)

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: web
        max_results: 5
```

Параметры:

| Параметр | Тип | Описание |
|----------|-----|----------|
| `max_results` | `number` | Количество результатов (1–10) |
| `engine` | `string` | Движок: `auto`, `native`, `exa` |

> Для моделей с нативным поиском (OpenAI, Anthropic, xAI) — поиск у провайдера.
> Для остальных (DeepSeek, Gemini) — через Exa. Цена — токены модели + Exa.

#### Исправление JSON (response-healing)

Автоматически чинит невалидный JSON. Полезно при `strict: true`:

```yaml
model:
  provider: polza
  model: openai/gpt-4o
  extra_body:
    plugins:
      - id: response-healing
        enabled: true
```

#### Парсинг PDF (file-parser)

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

Параметры `pdf.engine`:

| Значение | Описание |
|----------|----------|
| `pdf-text` | Извлечение текста (быстро, без OCR) |
| `mistral-ocr` | OCR через Mistral для сканов |
| `native` | Встроенная обработка провайдера |

#### Несколько плагинов одновременно

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

> **Примечание:** Плагины из config.yaml можно переопределить через
> контекст агента — например, `polza_web_search={"max_results": 10}`
> перезапишет конфиг для текущего запроса. Но выключить полностью
> из чата нельзя — только правкой конфига.

### С reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

## WebUI

Для Polza.ai есть [Hermes WebUI](https://github.com/nesquena/hermes-webui) с расширением:

- **Виджет баланса и расходов** — плавающий баланс, дневная статистика по моделям, управление API-ключом в браузере
- **Галерея расширений** — установка через Settings → Extensions

Подробнее: [polza-webui-extensions](https://github.com/akrhin/polza-webui-extensions)

---

## Обновление плагина

```bash
cd ~/git/polza-hermes-plugin
git pull origin main
```

Если плагин скопирован (не симлинк) — перекопируйте:

```bash
cp -r plugins/model-providers/polza ~/.hermes/plugins/model-providers/
```

После обновления — перезапустите Hermes.

> Плагин регистрируется в `PROVIDER_REGISTRY` автоматически через `register_provider()`. Никаких правок ядра не требуется. Все auxiliary-задачи (vision, сжатие, заголовки) работают сразу после установки плагина.

