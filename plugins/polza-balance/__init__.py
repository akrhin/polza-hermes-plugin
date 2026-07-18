"""
Polza Balance Plugin — /balance slash command for Telegram
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta, timezone

API_BASE = "https://polza.ai/api/v1"
MSK = timezone(timedelta(hours=3))

logger = logging.getLogger(__name__)

# ── Provider colors (copied from polza-balance.js widget) ──────────
PROVIDER_COLORS = {
    "DeepSeek": "#2e86de",
    "GMICloud": "#e74c3c",
    "Nebius":   "#2ecc71",
    "Parasail": "#f39c12",
    "Morph":    "#9b59b6",
    "Venice":   "#1abc9c",
    "Nvidia":   "#e91e63",
    "Mancer":   "#34495e",
}

COLOR_TO_EMOJI = {
    "#2e86de": "\U0001f535",
    "#e74c3c": "\U0001f534",
    "#2ecc71": "\U0001f7e2",
    "#f39c12": "\U0001f7e1",
    "#9b59b6": "\U0001f7e3",
    "#1abc9c": "\U0001f7e0",
    "#e91e63": "\U0001f7e3",
    "#34495e": "\U000026ab",
}


def _provider_color(provider_name: str) -> str:
    if not provider_name:
        return "#888"
    if provider_name in PROVIDER_COLORS:
        return PROVIDER_COLORS[provider_name]
    h, mod = 0, 1000003
    for ch in provider_name:
        h = (h * 131 + ord(ch)) % mod
    hue = (((h * 1234567) % mod + mod) % mod / mod) * 360
    sat = 55 + (h % 30)
    lit = 35 + ((h >> 4) % 25)
    return f"hsl({round(hue)}, {sat}%, {lit}%)"


def _provider_dot(provider_name: str) -> str:
    c = _provider_color(provider_name)
    return COLOR_TO_EMOJI.get(c, "\U000026ab")


def _fetch_json(url: str) -> dict:
    key = os.environ.get("POLZA_API_KEY", "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310 — hardcoded URLs to Polza API only
        return json.loads(resp.read())


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _to_msk(created_at: str) -> str:
    if not created_at:
        return "??:??"
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.astimezone(MSK).strftime("%H:%M")
    except (ValueError, TypeError):
        logger.debug("_to_msk: invalid created_at=%r", created_at)
        return "??:??"


def _split_provider(model_name: str) -> tuple:
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
            if n > 0:
                recent_n = n
        except ValueError:
            pass

    try:
        bal = _fetch_json(f"{API_BASE}/balance")
    except Exception as e:
        return f"Ошибка баланса: {e}"

    amount = float(bal.get("amount", 0) or 0)
    spent = float(bal.get("spentAmount", 0) or 0)

    now = datetime.now(MSK)
    now_str = now.strftime("%d.%m.%Y %H:%M")

    lines = []
    lines.append(f"\U0001f4ca <b>Polza AI \u2014 {now_str} MSK</b>")
    lines.append(
        f"\U0001f4b0 \u0411\u0430\u043b\u0430\u043d\u0441: <b>{amount:.2f} \u20bd</b>"
        f" | \u041f\u043e\u0442\u0440\u0430\u0447\u0435\u043d\u043e \u0432\u0441\u0435\u0433\u043e: {spent:.2f} \u20bd"
    )
    if amount < 100:
        lines.append("\u26a0\ufe0f \u0411\u0430\u043b\u0430\u043d\u0441 \u043d\u0438\u0436\u0435 100 \u20bd!")

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
            except Exception:  # noqa: BLE001 — network errors are transient
                logger.warning("pagination page=%d failed", page, exc_info=True)
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
        by_provider = {}

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

            p_provider = item.get("provider", provider)
            if p_provider:
                if p_provider not in by_provider:
                    by_provider[p_provider] = {"cost": 0.0, "count": 0}
                by_provider[p_provider]["cost"] += cost
                by_provider[p_provider]["count"] += 1

        cache_pct = int(total_cached / total_prompt * 100) if total_prompt > 0 else 0

        lines.append("")
        lines.append(
            f"\U0001f4c5 <b>\u0421\u0435\u0433\u043e\u0434\u043d\u044f</b>: {total_gen} gen \u2014 "
            f"\U0001f4e5{_fmt_num(total_prompt)} / \U0001f4e4{_fmt_num(total_completion)} \u2014 "
            f"\U0001f5c4\ufe0f{cache_pct}% \u2014 \U0001f9e0{_fmt_num(total_reasoning)} \u2014 "
            f"\U0001f4b0{total_cost:.2f}\u20bd"
        )

        top5 = sorted(
            by_provider_model.items(), key=lambda x: x[1]["cost"], reverse=True
        )[:5]
        if top5:
            lines.append("  🏆 <b>Топ-5</b>")
            for (provider, model_name), s in top5:
                dot = _provider_dot(provider)
                tag = f"{dot} " if provider else ""
                lines.append(
                    f"    \U0001f4b0{s['cost']:.2f}\u20bd {tag}{model_name}"
                    f" (\U0001f4e5{_fmt_num(s['prompt'])}/\U0001f4e4{_fmt_num(s['completion'])}, {s['gen']} gen)"
                )

        if len(by_provider) > 0:
            provider_list = sorted(
                by_provider.items(), key=lambda x: x[1]["cost"], reverse=True
            )
            lines.append("  \u26c1 <b>\u041f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440\u044b</b>")
            max_pn = max(len(pn) for pn, _ in provider_list) if provider_list else 0
            for pn, ps in provider_list:
                dot = _provider_dot(pn)
                avg = ps["cost"] / ps["count"] if ps["count"] > 0 else 0
                lines.append(
                    f"    {dot} {pn:<{max_pn}s}  "
                    f"\U0001f4ca{ps['count']:>3d}  \U0001f4b0{ps['cost']:>7.2f}\u20bd  \u0441\u0440\u0435\u0434\u043d\u0435\u0435 {avg:.2f}\u20bd"
                )

    # ── Recent N ──
    if recent_n > 0:
        if all_items:
            recent_items = all_items[:recent_n]
        else:
            try:
                data = _fetch_json(
                    f"{API_BASE}/history/generations"
                    f"?page=1&limit={recent_n}"
                    f"&sortBy=createdAt&sortOrder=desc"
                )
                recent_items = data.get("items", [])[:recent_n]
            except Exception:  # noqa: BLE001 — network errors
                logger.warning("failed to fetch recent items", exc_info=True)
                recent_items = []

        if not recent_items:
            recent_items = []

        lines.append("")
        lines.append(f"\U0001f550 <b>\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 {recent_n} \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432</b>")
        lines.append("<pre>")

        # Plain text headers — no emoji (monospace breaks on emoji width)
        lines.append(f"{'Время':>5s} | {'Модель':28s} | {'In/Out':13s} | {'Цена':>20s} | {'Длит':>6s}")
        lines.append(
            f"{'-----':>5s} | {'----------------------------':28s} | "
            f"{'-------------':13s} | {'--------------------':20s} | {'------':>6s}"
        )
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
            # No emoji dot inside <pre> — plain model name only
            name = model_name[:28]
            gen_ms = item.get("generationTimeMs", 0) or 0
            time_str = f"{gen_ms/1000:.1f}s" if gen_ms >= 1000 else f"{gen_ms}ms"

            inout = f"{_fmt_num(pt)}/{_fmt_num(ct)}"
            extra = ""
            if cached > 0 and pt > 0:
                extra += f" c{int(cached/pt*100)}%"
            if reasoning > 0:
                extra += f" r{_fmt_num(reasoning)}"
            cost_str = f"{cost:.2f}{extra}"

            lines.append(
                f"{t:>5s} | {name:28s} | {inout:>13s} | {cost_str:>20s} | {time_str:>6s}"
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
