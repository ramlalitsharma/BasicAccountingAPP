"""CLI tool to generate RSA-signed license tokens for Accounting Pro.

The private key is loaded from a path on the operator's machine (typically
``C:\\Users\\<admin>\\.accountingpro_keys\\license_signing_priv.pem``). The
desktop app embeds only the matching public key and cannot forge tokens.

Usage (from the project root)::

    python tools/gen_license.py --tier pro --licensee "Coffee House Pvt Ltd" \\
        --expires 2027-08-01 --max-machines 2 --note "Annual subscription"

The tool prints a base64-encoded JSON token to stdout (and writes it to
``--out`` if provided) that the user pastes into Accounting Pro's License tab.

It also prints the SHA-256 fingerprint of the public key so the operator can
verify the on-device public key matches.

This file is part of the project but is **not** packaged into the desktop
installer (PyInstaller only bundles ``main.py`` and its imports). The private
key MUST live off-machine and MUST stay out of git.

Run from anywhere: the script locates the project root via ``__file__`` so the
``utils.license`` import resolves correctly.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

DEFAULT_PRIV_KEY_PATH = os.path.expanduser(
    os.path.join("~", ".accountingpro_keys", "license_signing_priv.pem")
)

TIER_CHOICES = ("free", "basic", "pro", "enterprise")

DEFAULT_TIER_FEATURES = {
    "free": {
        "whatsapp_invoice": False,
        "cloud_backup": False,
        "email_invoicing": False,
        "advanced_reports": False,
        "multi_company": False,
        "customer_notifications": False,
        "purchase_notifications": False,
        "sale_notifications": False,
    },
    "basic": {
        "whatsapp_invoice": False,
        "cloud_backup": True,
        "email_invoicing": False,
        "advanced_reports": False,
        "multi_company": False,
        "customer_notifications": False,
        "purchase_notifications": False,
        "sale_notifications": False,
    },
    "pro": {
        "whatsapp_invoice": True,
        "cloud_backup": True,
        "email_invoicing": True,
        "advanced_reports": True,
        "multi_company": False,
        "customer_notifications": True,
        "purchase_notifications": True,
        "sale_notifications": True,
    },
    "enterprise": {
        "whatsapp_invoice": True,
        "cloud_backup": True,
        "email_invoicing": True,
        "advanced_reports": True,
        "multi_company": True,
        "customer_notifications": True,
        "purchase_notifications": True,
        "sale_notifications": True,
    },
}

DEFAULT_DURATIONS_DAYS = {
    "monthly": 31,
    "annual": 365,
    "perpetual": 365 * 100,
}


def _load_private_key(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Private key not found: {path}")
    with open(path, "rb") as f:
        pem = f.read()
    from cryptography.hazmat.primitives import serialization
    try:
        return serialization.load_pem_private_key(pem, password=None)
    except Exception as exc:
        raise RuntimeError(f"Could not parse private key at {path}: {exc}") from exc


def _public_key_fingerprint(public_key) -> str:
    from cryptography.hazmat.primitives import serialization
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(pem).hexdigest()


def _canonical_payload(token: dict) -> bytes:
    d = {k: v for k, v in token.items() if k != "sig"}
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign_payload(private_key, payload: bytes) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    signature = private_key.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def _parse_expiry(expires_arg: str, issued: datetime) -> str:
    """Accept either an explicit YYYY-MM-DD date or one of: 30d / 1y / perpetual."""
    arg = (expires_arg or "").strip().lower()
    if not arg or arg == "perpetual":
        return (issued + timedelta(days=DEFAULT_DURATIONS_DAYS["perpetual"])).strftime(
            "%Y-%m-%dT00:00:00Z"
        )
    if arg.endswith("d"):
        try:
            days = int(arg[:-1])
        except ValueError:
            raise ValueError("--expires: <N>d requires an integer number of days")
        return (issued + timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    if arg.endswith("y"):
        try:
            years = int(arg[:-1])
        except ValueError:
            raise ValueError("--expires: <N>y requires an integer number of years")
        return (issued + timedelta(days=365 * years)).strftime("%Y-%m-%dT00:00:00Z")
    if arg in DEFAULT_DURATIONS_DAYS:
        return (issued + timedelta(days=DEFAULT_DURATIONS_DAYS[arg])).strftime(
            "%Y-%m-%dT00:00:00Z"
        )
    try:
        d = datetime.strptime(arg, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            "--expires must be YYYY-MM-DD, Nd, Ny, monthly, annual, or perpetual"
        )
    return d.strftime("%Y-%m-%dT00:00:00Z")


def build_token(*, tier: str, licensee: str, expires: str,
                max_machines: int, note: str, features_override: dict) -> dict:
    issued = datetime.now(timezone.utc)
    issued_iso = issued.strftime("%Y-%m-%dT00:00:00Z")
    expires_iso = _parse_expiry(expires, issued)
    key_raw = secrets.token_bytes(32)
    key_hash = hashlib.sha256(key_raw).hexdigest()
    features = dict(DEFAULT_TIER_FEATURES.get(tier, {}))
    if features_override:
        features.update(features_override)
    token = {
        "version": 2,
        "tier": tier,
        "licensee": licensee,
        "issued": issued_iso,
        "expires": expires_iso,
        "key_hash": key_hash,
        "max_machines": max_machines,
        "features": features,
    }
    if note:
        token["note"] = note[:200]
    return token


def sign_token(token: dict, priv_key_path: str) -> dict:
    priv = _load_private_key(priv_key_path)
    payload = _canonical_payload(token)
    token["sig"] = _sign_payload(priv, payload)
    return token


def encode_token(token: dict) -> str:
    raw = json.dumps(token, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def decode_token(b64: str) -> dict:
    raw = base64.b64decode(b64, validate=True)
    return json.loads(raw.decode("utf-8"))


def _build_argparser():
    import argparse as ap
    parser = ap.ArgumentParser(
        prog="gen_license.py",
        description="Generate an RSA-signed Accounting Pro license token.",
    )
    parser.add_argument("--tier", choices=TIER_CHOICES, required=True,
                        help="License tier to grant.")
    parser.add_argument("--licensee", required=True,
                        help="Customer / business name (shown in-app).")
    parser.add_argument("--expires", default="annual",
                        help="Expiry: YYYY-MM-DD, Nd (e.g. 30d), Ny, monthly, annual, perpetual (default annual).")
    parser.add_argument("--max-machines", type=int, default=2,
                        help="How many distinct machines may run this license (default 2).")
    parser.add_argument("--note", default="",
                        help="Optional admin note included in the token (max 200 chars).")
    parser.add_argument("--priv-key", default=DEFAULT_PRIV_KEY_PATH,
                        help=f"path to RSA private key (default: {DEFAULT_PRIV_KEY_PATH})")
    parser.add_argument("--out", default="",
                        help="Optional path to also write the token to.")
    parser.add_argument("--show-raw", action="store_true",
                        help="Also print the decoded JSON payload for visual inspection.")
    return parser


def main(argv=None):
    parser = _build_argparser()
    args = parser.parse_args(argv)
    if args.max_machines < 1:
        print("--max-machines must be >= 1", file=sys.stderr)
        return 2

    try:
        token = build_token(
            tier=args.tier,
            licensee=args.licensee,
            expires=args.expires,
            max_machines=args.max_machines,
            note=args.note,
            features_override={},
        )
        token = sign_token(token, args.priv_key)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    b64 = encode_token(token)

    priv = _load_private_key(args.priv_key)
    pub_fp = _public_key_fingerprint(priv.public_key())
    print("# Accounting Pro license token")
    print(f"# tier={args.tier}  licensee={args.licensee!r}  expires={token['expires']}")
    print(f"# max_machines={args.max_machines}  key_hash={token['key_hash'][:12]}...")
    print(f"# public key SHA256 = {pub_fp}")
    print("# paste the line below into Accounting Pro -> Settings -> License -> Activate:")
    print()
    print(b64)
    print()

    if args.show_raw:
        print("# decoded JSON payload:")
        print(json.dumps(token, indent=2, sort_keys=True))
        print()

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(b64 + "\n")
        print(f"# token also written to: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
