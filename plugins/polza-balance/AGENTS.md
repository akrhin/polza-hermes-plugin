# AGENTS.md — для AI-ассистентов

> Это копия корневого AGENTS.md с фокусом на Balance Plugin.
> Общий справочник по репозиторию — см. `/AGENTS.md` в корне.

## Polza Balance Plugin

Hermes plugin, регистрирующий слэш-команду `/balance` через `ctx.register_command()`.

### Команды в Telegram

| Команда | Что показывает |
|---------|----------------|
| `/balance` | Баланс + сегодня + последние 10 (по умолчанию) |
| `/balance only` | Только баланс |
| `/balance today` | + статистика за сегодня |
| `/balance 10` | + последние 10 запросов |
| `/balance 20` | + последние 20 запросов |
| `/balance today 10` | Всё сразу |

### Ключевые моменты для разработки

- **Строковый парсинг**: `amount`, `cost` приходят строками — `float()` обязателен
- **Время**: `createdAt` от API в UTC, конвертится в MSK (`UTC+3`)
- **dateFrom**: считается от 00:00 MSK сегодня, переводится в UTC для API
- **ctx.register_command()** принимает `(name, handler, description, args_hint)`. Хендлер получает `raw_args: str`
- **dispatch_tool()** — если хендлеру нужно вызвать тулзу (не нужно для баланса, но паттерн)
- **requires_env** в `plugin.yaml` — проверяет `POLZA_API_KEY` при старте
- **provides_tools: []** — команды НЕ тулы, это отдельный механизм

### Структура

```
plugins/polza-balance/
├── __init__.py        # register() + _handle_balance()
├── plugin.yaml        # Манифест
├── AGENTS.md          # Эта шпаргалка
└── ARCHITECTURE.md    # Архитектура
```

### API

```
GET /v1/balance
→ { "amount": "434.14", "spentAmount": "7819.16" }

GET /v1/history/generations?page=1&limit=10&dateFrom=...&dateTo=...
→ { "items": [...], "meta": { "total": N } }
```
