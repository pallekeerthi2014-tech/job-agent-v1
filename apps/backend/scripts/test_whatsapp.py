"""
test_whatsapp.py — Verify Twilio WhatsApp connection (Phase 2)

Run this BEFORE the full pipeline to confirm your Twilio credentials
and team numbers are configured correctly.

Usage (inside Docker):
    docker-compose exec backend python scripts/test_whatsapp.py

Usage (local):
    cd apps/backend
    python scripts/test_whatsapp.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load .env if running locally (Docker already injects env vars so this is a no-op there)
try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    for _parent in _here.parents:
        _candidate = _parent / ".env"
        if _candidate.exists():
            load_dotenv(_candidate)
            break
except Exception:
    pass


def main() -> None:
    print("\n── ThinkSuccess WhatsApp Connection Test ──\n")

    # Check credentials
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "")
    raw_numbers = os.getenv("WHATSAPP_TEAM_NUMBERS", "")

    ok = True
    checks = [
        ("TWILIO_ACCOUNT_SID", bool(account_sid), account_sid[:8] + "..." if account_sid else "NOT SET"),
        ("TWILIO_AUTH_TOKEN",  bool(auth_token),  "set (hidden)" if auth_token else "NOT SET"),
        ("TWILIO_WHATSAPP_FROM", bool(from_number), from_number or "NOT SET"),
        ("WHATSAPP_TEAM_NUMBERS", bool(raw_numbers), raw_numbers or "NOT SET"),
    ]
    for name, passed, display in checks:
        icon = "✓" if passed else "✗"
        print(f"  {icon}  {name}: {display}")
        if not passed:
            ok = False

    if not ok:
        print("\n  One or more required env vars are missing. Check your .env file.\n")
        sys.exit(1)

    # Parse team numbers
    team_numbers = [
        (n.strip() if n.strip().startswith("whatsapp:") else f"whatsapp:{n.strip()}")
        for n in raw_numbers.split(",") if n.strip()
    ]
    print(f"\n  Team numbers ({len(team_numbers)}):")
    for n in team_numbers:
        print(f"    • {n}")

    # Try importing Twilio
    try:
        from twilio.rest import Client
    except ImportError:
        print("\n  ✗  twilio package not installed. Run: pip install twilio\n")
        sys.exit(1)

    # Send a test message to each number
    print("\n  Sending test WhatsApp messages...\n")
    wa_from = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
    client  = Client(account_sid, auth_token)
    sent, failed = 0, 0

    test_body = (
        "👋 ThinkSuccess Job Alert Platform — test message.\n"
        "If you received this, your WhatsApp alert setup is working correctly!"
    )

    for to_number in team_numbers:
        try:
            msg = client.messages.create(body=test_body, from_=wa_from, to=to_number)
            print(f"  ✓  {to_number}  →  SID: {msg.sid}")
            sent += 1
        except Exception as exc:
            print(f"  ✗  {to_number}  →  ERROR: {exc}")
            failed += 1

    print(f"\n  Result: {sent} sent, {failed} failed")

    if failed > 0:
        print(
            "\n  Tip: Make sure each number has joined the Twilio sandbox by sending\n"
            "  'join <your-sandbox-code>' to +14155238886 via WhatsApp.\n"
        )
    else:
        print("\n  All good! Your team should receive the test messages now.\n")


if __name__ == "__main__":
    main()
