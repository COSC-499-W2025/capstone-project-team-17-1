"""Configuration management with simple encryption."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, dataclass, field
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
    user_id: str = "default-local-user"
    external_permissions: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Config:
    consent: ConsentState
    preferences: Preferences


_REQUIRED_CONSENT_FIELDS = {"granted", "decision", "timestamp", "source"}
_REQUIRED_PREFERENCE_FIELDS = {"last_opened_path", "analysis_mode", "theme", "labels"}


def _default_preferences_dict() -> Dict[str, Any]:
    defaults = asdict(Preferences())
    defaults["labels"] = dict(defaults.get("labels", {}))
    defaults["external_permissions"] = dict(defaults.get("external_permissions", {}))
    return defaults


def _fresh_default_config() -> Config:
    return Config(
        consent=ConsentState(
            granted=False,
            decision="deny",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
        preferences=Preferences(),
    )


_DEFAULT_CONFIG = _fresh_default_config()


def validate_config_shape(payload: Dict[str, Any]) -> None:
    """Validate that an on-disk payload contains the expected encrypted shape."""

    if not isinstance(payload, dict):
        raise ValueError("Configuration payload must be an object")

    required_top_level = {"consent", "preferences"}
    missing_keys = required_top_level - payload.keys()
    if missing_keys:
        raise ValueError(f"Configuration payload missing keys: {sorted(missing_keys)}")

    consent_blob = payload.get("consent")
    preferences_blob = payload.get("preferences")

    if not isinstance(consent_blob, str) or not isinstance(preferences_blob, str):
        raise ValueError("Configuration values must be encrypted strings")

    consent_data = _decrypt(consent_blob)
    preferences_data = _decrypt(preferences_blob)

    if not _REQUIRED_CONSENT_FIELDS <= consent_data.keys():
        raise ValueError("Consent payload missing required fields")
    if not _REQUIRED_PREFERENCE_FIELDS <= preferences_data.keys():
        raise ValueError("Preferences payload missing required fields")

    pref_defaults = _default_preferences_dict()
    for key, default in pref_defaults.items():
        preferences_data.setdefault(key, default)

    for key in _REQUIRED_CONSENT_FIELDS:
        if key not in consent_data:
            raise ValueError("Consent payload missing required fields")


def load_config() -> Config:
    _ensure_config_dir()
    if not CONFIG_PATH.exists():
        default = _fresh_default_config()
        save_config(default)
        return default

    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        stored = json.load(fh)

    if isinstance(stored, dict):
        validate_config_shape(stored)

    consent_data = stored.get("consent")
    preferences_data = stored.get("preferences")

    if isinstance(consent_data, str):
        consent_payload = _decrypt(consent_data)
        defaults = _DEFAULT_CONFIG.consent.__dict__
        for key, default in defaults.items():
            consent_payload.setdefault(key, default)
        consent = ConsentState(**consent_payload)
    else:
        consent = ConsentState(**consent_data)

    if isinstance(preferences_data, str):
        preferences_payload = _decrypt(preferences_data)
        pref_defaults = _default_preferences_dict()
        for key, default in pref_defaults.items():
            if key not in preferences_payload:
                value = default if not isinstance(default, dict) else dict(default)
                preferences_payload[key] = value
        preferences = Preferences(**preferences_payload)
    else:
        pref_defaults = _default_preferences_dict()
        merged = {**pref_defaults, **preferences_data}
        preferences = Preferences(**merged)
        preferences = Preferences(**payload)

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


def reset_config() -> Config:
    """Restore default configuration values on disk."""

    default = _fresh_default_config()
    save_config(default)
    return default


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
