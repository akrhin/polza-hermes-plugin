# AGENTS.md — для AI-ассистентов

## Polza Balance Plugin

Плагин в `plugins/polza-balance/` — регистрирует слэш-команду `/balance` в Hermes.

### Установка

```bash
# Симлинк из репозитория в ~/.hermes/plugins/
ln -sf ~/git/polza-hermes-plugin/plugins/polza-balance ~/.hermes/plugins/polza-balance

# Добавить в config.yaml plugins.enabled:
#   - polza-balance

# Перезагрузить gateway:
systemctl --user restart hermes-gateway
```

### Команды в Telegram

| Команда | Что показывает |
|---------|----------------|
| `/balance` | Баланс + всего потрачено |
| `/balance today` | + статистика за сегодня |
| `/balance 10` | + последние 10 запросов |
| `/balance 20` | + последние 20 запросов |
| `/balance today 10` | Всё сразу |

### API (используется плагином)

```bash
GET /v1/balance
→ { "amount": "434.14", "spentAmount": "7819.16", "reservedAmount": "0.00", "updatedAt": "..." }

GET /v1/history/generations?page=1&limit=N&dateFrom=...&dateTo=...&sortBy=createdAt&sortOrder=desc
→ { "items": [...], "meta": { "total": N, "page": 1, "limit": N } }
```

### Особенности реализации

- `register(ctx)` вызывается автоматически при загрузке плагина
- `ctx.register_command("balance", handler=..., description=..., args_hint=...)` — регистрирует `/balance`
- Хендлер принимает `raw_args: str` — всё после команды
- Время в ответе — MSK (UTC+3)
- `dateFrom` для today считается от начала дня по Москве, переводится в UTC
- API history работает в UTC — `createdAt` в ответе тоже UTC, конвертится в MSK
- Учти: `amount` и `cost` приходят строками, надо `float()`

### Скрипт для cron

`~/git/polza-hermes-plugin/scripts/check-balance.cpython-311.pyc` — старый скрипт, не используется. Актуальный: `~/.hermes/scripts/check-polza-balance.sh` (bash обёртка над Python).

### Требования

- `POLZA_API_KEY` в `~/.hermes/.env`
- Плагин сам проверяет наличие ключа на старте (через `requires_env`)
