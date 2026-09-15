from collections.abc import Callable, Sequence
from os import environ
from urllib.parse import urlparse

from weather_mlops.config.settings import settings

SecretFetcher = Callable[[str], str | None]

# Local .env only needs SUPABASE_URL + SUPABASE_KEY. Everything else is stored
# in Supabase Vault under the same names and loaded at process start.
BOOTSTRAP_ENV = ("SUPABASE_URL", "SUPABASE_KEY")
AUTH_SETTINGS = (
    ("API_AUTH_USER", "api_auth_user"),
    ("API_AUTH_PASSWORD", "api_auth_password"),
)
S3_SETTINGS = (
    ("AWS_ACCESS_KEY_ID", "aws_access_key_id"),
    ("AWS_SECRET_ACCESS_KEY", "aws_secret_access_key"),
)
VAULT_SETTINGS = AUTH_SETTINGS + S3_SETTINGS

_client = None


class VaultError(Exception):
    """Vault RPC failed. Distinct from a secret that is simply absent."""


def derive_s3_endpoint(supabase_url: str) -> str:
    hostname = urlparse(supabase_url).hostname or ""
    project_ref = hostname.split(".")[0]
    if not project_ref:
        raise ValueError(f"Cannot derive Storage S3 endpoint from {supabase_url}")
    return f"https://{project_ref}.storage.supabase.co/storage/v1/s3"


def resolve_secret(
    name: str,
    *,
    default: str | None = None,
    fetcher: SecretFetcher | None = None,
) -> str | None:
    """Resolve a secret from the process environment, then optional Vault fetcher.

    Frontend / Streamlit code must never call this helper.
    """

    env_value = environ.get(name)
    if env_value:
        return env_value
    if fetcher is not None:
        fetched = fetcher(name)
        if fetched:
            return fetched
    return default


def _supabase_client():
    global _client
    if not settings.supabase_url or not settings.supabase_key:
        return None
    if _client is None:
        from supabase import create_client

        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def default_vault_fetcher(name: str) -> str | None:
    """Read a named secret through the service-role RPC `public.get_app_secret`."""

    client = _supabase_client()
    if client is None:
        return None
    try:
        response = client.rpc("get_app_secret", {"secret_name": name}).execute()
    except Exception as exc:
        raise VaultError(f"Vault RPC failed while reading {name}") from exc
    data = response.data
    if isinstance(data, str) and data:
        return data
    return None


def hydrate_runtime_secrets(
    *,
    fetcher: SecretFetcher | None = None,
    names: Sequence[str] | None = None,
    required: Sequence[str] = (),
) -> None:
    """Fill settings and os.environ from Vault (or env fallback).

    Pass `names` to fetch only what this process needs. Missing *required*
    names raise VaultError after hydration. This is a startup snapshot: rotate
    a Vault secret, then restart the process.
    """

    if settings.supabase_url and not settings.supabase_s3_endpoint:
        settings.supabase_s3_endpoint = derive_s3_endpoint(settings.supabase_url)

    wanted = None if names is None else set(names)
    active_fetcher = fetcher if fetcher is not None else default_vault_fetcher
    for env_name, attr in VAULT_SETTINGS:
        if wanted is not None and env_name not in wanted:
            continue
        current = getattr(settings, attr)
        if current:
            environ.setdefault(env_name, current)
            continue
        value = resolve_secret(env_name, fetcher=active_fetcher)
        if value:
            setattr(settings, attr, value)
            environ[env_name] = value

    missing = [name for name in required if not environ.get(name)]
    if missing:
        joined = ", ".join(missing)
        raise VaultError(f"Required secrets are missing: {joined}")
