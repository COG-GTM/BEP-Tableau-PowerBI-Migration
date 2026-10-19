#!/usr/bin/env python3
"""Create an expiring HMAC-signed identity token for app_reader."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import time
from pathlib import Path

if __package__:
    from .load_postgres import connect_supabase
else:
    from load_postgres import connect_supabase


SIGNING_KEY_FILE = Path.home() / "gdit" / ".secrets" / "app_signing_key"


def sign_identity(email: str, ttl: int = 3600, *, cached_only: bool = False) -> str:
    if not email or "|" in email:
        raise ValueError("email must be non-empty and may not contain '|'")
    if ttl <= 0:
        raise ValueError("ttl must be greater than zero")
    SIGNING_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        key = bytes.fromhex(SIGNING_KEY_FILE.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        if cached_only:
            raise RuntimeError(f"Signing-key cache is required: {SIGNING_KEY_FILE}")
        connection = connect_supabase("postgres")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT secret_key FROM security.app_signing_key WHERE singleton"
                )
                row = cursor.fetchone()
        finally:
            connection.close()
        if row is None:
            raise RuntimeError("Supabase signing key is missing; reload the demo data")
        key = bytes(row[0])
        temporary_path = SIGNING_KEY_FILE.with_name(
            f".{SIGNING_KEY_FILE.name}.{os.getpid()}.tmp"
        )
        descriptor = os.open(
            temporary_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="ascii") as output:
            output.write(key.hex())
            output.write("\n")
        os.replace(temporary_path, SIGNING_KEY_FILE)
        SIGNING_KEY_FILE.chmod(0o600)
    expiry = int(time.time()) + ttl
    message = f"{email}|{expiry}"
    signature = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{message}|{signature}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args()
    print(sign_identity(args.email, args.ttl))


if __name__ == "__main__":
    main()
