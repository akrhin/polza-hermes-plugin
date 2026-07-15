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
```

### 2. Model Provider (основной LLM-провайдер)

Подключает Polza.ai как first-class провайдер для всех чат-запросов.

```bash
mkdir -p ~/.hermes/plugins/model-providers
ln -sf "$(pwd)/polza-hermes-plugin/plugins/model-providers/polza" \
       ~/.hermes/plugins/model-providers/polza
```

Или скопируйте `plugins/model-providers/polza/` в `~/.hermes/plugins/model-providers/`.

### 3. Добавьте API-ключ

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

### 4. Настройте Hermes

```yaml
model:
  provider: polza
  model: deepseek/deepseek-v4-flash
```

---

### 5. Balance Plugin — `/balance` в Telegram (опционально)

Плагин для проверки баланса и трат прямо из Telegram:

```bash
ln -sf ~/git/polza-hermes-plugin/plugins/polza-balance ~/.hermes/plugins/polza-balance
```

```yaml
plugins:
  enabled:
    - polza-balance
```

**Команды:**

| Команда | Что показывает |
|---------|----------------|
| `/balance` | Баланс + всего потрачено |
| `/balance today` | + статистика за сегодня (gen, токены, кэш, top-5 моделей) |
| `/balance 10` | + последние 10 запросов |
| `/balance 20` | + последние 20 запросов |
| `/balance today 10` | Всё сразу |

Пример вывода:
```
📊 Polza AI — 03.07.2026 02:26 MSK
💰 Баланс: 429.39 ₽ | Потрачено всего: 7823.21 ₽

📅 Сегодня: 545 gen · 83.2M in / 519.1K out · 🗄96% cached · 🧠368.7K thinking · 💰 83.06 ₽
  Топ-5 моделей:
    DeepSeek: DeepSeek V4 Flash: 83.06 ₽ (83.2M/519.1K, 545 gen)

🕐 Последние 10 запросов
  00:00 | DeepSeek V4 Flash | 130.8K/2.4K | 0.11₽ 🗄99% 🧠2.2K | ⏱25.1s
```

---

### 6. Image Gen Plugin — генерация изображений (опционально)

Плагин для генерации изображений через Polza.ai. Использует OpenAI-совместимый эндпоинт `/v2/images/generations`.

```bash
ln -sf ~/git/polza-hermes-plugin/plugins/image_gen ~/.hermes/plugins/image_gen
```

**Конфигурация:**

```yaml
image_gen:
  provider: polza
  polza:
    model: yandex/yandex-art

plugins:
  enabled:
    - image_gen/polza
```

**Включение тулы `image_generate` на платформе:**

Чтобы модель могла вызвать `image_generate`, эта тула должна быть в инструментарии платформы (CLI / Telegram / Discord и т.д.). Самый надёжный способ — прописать `image_gen` (готовый toolset) в `platform_toolsets`:

```yaml
platform_toolsets:
  cli:
    - image_gen           # для CLI
  telegram:
    - image_gen           # для Telegram
  # и для других платформ по необходимости
```

| Сценарий | Что писать |
|----------|-----------|
| Стандартный CLI | `platform_toolsets: { cli: [..., image_gen] }` |
| Telegram без `hermes tools` | `telegram: [..., image_gen]` |
| Через `hermes tools` UI | `hermes tools` → Image Generation → включить |

> **Важно:** Если `image_gen` нет в `platform_toolsets` для твоей платформы, модель не будет знать о существовании этой тулы и не сможет генерировать изображения — даже если плагин установлен.

**Модели по умолчанию:** `yandex/yandex-art` (2.91 ₽/image). Fallback: `seedream/5-pro-text-to-image`.

**Ограничение:** Text-to-image only. Image-to-image / editing не поддерживается.

**Обновление с v1.0.0 на v1.0.1:**

Если плагин был установлен раньше (старый OpenRouter-совместимый вариант):

```bash
cd ~/git/polza-hermes-plugin
git pull origin main
```

Убедиться, что в конфиге указана рабочая модель (старые `tongyi-mai/z-image` и `google/gemini-2.5-flash-image` несовместимы с новым API):

```yaml
image_gen:
  provider: polza
  polza:
    model: yandex/yandex-art
```

Перезагрузить gateway (из отдельного терминала):
```bash
systemctl --user restart hermes-gateway
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

