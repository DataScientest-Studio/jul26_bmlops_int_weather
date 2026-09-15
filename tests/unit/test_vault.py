from os import environ

import pytest

from weather_mlops.config.settings import settings
from weather_mlops.security.vault import (
    VAULT_SETTINGS,
    VaultError,
    derive_s3_endpoint,
    hydrate_runtime_secrets,
    resolve_secret,
)


def test_resolve_secret_prefers_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPEN_METEO_TOKEN", "from-env")

    value = resolve_secret("OPEN_METEO_TOKEN", fetcher=lambda _name: "from-vault")

    assert value == "from-env"


def test_resolve_secret_uses_fetcher_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)

    value = resolve_secret(
        "AWS_ACCESS_KEY_ID",
        fetcher=lambda name: f"vault:{name}",
    )

    assert value == "vault:AWS_ACCESS_KEY_ID"


def test_resolve_secret_returns_default_when_nothing_configured(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_SECRET", raising=False)

    assert resolve_secret("MISSING_SECRET", default="fallback") == "fallback"
    assert resolve_secret("MISSING_SECRET") is None


def test_resolve_secret_does_not_call_fetcher_when_env_is_set(monkeypatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "env-key")
    calls: list[str] = []

    def fetcher(name: str) -> str:
        calls.append(name)
        return "vault-key"

    assert resolve_secret("AWS_ACCESS_KEY_ID", fetcher=fetcher) == "env-key"
    assert calls == []


def test_derive_s3_endpoint_from_project_url() -> None:
    endpoint = derive_s3_endpoint("https://fgxgenjxslytnqygpefk.supabase.co")

    assert endpoint == "https://fgxgenjxslytnqygpefk.storage.supabase.co/storage/v1/s3"


def test_hydrate_runtime_secrets_fills_missing_settings_from_vault(monkeypatch) -> None:
    monkeypatch.setattr(settings, "supabase_url", "https://fgxgenjxslytnqygpefk.supabase.co")
    monkeypatch.setattr(settings, "supabase_s3_endpoint", None)
    monkeypatch.setattr(settings, "aws_access_key_id", None)
    monkeypatch.setattr(settings, "aws_secret_access_key", None)
    monkeypatch.setattr(settings, "api_auth_user", None)
    monkeypatch.setattr(settings, "api_auth_password", None)
    for env_name, _attr in VAULT_SETTINGS:
        monkeypatch.delenv(env_name, raising=False)

    hydrate_runtime_secrets(fetcher=lambda name: f"vault-{name}")

    assert settings.supabase_s3_endpoint.endswith("/storage/v1/s3")
    assert settings.aws_access_key_id == "vault-AWS_ACCESS_KEY_ID"
    assert settings.aws_secret_access_key == "vault-AWS_SECRET_ACCESS_KEY"
    assert settings.api_auth_user == "vault-API_AUTH_USER"
    assert settings.api_auth_password == "vault-API_AUTH_PASSWORD"
    assert environ["API_AUTH_USER"] == "vault-API_AUTH_USER"
    assert environ["API_AUTH_PASSWORD"] == "vault-API_AUTH_PASSWORD"


def test_hydrate_runtime_secrets_can_limit_names(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_auth_user", None)
    monkeypatch.setattr(settings, "api_auth_password", None)
    monkeypatch.setattr(settings, "aws_access_key_id", None)
    monkeypatch.delenv("API_AUTH_USER", raising=False)
    monkeypatch.delenv("API_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    fetched: list[str] = []

    def fetcher(name: str) -> str:
        fetched.append(name)
        return f"vault-{name}"

    hydrate_runtime_secrets(fetcher=fetcher, names=("API_AUTH_USER", "API_AUTH_PASSWORD"))

    assert set(fetched) == {"API_AUTH_USER", "API_AUTH_PASSWORD"}
    assert settings.api_auth_user == "vault-API_AUTH_USER"
    assert settings.aws_access_key_id is None


def test_default_vault_fetcher_raises_on_rpc_failure(monkeypatch) -> None:
    class BoomClient:
        def rpc(self, *_args, **_kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_key", "service-role")
    monkeypatch.setattr("weather_mlops.security.vault._client", BoomClient())

    from weather_mlops.security.vault import default_vault_fetcher

    with pytest.raises(VaultError, match="Vault RPC failed"):
        default_vault_fetcher("API_AUTH_USER")


def test_hydrate_runtime_secrets_requires_named_secrets(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_auth_user", None)
    monkeypatch.setattr(settings, "api_auth_password", None)
    monkeypatch.delenv("API_AUTH_USER", raising=False)
    monkeypatch.delenv("API_AUTH_PASSWORD", raising=False)

    with pytest.raises(VaultError, match="API_AUTH_USER"):
        hydrate_runtime_secrets(
            fetcher=lambda _name: None,
            names=("API_AUTH_USER",),
            required=("API_AUTH_USER",),
        )
