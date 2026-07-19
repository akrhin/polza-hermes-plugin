# AGENTS.md — для AI-ассистентов

> Копия корневого AGENTS.md с фокусом на Image Gen Plugin.

## Polza Image Gen Plugin

Плагин генерации изображений через Polza.ai. Регистрируется как `ImageGenProvider`
через `ctx.register_image_gen_provider()`.

### Ключевые моменты

- `PolzaImageProvider(ImageGenProvider)` — все в `__init__.py`
- Использует OpenAI-совместимый `/v2/images/generations` (НЕ chat/completions с modalities)
- Credentials через `resolve_runtime_provider("polza")` — тот же механизм, что у model-provider
- **Text-to-image only** — image-to-image / editing не поддерживается, вызов с `image_url` вернёт ошибку
- Результат (эфимерная URL на S3) скачивается локально в `~/.hermes/cache/images/`

### Модели

| Модель | Цена | Статус |
|--------|------|--------|
| `yandex/yandex-art` | 2.91 RUB/image | Дефолт, проверен |
| `seedream/5-pro-text-to-image` | varies | Fallback |
| `qwen/image` | 2.25–3.00 RUB | Альтернатива |
| `qwen/image-2` | 4.00 RUB | Альтернатива |

Переопределение модели (приоритет):
1. `POLZA_IMAGE_MODEL` env var
2. `image_gen.polza.model` в `config.yaml`
3. `image_gen.model` в `config.yaml`
4. Дефолтная цепочка: `yandex/yandex-art` → `seedream/5-pro-text-to-image`

### Pure helpers в `_utils.py`

`_utils.py` выделен для тестирования без Hermes:

- `_build_images_endpoint(base_url)` — сборка URL из base API URL
- `_dedupe_models(models)` — дедупликация списка моделей
- `_POLZA_DEFAULT`, `_POLZA_FALLBACK` — константы

### Структура

```
plugins/image_gen/polza/
├── __init__.py        # PolzaImageProvider + register()
├── _utils.py          # Pure helpers (no Hermes deps)
├── plugin.yaml        # Манифест (kind: backend)
├── AGENTS.md          # Этот файл
└── ARCHITECTURE.md    # Архитектура
```
