"""Utility script to point a Twilio phone number at the local FastAPI webhook."""
from __future__ import annotations

# pyright: reportMissingImports=false

import argparse
import sys
from typing import Optional

import os
from typing import Any, Optional

from dotenv import load_dotenv
from twilio.rest import Client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update the Twilio voice webhook URL")
    parser.add_argument(
        "--public-url",
        required=True,
        help="Public HTTPS URL (for example https://abc.ngrok-free.app) that exposes your FastAPI server",
    )
    parser.add_argument(
        "--phone-number",
        dest="phone_number",
        help="E.164 formatted Twilio phone number (for example +12025551234)",
    )
    parser.add_argument(
        "--phone-sid",
        dest="phone_sid",
        help="Explicit PN SID of the Twilio phone number. Overrides --phone-number when provided.",
    )
    return parser.parse_args()


def find_phone_sid(client: Any, phone_number: str) -> Optional[str]:
    for incoming_number in client.incoming_phone_numbers.list(limit=20):
        if incoming_number.phone_number == phone_number:
            return incoming_number.sid
    return None


def main() -> int:
    args = parse_args()
    public_url = args.public_url.rstrip("/")

    if not public_url.startswith("http"):
        print("[error] --public-url must start with http or https", file=sys.stderr)
        return 1

    load_dotenv()
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        print("[error] TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set", file=sys.stderr)
        return 1

    client = Client(account_sid, auth_token)

    phone_sid = args.phone_sid
    if not phone_sid:
        if not args.phone_number:
            print("[error] Provide either --phone-sid or --phone-number", file=sys.stderr)
            return 1
        phone_sid = find_phone_sid(client, args.phone_number)
        if not phone_sid:
            print(f"[error] Could not locate phone number {args.phone_number} in this Twilio account", file=sys.stderr)
            return 1

    voice_url = f"{public_url}/twilio/voice"
    process_url = f"{public_url}/twilio/process-speech"

    try:
        updated = client.incoming_phone_numbers(phone_sid).update(
            voice_url=voice_url,
            voice_method="POST",
            status_callback=None,
        )
        print("Updated voice webhook:")
        print(f"  Phone Number: {updated.phone_number}")
        print(f"  Voice URL:   {updated.voice_url}")
        print(f"  Gather URL:  {process_url}")
        return 0
    except Exception as exc:  # noqa: BLE001 - surface full Twilio error message
        print(f"[error] Twilio API call failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
