# Polza Image Gen — Architecture

## Overview

Плагин добавляет Polza.ai как бэкенд генерации изображений в Hermes Agent.
В отличие от штатных бэкендов (OpenRouter, xAI), Polza использует
**OpenAI-совместимый `/v2/images/generations`**, а не `/chat/completions` с модальностями.

## Component diagram

```
Hermes Agent
  └── image_generate tool
        └── PolzaImageProvider.generate()
              ├── resolve_runtime_provider("polza") → api_key, base_url
              ├── _resolve_model_chain()
              │     ├── explicit override (kwargs["model"])
              │     ├── POLZA_IMAGE_MODEL env
              │     ├── image_gen.polza.model (config.yaml)
              │     ├── image_gen.model (config.yaml)
              │     └── [yandex/yandex-art, seedream/5-pro-text-to-image]
              └── POST /v2/images/generations
                    └── download ephemeral URL → save locally
```

## Design decisions

### Why not OpenRouterCompatImageProvider

Polza не поддерживает протокол `/chat/completions` с `modalities: ["image"]`.
Её image-модели работают только через стандартный images API.
Наследование от `OpenRouterCompatImageProvider` давало `400 BAD_REQUEST` или пустые ответы.

### Text-to-image only

Polza models не поддерживают image-to-image / editing.
Вызовы с `image_url` или `reference_image_urls` возвращают `error_response` с типом `not_supported`.

### Model chain with fallbacks

При неудаче генерации с первой моделью, провайдер автоматически пробует следующую
из цепочки (`_resolve_model_chain`). После исчерпания всех моделей возвращается ошибка.

### Credential resolution

Использует `hermes_cli.runtime_provider.resolve_runtime_provider("polza")` —
тот же механизм, что и model-provider. Один `POLZA_API_KEY` для обоих плагинов.

### Separate _utils.py

Pure-функции (`_build_images_endpoint`, `_dedupe_models`) вынесены в `_utils.py`,
чтобы unit-тесты могли импортировать их без Hermes-зависимостей.
