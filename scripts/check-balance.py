#!/usr/bin/env python3
"""Check Polza.ai account balance.

Usage:
    # Uses POLZA_API_KEY from environment
    python3 scripts/check-balance.py

    # Or enter key interactively
    python3 scripts/check-balance.py --key YOUR_KEY
"""

import argparse
import os
import sys

# ⚠️ Requires Hermes agent venv — run as:
#   /home/sintez/.hermes/hermes-agent/venv/bin/python3 scripts/check-balance.py
from providers import get_provider_profile


def main():
    parser = argparse.ArgumentParser(description="Check Polza.ai account balance")
    parser.add_argument("--key", help="Polza API key (default: POLZA_API_KEY env var)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    api_key = args.key or os.environ.get("POLZA_API_KEY") or ""
    if not api_key:
        print("Error: POLZA_API_KEY not set. Use --key or set the environment variable.")
        sys.exit(1)

    p = get_provider_profile("polza")
    if p is None:
        print("Error: Polza provider profile not found — is the plugin installed?")
        sys.exit(1)

    balance = p.check_balance(api_key=api_key)
    if balance is None:
        print("Error: Could not fetch balance. Check your API key and network.")
        sys.exit(1)

    if args.json:
        import json
        json.dump({"balance": balance, "currency": "RUB"}, sys.stdout, indent=2)
        print()
    else:
        print(f"Polza.ai balance: {balance:.2f} RUB")


if __name__ == "__main__":
    main()
