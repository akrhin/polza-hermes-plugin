# Polza.ai Hermes Provider Plugin

[🇬🇧 English](README.md)

> **Унифицированный API для сотен AI-моделей** с оплатой в рублях, выбором
> провайдера, reasoning-токенами и веб-поиском — как встроенный провайдер
> Hermes Agent.

---

## Возможности

- **OpenAI-совместимость** — Chat Completions, Tools, Structured Output, Streaming
- **Выбор провайдера** — приоритет, сортировка по цене, белый/чёрный список
- **Reasoning** — o-series, DeepSeek R1, Claude Opus 4.7+, Grok
- **Веб-поиск** — доступ к реальному интернету для любой модели
- **Публичный каталог моделей** — `GET /v1/models` без API-ключа
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
echo 'POLZA_API_KEY=pza_ключ' >> ~/.hermes/.env
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

### С выбором провайдера (рекомендуется)

Объект `provider` передаётся напрямую через `extra_body`. Этот подход
работает во всех режимах (CLI, Gateway, WebUI) и соответствует формату
API Polza:

```yaml
model:
  provider: polza
  model: deepseek/deepseek-v4-flash
  extra_body:
    provider:
      only:
        - DeepSeek
        - OpenAI
        - Anthropic
      sort: price
      allow_fallbacks: true
```

Поля объекта `provider` (см. [документацию](https://polza.ai/docs/gaidy/provider-selection)):

| Поле | Тип | Описание |
|------|-----|----------|
| `only` | `string[]` | Белый список — только эти провайдеры |
| `ignore` | `string[]` | Чёрный список — исключить провайдеры |
| `order` | `string[]` | Приоритетный порядок |
| `sort` | `string` | Сортировка: `price`, `latency`, `throughput` |
| `max_price` | `object` | Макс. цена за 1М токенов: `{prompt, completion}` |
| `allow_fallbacks` | `boolean` | Fallback на другие провайдеры при ошибке |

**Почему `extra_body`, а не `providers:`?** `extra_body` — провайдер-специфичный,
однозначный и работает одинаково в CLI и Gateway. Верхнеуровневый `providers:`
работает только в CLI; `provider_routing:` — только в Gateway/WebUI.
`extra_body` работает везде.

### С reasoning

```yaml
reasoning_effort: high  # xhigh | high | medium | low | minimal | none
```

Подробнее: [документация Polza по reasoning](https://polza.ai/docs/osobennosti/reasoning-tokens).

### С веб-поиском

Polza поддерживает веб-поиск через поле `plugins` в `extra_body`:

```yaml
model:
  extra_body:
    plugins:
      - id: web
        max_results: 5
```

Или через `polza_web_search` в `config.yaml` (прокидывается через
`build_extra_body()` из `providers:` секции):

```yaml
# provider-specific context — must be enabled in config
polza_web_search:
  max_results: 5
  engine: auto  # auto | native | exa
```

### Баланс

Проверить баланс аккаунта Polza можно методом профиля:

```bash
python3 -c "
from providers import get_provider_profile
p = get_provider_profile('polza')
# Замените *** на ваш ключ или используйте os.environ
import os
key = os.environ.get('POLZA_API_KEY', '')
bal = p.check_balance(api_key=key)
print(f'Баланс: {bal} руб.')
"
```

Скрипт `scripts/check-balance.py` — если ещё не создан:

```python
#!/usr/bin/env python3
"""Check Polza.ai account balance."""
import os
from providers import get_provider_profile
p = get_provider_profile("polza")
key = os.environ.get("POLZA_API_KEY") or input("POLZA_API_KEY: ")
bal = p.check_balance(api_key=key)
if bal is None:
    print("Не удалось проверить баланс")
else:
    print(f"Баланс: {bal} руб.")
```

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
не изменяется.

Подробности реализации — в [`DEVELOPMENT.md`](DEVELOPMENT.md).
