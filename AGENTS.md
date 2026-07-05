# AGENTS.md — шпаргалка для AI-ассистентов

## Репозиторий: polza-hermes-plugin
## Деплой

Оба плагина прилинкованы симлинками:

```bash
ln -sf ~/git/polza-hermes-plugin/plugins/model-providers/polza ~/.hermes/plugins/model-providers/polza
ln -sf ~/git/polza-hermes-plugin/plugins/polza-balance ~/.hermes/plugins/polza-balance
```

В `~/.hermes/config.yaml`:
```yaml
plugins:
  enabled:
    - polza-provider
    - polza-balance
```

**Polza Provider** — основной LLM-провайдер для Hermes. Именно через него идут все запросы к DeepSeek V4 Flash и другим моделям.

**Polza Balance** — команда `/balance` в Telegram (с правами администратора чата).

## Связанные проекты

- **polza-webui-extensions** — [akrhin/polza-webui-extensions](https://github.com/akrhin/polza-webui-extensions) — UI-расширения для Hermes WebUI
- **polza-hermes-plugin** (этот репозиторий) — провайдер + баланс

## Два Hermes-плагина в одном репозитории:

| Плагин | Путь | Что делает |
|--------|------|------------|
| **Polza Provider** | `plugins/model-providers/polza/` | Провайдер LLM — добавляет Polza.ai как first-class provider |
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

## Обновление

```bash
cd ~/git/polza-hermes-plugin && git pull && systemctl --user restart hermes-gateway
```
