# AGENTS.md — шпаргалка для AI-ассистентов

## Репозиторий: polza-hermes-plugin
## Деплой

Все три плагина прилинкованы симлинками:

```bash
ln -sf ~/git/polza-hermes-plugin/plugins/model-providers/polza ~/.hermes/plugins/model-providers/polza
ln -sf ~/git/polza-hermes-plugin/plugins/polza-balance ~/.hermes/plugins/polza-balance
ln -sf ~/git/polza-hermes-plugin/plugins/image_gen ~/.hermes/plugins/image_gen
```

В `~/.hermes/config.yaml`:
```yaml
plugins:
  enabled:
    - polza-provider
    - polza-balance
    - image_gen/polza
```

**Polza Provider** — основной LLM-провайдер для Hermes. Именно через него идут все запросы к DeepSeek V4 Flash и другим моделям.

**Polza Balance** — команда `/balance` в Telegram (с правами администратора чата).

## Связанные проекты

- **polza-webui-extensions** — [akrhin/polza-webui-extensions](https://github.com/akrhin/polza-webui-extensions) — UI-расширения для Hermes WebUI
- **polza-hermes-plugin** (этот репозиторий) — провайдер + баланс

## Три Hermes-плагина в одном репозитории:

| Плагин | Путь | Что делает |
|--------|------|------------|
| **Polza Provider** | `plugins/model-providers/polza/` | Провайдер LLM — добавляет Polza.ai как first-class provider |
| **Polza Image Gen** | `plugins/image_gen/polza/` | Генерация изображений через Polza.ai (OpenAI-compatible chat-completions) |
| **Polza Balance** | `plugins/polza-balance/` | Команда `/balance` в Telegram — баланс + траты |

---

## Polza Provider (`plugins/model-providers/polza/`)

Hermes model provider plugin. Добавляет Polza.ai как провайдера с 376+ моделями.

### Ключевые файлы

- `__init__.py` — `PolzaProfile(ProviderProfile)` — все хуки интеграции
- `plugin.yaml` — манифест
- `tests/test_polza_profile.py` — 23 unit-теста (без ключа)
- `tests/test_polza_live.py` — live-тесты (требуют POLZA_API_KEY)

### Что делает

| Интеграция | Как |
|------------|-----|
| PROVIDER_REGISTRY | Auth, credential pool, doctor |
| CANONICAL_PROVIDERS | CLI `/model` picker, `--provider polza` |
| URL-детекция | `polza.ai` → автоматический выбор провайдера |
| Алиасы | `polza-ai`, `pza` |
| Модели | 376 через публичный `/v1/models` |
| Provider selection | Параметр `provider` в `extra_body` — выбор роутинга |
| Reasoning | DeepSeek R1, o-series, Claude Opus через `extra_body` |
| Веб-поиск | `extra_body.plugins` |

### API для плагина

```python
# via hermes_cli provider system — не через register_tool
profile = get_provider_profile("polza")
profile.fetch_models(api_key=...)  # → 376 models
profile.build_extra_body(provider_preferences={"sort": "price"})
profile.build_api_kwargs_extras(reasoning_config={"effort": "high"})
```

---

## Polza Balance (`plugins/polza-balance/`)

Hermes plugin, регистрирующий слэш-команду `/balance` через `ctx.register_command()`.

### Как работает

```
register(ctx) → ctx.register_command("balance", handler=_handle_balance)
  ↓
User: /balance today 10
  ↓
_handle_balance("today 10") → парсит аргументы
  ↓
GET /v1/balance          → { amount, spentAmount }
GET /v1/history/generations → { items, meta }
  ↓
Возвращает HTML-строку → Telegram
```

### Команды

| Ввод | Что выводит |
|------|-------------|
| `/balance` | Баланс |
| `/balance today` | + сегодняшняя статистика |
| `/balance 10` | + последние 10 запросов |
| `/balance 20` | + последние 20 запросов |
| `/balance today 10` | Всё сразу |

### Ключевые моменты для разработки

- **Строковый парсинг**: `amount`, `cost` приходят строками — `float()` обязателен
- **Время**: `createdAt` от API в UTC, конвертится в MSK (`UTC+3`)
- **dateFrom**: считается от 00:00 MSK сегодня, переводится в UTC для API
- **ctx.register_command()** принимает `(name, handler, description, args_hint)`. Хендлер получает `raw_args: str`
- **dispatch_tool()** — если хендлеру нужно вызвать тулзу (не нужно для баланса, но паттерн)
- **requires_env** в `plugin.yaml` — проверяет `POLZA_API_KEY` при старте, без него плагин отключится сам
- **provides_tools: []** — команды НЕ тулы, это отдельный механизм

### Структура

```
plugins/polza-balance/
├── __init__.py        # register() + _handle_balance()
├── plugin.yaml        # Манифест (requires_env: POLZA_API_KEY)
├── AGENTS.md          # Эта шпаргалка (дубль корневого для быстрого доступа)
└── ARCHITECTURE.md    # Архитектура
```

---

## Установка любого плагина

```bash
ln -sf ~/git/polza-hermes-plugin/plugins/model-providers/polza ~/.hermes/plugins/model-providers/polza
ln -sf ~/git/polza-hermes-plugin/plugins/polza-balance ~/.hermes/plugins/polza-balance
```

Добавить в `config.yaml`:
```yaml
plugins:
  enabled:
    - polza-provider
    - polza-balance
```

Перезагрузить gateway:
```bash
# из отдельного терминала:
systemctl --user restart hermes-gateway
```

---

## Polza Image Gen (`plugins/image_gen/polza/`)

Плагин генерации изображений через Polza.ai. Регистрируется как `ImageGenProvider` через `ctx.register_image_gen_provider()`.

### Как работает

Использует прямые вызовы к OpenAI-совместимому `/v2/images/generations` (стандартный эндпоинт Polza для image-моделей).
Credentials резолвятся через `resolve_runtime_provider("polza")` — тот же механизм, что и для model-provider. Результат (эфимерная URL на S3) скачивается локально в `~/.hermes/cache/images/`.

**⚠️ Text-to-image only** — Polza models не поддерживают image-to-image / editing.

### Модели

По умолчанию (дешёвые, проверенные):
1. `yandex/yandex-art` — **2.91 ₽**/image (дефолт, проверен)
2. `seedream/5-pro-text-to-image` — fallback

Другие доступные варианты:
- `qwen/image` — 2.25–3.00 ₽
- `qwen/image-2` — 4.00 ₽

Можно переопределить через:
- `POLZA_IMAGE_MODEL` env var
- `image_gen.polza.model` в `config.yaml`
- `image_gen.model` (через `hermes tools`)

### Конфигурация

```yaml
image_gen:
  provider: polza
  polza:
    model: yandex/yandex-art

plugins:
  enabled:
    - image_gen/polza

toolsets:
  - hermes-cli  # для CLI — включает image_generate
  # Для Telegram нужно включать отдельно:
  # - hermes-telegram  # или собрать кастомный toolsets image_gen
```

### Как включить image_gen на платформе

Чтобы модель могла вызывать `image_generate`, тула должна быть в инструментарии платформы. Самый надёжный способ — добавить `image_gen` (готовый toolset) в `platform_toolsets` для каждой платформы, где нужна генерация:

```yaml
platform_toolsets:
  cli:
    - image_gen
  telegram:
    - image_gen
```

Либо через `hermes tools` → Image Generation → включить.

> **Важно:** Без этого модель не будет знать о туле, даже если плагин установлен и работает.

### Структура

```
plugins/image_gen/polza/
├── __init__.py        # PolzaImageProvider(ImageGenProvider) — прямой вызов /v2/images/generations
├── _utils.py          # Pure helpers (no Hermes deps) — _build_images_endpoint, _dedupe_models
├── plugin.yaml        # Манифест (kind: backend, requires_env: POLZA_API_KEY)
├── AGENTS.md          # Шпаргалка для AI-ассистентов
└── ARCHITECTURE.md    # Архитектура плагина
```

---

## Сборка и тестирование

```bash
make install-dev   # установка в editable mode + test deps
make lint          # ruff check
make format        # ruff format
make sast          # bandit security scan
make test          # unit-тесты
make live-test     # live-тесты (требуют POLZA_API_KEY)
make ci            # полный CI-пайплайн (lint + sast + compile + test)
```

## Планирование

- `PLAN.md` — план исправлений по findings аудита
- `TASKS.md` — разбивка плана на исполнимые задачи для @coder

## Обновление

```bash
cd ~/git/polza-hermes-plugin && git pull && systemctl --user restart hermes-gateway
```
