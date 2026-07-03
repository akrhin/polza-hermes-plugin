"""
Polza Balance Plugin — /balance slash command for Telegram
"""

import json
import urllib.request
import os
from datetime import datetime, timezone, timedelta

API_BASE = "https://polza.ai/api/v1"
MSK = timezone(timedelta(hours=3))


def _fetch_json(url: str) -> dict:
    key = os.environ.get("POLZA_API_KEY", "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _to_msk(created_at: str) -> str:
    """Parse ISO UTC string, return MSK time as HH:MM."""
    if not created_at:
        return "??:??"
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.astimezone(MSK).strftime("%H:%M")
    except Exception:
        return "??:??"


def _split_provider(model_name: str) -> tuple:
    """Split 'Provider: Model Name' into (provider, model)."""
    if ":" in model_name:
        parts = model_name.split(":", 1)
        return (parts[0].strip(), parts[1].strip())
    return ("", model_name)


def _handle_balance(raw_args: str) -> str:
    args = raw_args.strip().lower()
    no_args = not args
    only_balance = args == "only"

    show_today = (no_args or "today" in args or "сегодня" in args) and not only_balance
    recent_n = 10 if no_args else 0
    for word in args.split():
        try:
            n = int(word)
            if n in (10, 20):
                recent_n = n
        except ValueError:
            pass

    try:
        bal = _fetch_json(f"{API_BASE}/balance")
    except Exception as e:
        return f"❌ Ошибка баланса: {e}"

    amount = float(bal.get("amount", 0) or 0)
    spent = float(bal.get("spentAmount", 0) or 0)

    now = datetime.now(MSK)
    now_str = now.strftime("%d.%m.%Y %H:%M")

    lines = []
    # ── Header ──
    lines.append(f"📊 <b>Polza AI — {now_str} MSK</b>")
    lines.append(f"💰 Баланс: <b>{amount:.2f} ₽</b> | Всего потрачено: {spent:.2f} ₽")
    if amount < 100:
        lines.append(f"⚠️ Баланс ниже 100 ₽!")

    all_items = []

    if show_today:
        today_start = datetime(now.year, now.month, now.day, tzinfo=MSK)
        date_from = today_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        page = 1
        all_items = []
        while True:
            try:
                data = _fetch_json(
                    f"{API_BASE}/history/generations"
                    f"?page={page}&limit=100"
                    f"&dateFrom={date_from}&dateTo={date_to}"
                    f"&sortBy=createdAt&sortOrder=desc"
                )
            except Exception:
                break
            items = data.get("items", [])
            if not items:
                break
            all_items.extend(items)
            page += 1
            if len(items) < 100:
                break

        total_cost = 0.0
        total_prompt = 0
        total_completion = 0
        total_cached = 0
        total_reasoning = 0
        total_gen = len(all_items)
        by_provider_model = {}

        for item in all_items:
            cost = float(item.get("cost", 0) or 0)
            usage = item.get("usage", {}) or {}
            pt = usage.get("prompt_tokens", 0) or 0
            ct = usage.get("completion_tokens", 0) or 0
            ptd = usage.get("prompt_tokens_details", {}) or {}
            ctd = usage.get("completion_tokens_details", {}) or {}
            cached = ptd.get("cached_tokens", 0) or 0
            reasoning = ctd.get("reasoning_tokens", 0) or 0
            total_cost += cost
            total_prompt += pt
            total_completion += ct
            total_cached += cached
            total_reasoning += reasoning

            raw_model = item.get("modelDisplayName", item.get("model", "unknown"))
            provider, model_name = _split_provider(raw_model)
            pm_key = (provider, model_name)
            if pm_key not in by_provider_model:
                by_provider_model[pm_key] = {
                    "cost": 0.0, "prompt": 0, "completion": 0, "gen": 0,
                }
            s = by_provider_model[pm_key]
            s["cost"] += cost
            s["prompt"] += pt
            s["completion"] += ct
            s["gen"] += 1

        cache_pct = int(total_cached / total_prompt * 100) if total_prompt > 0 else 0

        lines.append("")
        lines.append(
            f"📅 <b>Сегодня</b>: {total_gen} gen · "
            f"{_fmt_num(total_prompt)} in / {_fmt_num(total_completion)} out · "
            f"🗄{cache_pct}% cached · 🧠{_fmt_num(total_reasoning)} thinking · "
            f"💰 {total_cost:.2f} ₽"
        )

        top5 = sorted(
            by_provider_model.items(), key=lambda x: x[1]["cost"], reverse=True
        )[:5]
        if top5:
            lines.append(f"<b>Топ-5:</b>")
            for (provider, model_name), s in top5:
                tag = f"[{provider}] " if provider else ""
                lines.append(
                    f"  {tag}{model_name}: {s['cost']:.2f} ₽ "
                    f"({_fmt_num(s['prompt'])}/{_fmt_num(s['completion'])}, {s['gen']} gen)"
                )

    # ── Recent N ──
    if recent_n > 0:
        if all_items:
            # all_items is newest-first; take the first N = truly newest
            recent_items = all_items[:recent_n]
        else:
            try:
                data = _fetch_json(
                    f"{API_BASE}/history/generations"
                    f"?page=1&limit={recent_n}"
                    f"&sortBy=createdAt&sortOrder=desc"
                )
                recent_items = data.get("items", [])[:recent_n]
            except Exception:
                recent_items = []

        if not recent_items:
            recent_items = []

        lines.append("")
        lines.append(f"🕐 <b>Последние {recent_n} запросов:</b>")
        lines.append("<pre>")
        lines.append(f"{'Время':6s} | {'Модель':30s} | {'In/Out':14s} | {'₽':24s} | {'Длит':>6s}")
        lines.append(f"{'------':6s} | {'------------------------------':30s} | {'--------------':14s} | {'------------------------':24s} | {'------':>6s}")
        for item in recent_items:
            cost = float(item.get("cost", 0) or 0)
            usage = item.get("usage", {}) or {}
            pt = usage.get("prompt_tokens", 0) or 0
            ct = usage.get("completion_tokens", 0) or 0
            ptd = usage.get("prompt_tokens_details", {}) or {}
            ctd = usage.get("completion_tokens_details", {}) or {}
            cached = ptd.get("cached_tokens", 0) or 0
            reasoning = ctd.get("reasoning_tokens", 0) or 0

            t = _to_msk(item.get("createdAt", ""))
            raw_model = item.get("modelDisplayName", item.get("model", "unknown"))
            provider, model_name = _split_provider(raw_model)
            full_name = f"[{provider}] {model_name}" if provider else model_name
            gen_ms = item.get("generationTimeMs", 0) or 0
            time_str = f"{gen_ms/1000:.1f}s" if gen_ms >= 1000 else f"{gen_ms}ms"

            inout = f"{_fmt_num(pt)}/{_fmt_num(ct)}"
            extra = ""
            if cached > 0 and pt > 0:
                extra += f" 🗄{int(cached/pt*100)}%"
            if reasoning > 0:
                extra += f" 🧠{_fmt_num(reasoning)}"
            cost_str = f"{cost:.2f}"

            lines.append(
                f"{t:>6s} | {full_name:30s} | {inout:>13s} | "
                f"{cost_str:>7s}{extra} | {time_str:>6s}"
            )
        lines.append("</pre>")

    return "\n".join(lines)


def register(ctx):
    """Register /balance slash command."""
    ctx.register_command(
        "balance",
        handler=_handle_balance,
        description="Check Polza AI balance and spending",
        args_hint="[today] [10|20]",
    )
