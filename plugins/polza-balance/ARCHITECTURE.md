# Architecture — Polza Balance Plugin

## Overview

`plugins/polza-balance/` — Hermes plugin that registers a `/balance` slash command. No tools, no hooks — just a command handler that calls Polza API.

## Flow

```
User: /balance 10
  ↓
Hermes gateway → dispatches to plugin handler
  ↓
_handle_balance("10") → calls Polza API
  ↓
GET /v1/balance          → { amount, spentAmount }
GET /v1/history/generations → { items [...] }
  ↓
Returns formatted HTML → Telegram message
```

## Key Design Decisions

### Why a plugin, not a skill?
- Slash commands (`/balance`) can ONLY be registered by plugins via `ctx.register_command()`.
- Skills cannot register commands — only tools.
- Plugin is auto-discovered by Hermes (`~/.hermes/plugins/polza-balance/`).

### Plugin vs MCP server
- Balance check is a 2-API-call operation — lightweight. MCP server would be overkill.
- Plugin runs in-process (no stdio transport overhead).
- Both would work; plugin is simpler.

### No tools needed
- Only `/balance` command. No tool registration — no `provides_tools` in `plugin.yaml`.
- The handler fetches data and returns the formatted string directly.

## File Structure

```
plugins/polza-balance/
├── __init__.py    # Handler + register() function
├── plugin.yaml    # Manifest (name, version, requires_env)
└── AGENTS.md      # AI-assistant cheat sheet
```

## Auto-registration Flow

1. Gateway starts → scans `~/.hermes/plugins/polza-balance/`
2. Reads `plugin.yaml` — checks `requires_env: POLZA_API_KEY`
3. If key present → calls `register(ctx)` from `__init__.py`
4. `register()` calls `ctx.register_command("balance", handler=..., description=...)`
5. `/balance` appears in Telegram menu, `/help`, CLI autocomplete
6. User types `/balance today 10` → `_handle_balance("today 10")` called
7. Handler parses args, fetches APIs, returns formatted HTML string
8. Platform adapter (Telegram/CLI) renders the response
