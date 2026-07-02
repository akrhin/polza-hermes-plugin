# AGENTS.md — для AI-ассистентов

> Копия корневого AGENTS.md с фокусом на Provider Plugin.

## Polza Provider Plugin

Hermes model provider plugin. Добавляет Polza.ai как first-class provider.

### Ключевые моменты

- `PolzaProfile(ProviderProfile)` — все хуки в `__init__.py`
- Алиасы: `polza`, `polza-ai`, `pza`
- 376+ моделей через публичный `/v1/models`
- `build_extra_body(provider_preferences=...)` — роутинг по провайдерам
- `build_api_kwargs_extras(reasoning_config=...)` — reasoning
- Веб-поиск через `extra_body.plugins`

### Интеграции

| Layer | Как |
|-------|-----|
| PROVIDER_REGISTRY | Auth, credential pool, doctor |
| CANONICAL_PROVIDERS | CLI `/model` picker |
| URL-детекция | `polza.ai` → авт��определение |

### Структура

```
plugins/model-providers/polza/
├── __init__.py        # PolzaProfile + register_provider()
└── plugin.yaml        # Манифест
```
