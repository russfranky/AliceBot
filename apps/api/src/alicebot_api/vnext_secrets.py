from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from typing import Protocol

from alicebot_api.vnext_repositories import JsonObject


DEFAULT_SECRET_DIR = Path("~/.alicebot/vnext-secrets").expanduser()
DEFAULT_SECRET_FILE = DEFAULT_SECRET_DIR / "secrets.json"
DEFAULT_KEY_FILE = DEFAULT_SECRET_DIR / "local.key"
SECRET_STORE_KEY_ENV = "ALICE_VNEXT_SECRET_STORE_KEY"


class VNextSecretError(ValueError):
    """Raised when a vNext connector secret cannot be stored or resolved."""


class SecretProvider(Protocol):
    def get_secret(self, secret_ref: str) -> str | None: ...

    def set_secret(self, secret_ref: str, secret_value: str) -> None: ...

    def has_secret(self, secret_ref: str) -> bool: ...


def redact_secret_text(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def is_secret_key(key: str) -> bool:
    normalized = key.casefold()
    return any(marker in normalized for marker in ("token", "secret", "password", "credential", "api_key"))


def redact_secret_fields(value: object) -> object:
    if isinstance(value, dict):
        redacted: JsonObject = {}
        for key, item in value.items():
            if is_secret_key(str(key)):
                redacted[str(key)] = "***"
            else:
                redacted[str(key)] = redact_secret_fields(item)
        return redacted
    if isinstance(value, list):
        return [redact_secret_fields(item) for item in value]
    return value


@dataclass(slots=True)
class EnvironmentSecretProvider:
    """Resolve refs such as env:TELEGRAM_BOT_TOKEN without persisting values."""

    def get_secret(self, secret_ref: str) -> str | None:
        if not secret_ref.startswith("env:"):
            return None
        env_name = secret_ref.removeprefix("env:").strip()
        if not env_name:
            return None
        return os.environ.get(env_name)

    def set_secret(self, secret_ref: str, secret_value: str) -> None:
        if not secret_ref.startswith("env:"):
            return
        env_name = secret_ref.removeprefix("env:").strip()
        if env_name:
            os.environ[env_name] = secret_value

    def has_secret(self, secret_ref: str) -> bool:
        return self.get_secret(secret_ref) is not None


class LocalEncryptedFileSecretProvider:
    """Small local encrypted-file fallback for alpha connector secrets.

    The key is read from ALICE_VNEXT_SECRET_STORE_KEY or generated into a local
    user-only key file. This is intentionally isolated behind the provider
    interface so it can be replaced with Keychain/libsecret later.
    """

    def __init__(self, *, path: Path = DEFAULT_SECRET_FILE, key_path: Path = DEFAULT_KEY_FILE) -> None:
        self.path = path
        self.key_path = key_path

    def _key(self) -> bytes:
        configured = os.environ.get(SECRET_STORE_KEY_ENV)
        if configured:
            return hashlib.sha256(configured.encode("utf-8")).digest()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.key_path.exists():
            self.key_path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
            self.key_path.chmod(0o600)
        return hashlib.sha256(self.key_path.read_text(encoding="utf-8").strip().encode("utf-8")).digest()

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VNextSecretError("vNext local secret store is unreadable") from exc
        if not isinstance(loaded, dict):
            raise VNextSecretError("vNext local secret store is invalid")
        return {str(key): str(value) for key, value in loaded.items() if isinstance(value, str)}

    def _save(self, entries: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(entries, indent=2, sort_keys=True), encoding="utf-8")
        self.path.chmod(0o600)

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        key = self._key()
        output = bytearray()
        counter = 0
        while len(output) < length:
            output.extend(hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
            counter += 1
        return bytes(output[:length])

    def _encrypt(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        nonce = secrets.token_bytes(16)
        ciphertext = bytes(left ^ right for left, right in zip(raw, self._keystream(nonce, len(raw)), strict=True))
        mac = hmac.new(self._key(), nonce + ciphertext, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(nonce + mac + ciphertext).decode("ascii")

    def _decrypt(self, encoded: str) -> str:
        try:
            raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
        except Exception as exc:
            raise VNextSecretError("vNext local secret entry is invalid") from exc
        if len(raw) < 48:
            raise VNextSecretError("vNext local secret entry is truncated")
        nonce = raw[:16]
        mac = raw[16:48]
        ciphertext = raw[48:]
        expected = hmac.new(self._key(), nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            raise VNextSecretError("vNext local secret entry failed integrity check")
        plaintext = bytes(left ^ right for left, right in zip(ciphertext, self._keystream(nonce, len(ciphertext)), strict=True))
        return plaintext.decode("utf-8")

    def get_secret(self, secret_ref: str) -> str | None:
        if secret_ref.startswith("env:"):
            return None
        entries = self._load()
        encoded = entries.get(secret_ref)
        if encoded is None:
            return None
        return self._decrypt(encoded)

    def set_secret(self, secret_ref: str, secret_value: str) -> None:
        if secret_ref.startswith("env:"):
            return
        if not secret_ref.strip():
            raise VNextSecretError("secret_ref is required")
        entries = self._load()
        entries[secret_ref] = self._encrypt(secret_value)
        self._save(entries)

    def has_secret(self, secret_ref: str) -> bool:
        if secret_ref.startswith("env:"):
            return False
        return secret_ref in self._load()


@dataclass(slots=True)
class CompositeSecretProvider:
    providers: tuple[SecretProvider, ...]

    def get_secret(self, secret_ref: str) -> str | None:
        for provider in self.providers:
            value = provider.get_secret(secret_ref)
            if value is not None:
                return value
        return None

    def set_secret(self, secret_ref: str, secret_value: str) -> None:
        for provider in self.providers:
            if secret_ref.startswith("env:") and isinstance(provider, EnvironmentSecretProvider):
                provider.set_secret(secret_ref, secret_value)
                return
            if not secret_ref.startswith("env:") and isinstance(provider, LocalEncryptedFileSecretProvider):
                provider.set_secret(secret_ref, secret_value)
                return
        raise VNextSecretError(f"no vNext secret provider can write {secret_ref}")

    def has_secret(self, secret_ref: str) -> bool:
        return any(provider.has_secret(secret_ref) for provider in self.providers)


class InMemorySecretProvider:
    def __init__(self, entries: dict[str, str] | None = None) -> None:
        self.entries = dict(entries or {})

    def get_secret(self, secret_ref: str) -> str | None:
        return self.entries.get(secret_ref)

    def set_secret(self, secret_ref: str, secret_value: str) -> None:
        self.entries[secret_ref] = secret_value

    def has_secret(self, secret_ref: str) -> bool:
        return secret_ref in self.entries


def default_secret_provider() -> SecretProvider:
    return CompositeSecretProvider((EnvironmentSecretProvider(), LocalEncryptedFileSecretProvider()))


__all__ = [
    "CompositeSecretProvider",
    "DEFAULT_KEY_FILE",
    "DEFAULT_SECRET_FILE",
    "EnvironmentSecretProvider",
    "InMemorySecretProvider",
    "LocalEncryptedFileSecretProvider",
    "SECRET_STORE_KEY_ENV",
    "SecretProvider",
    "VNextSecretError",
    "default_secret_provider",
    "is_secret_key",
    "redact_secret_fields",
    "redact_secret_text",
]
