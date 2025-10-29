"""Configuration management with simple encryption."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


CONFIG_DIR = Path("config")
CONFIG_PATH = CONFIG_DIR / "user_config.json"
CONFIG_SECRET = "capstone-local-secret"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(exist_ok=True)


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _encrypt(value: Dict[str, Any], secret: str = CONFIG_SECRET) -> str:
    payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
    key = _derive_key(secret)
    encrypted = _xor_bytes(payload, key)
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def _decrypt(token: str, secret: str = CONFIG_SECRET) -> Dict[str, Any]:
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    key = _derive_key(secret)
    decrypted = _xor_bytes(raw, key)
    return json.loads(decrypted.decode("utf-8"))


@dataclass
class ConsentState:
    granted: bool
    decision: str
    timestamp: str
    source: str = "cli"


@dataclass
class Preferences:
    last_opened_path: str | None = None
    analysis_mode: str = "local"
    theme: str = "light"
    labels: Dict[str, str] = field(default_factory=lambda: {"local_mode": "Local Analysis Mode"})


@dataclass
class Config:
    consent: ConsentState
    preferences: Preferences


_DEFAULT_CONFIG = Config(
    consent=ConsentState(granted=False, decision="deny", timestamp=datetime.now(timezone.utc).isoformat()),
    preferences=Preferences(),
)


def load_config() -> Config:
    _ensure_config_dir()
    if not CONFIG_PATH.exists():
        save_config(_DEFAULT_CONFIG)
        return _DEFAULT_CONFIG

    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        stored = json.load(fh)

    consent_data = stored.get("consent")
    preferences_data = stored.get("preferences")

    if isinstance(consent_data, str):
        consent = ConsentState(**_decrypt(consent_data))
    else:
        consent = ConsentState(**consent_data)

    if isinstance(preferences_data, str):
        preferences = Preferences(**_decrypt(preferences_data))
    else:
        preferences = Preferences(**preferences_data)

    return Config(consent=consent, preferences=preferences)


def save_config(config: Config) -> None:
    _ensure_config_dir()
    payload = {
        "consent": _encrypt(config.consent.__dict__),
        "preferences": _encrypt(config.preferences.__dict__),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def update_consent(granted: bool, decision: str, source: str = "cli") -> Config:
    config = load_config()
    config.consent = ConsentState(
        granted=granted,
        decision=decision,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
    )
    save_config(config)
    return config


def update_preferences(**kwargs: Any) -> Config:
    config = load_config()
    for key, value in kwargs.items():
        if hasattr(config.preferences, key):
            setattr(config.preferences, key, value)
    save_config(config)
    return config
