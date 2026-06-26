#!/usr/bin/env python3
"""Polza.ai health check — balance, models, provider status.

Usage:
    # Full check
    python3 scripts/polza-doctor.py

    # Quick balance only
    python3 scripts/polza-doctor.py --balance-only

    # JSON output
    python3 scripts/polza-doctor.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ⚠️ Requires Hermes agent venv:
#   /home/sintez/.hermes/hermes-agent/venv/bin/python3 scripts/polza-doctor.py

from providers import get_provider_profile

CHECK_EMOJI = {"pass": "✅", "warn": "⚠️ ", "fail": "❌", "info": "ℹ️ "}


def check(typ: str, label: str, detail: str = ""):
    emoji = CHECK_EMOJI.get(typ, "•")
    print(f"  {emoji} {label}" + (f" — {detail}" if detail else ""))


def get_api_key() -> str:
    """Resolve Polza API key from env, .env, or credential pool."""
    # Try env var first
    api_key = os.environ.get("POLZA_API_KEY", "").strip()
    if api_key:
        return api_key

    # Try credential pool
    try:
        from agent.credential_pool import load_pool
        pool = load_pool("polza")
        if pool and pool.has_credentials():
            entry = pool.peek()
            if entry:
                tok = getattr(entry, "access_token", "") or ""
                if tok:
                    return str(tok).strip()
    except Exception:
        pass

    # Try .env file directly
    try:
        from pathlib import Path
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("POLZA_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("\"'")
                    if key:
                        return key
    except Exception:
        pass

    return ""


def run_check(args: argparse.Namespace) -> dict:
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "polza",
        "checks": {},
    }

    print(f"┌─ Polza.ai Health Check ──────────────────────")
    print(f"│ {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"└──────────────────────────────────────────────")

    # ── 1. Profile registration ──
    print("\n── Provider profile ──")
    profile = get_provider_profile("polza")
    check("pass" if profile else "fail", "Profile registered",
          f"name={profile.name}" if profile else "NOT FOUND")
    results["checks"]["profile"] = bool(profile)

    if not profile:
        check("fail", "Cannot continue — profile not found")
        return results

    # ── 2. API key ──
    print("\n── API key ──")
    api_key = get_api_key()
    if api_key:
        check("pass", f"Key resolved", f"{api_key[:16]}...{api_key[-4:]} ({len(api_key)} chars)")
        results["checks"]["api_key_present"] = True
    else:
        check("fail", "API key", "Not found in env, .env, or credential pool")
        check("info", "Set via", "export POLZA_API_KEY=... or hermes auth add polza ...")
        results["checks"]["api_key_present"] = False
        return results

    # ── 3. Model catalog ──
    print("\n── Model catalog ──")
    try:
        models = profile.fetch_models(api_key=None, timeout=8.0)
        if models is None:
            check("warn", "Live model fetch", "Timed out or failed — using fallback models")
            model_count = len(profile.fallback_models)
            results["checks"]["models_live"] = False
        else:
            model_count = len(models)
            check("pass", f"Live fetch OK", f"{model_count} models available")
            results["checks"]["models_live"] = True
        results["checks"]["model_count"] = model_count
    except Exception as e:
        check("warn", "Model fetch", str(e))
        model_count = len(profile.fallback_models)
        results["checks"]["models_live"] = False
        results["checks"]["model_count"] = model_count

    # ── 4. Balance ──
    if not args.balance_only:
        print("\n── Balance ──")
    else:
        print()

    try:
        balance = profile.check_balance(api_key=api_key, timeout=10.0)
        if balance is None:
            check("warn", "Balance check", "Failed (network or auth error)")
            results["checks"]["balance"] = None
        else:
            status = "pass" if balance > 50 else ("warn" if balance > 10 else "fail")
            check(status, f"Balance: {balance:.2f} RUB",
                  "Plenty 💰" if balance > 100 else ("Getting low" if balance > 10 else "CRITICAL — add funds"))
            results["checks"]["balance"] = balance
    except Exception as e:
        check("warn", "Balance check", str(e))
        results["checks"]["balance"] = None

    # ── 5. Configuration ──
    print("\n── Configuration ──")
    check("info", "Base URL", profile.base_url)
    check("info", "Models URL", profile.models_url)
    check("info", "Auth type", profile.auth_type)
    check("info", "Aux model", profile.default_aux_model)
    check("info", "Fallback models", ", ".join(profile.fallback_models[:3]) + "...")
    results["checks"]["config"] = {
        "base_url": profile.base_url,
        "models_url": profile.models_url,
        "auth_type": profile.auth_type,
        "default_aux_model": profile.default_aux_model,
        "fallback_models": list(profile.fallback_models),
    }

    # ── 6. Summary ──
    if not args.balance_only:
        print(f"\n── Summary ──")
        balance_ok = results["checks"].get("balance", 0) or 0
        bal_status = "✅ Healthy" if balance_ok > 10 else ("⚠️  Low funds" if balance_ok > 0 else "❌ No balance data")
        print(f"  Models: {model_count} | Balance: {balance_ok:.2f} RUB | {bal_status}")
        results["summary"] = f"Models={model_count}, Balance={balance_ok:.2f}, Status={bal_status}"

    return results


def main():
    parser = argparse.ArgumentParser(description="Polza.ai health check")
    parser.add_argument("--balance-only", action="store_true", help="Only check balance")
    parser.add_argument("--json", action="store_true", help="Output as JSON only")
    args = parser.parse_args()

    results = run_check(args)

    if args.json:
        json.dump(results, sys.stdout, indent=2, default=str)
        print()

    return 0 if results["checks"].get("api_key_present") else 1


if __name__ == "__main__":
    sys.exit(main())
