"""
Polza Balance Plugin — /balance slash command for Telegram
"""

import json
import urllib.request
import os
from datetime import datetime, timezone, timedelta

API_BASE = "https://polza.ai/api/v1"


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


def _handle_balance(raw_args: str):
    """Handler for /balance — optional args: today, 10, 20"""
    args = raw_args.strip().lower()

    show_today = "today" in args or "сегодня" in args
    recent_n = 0
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

    msk = timezone(timedelta(hours=3))
    now = datetime.now(msk)
    now_str = now.strftime("%d.%m.%Y %H:%M")

    out = []
    out.append(f"📊 <b>Polza AI — {now_str} MSK</b>")
    out.append(f"💰 Баланс: <b>{amount:.2f} ₽</b> | Всего потрачено: {spent:.2f} ₽")

    if amount < 100:
        out.append(f"⚠️ Баланс ниже 100 ₽!")

    # Today stats
    if show_today:
        today_start = datetime(now.year, now.month, now.day, tzinfo=msk)
        date_from = today_start.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
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
        by_model = {}

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
            model = item.get("modelDisplayName", item.get("model", "unknown"))
            if model not in by_model:
                by_model[model] = {
                    "cost": 0.0,
                    "prompt": 0,
                    "completion": 0,
                    "gen": 0,
                }
            s = by_model[model]
            s["cost"] += cost
            s["prompt"] += pt
            s["completion"] += ct
            s["gen"] += 1

        cache_pct = (
            int(total_cached / total_prompt * 100) if total_prompt > 0 else 0
        )
        out.append("")
        out.append(
            f"📅 <b>Сегодня</b>: {total_gen} gen · "
            f"{_fmt_num(total_prompt)} in / {_fmt_num(total_completion)} out · "
            f"🗄{cache_pct}% cached · 🧠{_fmt_num(total_reasoning)} thinking · "
            f"💰 {total_cost:.2f} ₽"
        )
        top5 = sorted(
            by_model.items(), key=lambda x: x[1]["cost"], reverse=True
        )[:5]
        if top5:
            out.append(f"<b>Топ-5 моделей:</b>")
            for m, s in top5:
                out.append(
                    f"  {m}: {s['cost']:.2f} ₽ "
                    f"({_fmt_num(s['prompt'])}/{_fmt_num(s['completion'])}, {s['gen']} gen)"
                )

    # Recent N
    if recent_n > 0:
        try:
            data = _fetch_json(
                f"{API_BASE}/history/generations"
                f"?page=1&limit={recent_n}"
                f"&sortBy=createdAt&sortOrder=desc"
            )
            items = data.get("items", [])[:recent_n]
        except Exception as e:
            items = []

        out.append("")
        out.append(f"🕐 <b>Последние {recent_n} запросов</b>")
        for item in items:
            cost = float(item.get("cost", 0) or 0)
            usage = item.get("usage", {}) or {}
            pt = usage.get("prompt_tokens", 0) or 0
            ct = usage.get("completion_tokens", 0) or 0
            ptd = usage.get("prompt_tokens_details", {}) or {}
            ctd = usage.get("completion_tokens_details", {}) or {}
            cached = ptd.get("cached_tokens", 0) or 0
            reasoning = ctd.get("reasoning_tokens", 0) or 0
            created = item.get("createdAt", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created = dt.astimezone(msk).strftime("%H:%M")
                except Exception:
                    pass
            model = item.get("modelDisplayName", item.get("model", "unknown"))
            gen_ms = item.get("generationTimeMs", 0) or 0
            time_str = (
                f"{gen_ms/1000:.1f}s" if gen_ms >= 1000 else f"{gen_ms}ms"
            )
            cache_str = (
                f" 🗄{int(cached/pt*100)}%"
                if pt > 0 and cached > 0
                else ""
            )
            rsn_str = (
                f" 🧠{_fmt_num(reasoning)}" if reasoning > 0 else ""
            )
            out.append(
                f"  {created} | {model} | {_fmt_num(pt)}/{_fmt_num(ct)} "
                f"| {cost:.2f}₽{cache_str}{rsn_str} | ⏱{time_str}"
            )

    return "\n".join(out)


def register(ctx):
    """Register /balance slash command."""
    ctx.register_command(
        "balance",
        handler=_handle_balance,
        description="Check Polza AI balance and spending",
        args_hint="[today] [10|20]",
    )
