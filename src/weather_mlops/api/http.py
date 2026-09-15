"""HTTP helpers for the local Compose network."""

from urllib.parse import urlparse

import urllib3

_LOCAL_TLS_HOSTS = {"nginx", "localhost", "127.0.0.1", "::1"}


def tls_verify(url: str) -> bool:
    """Skip certificate checks only for the local Compose Nginx.

    The published gateway uses a self-signed cert generated inside the
    Nginx container, so there is no host CA to trust. Remote HTTPS URLs
    keep verification on.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return True
    host = (parsed.hostname or "").lower()
    if host not in _LOCAL_TLS_HOSTS:
        return True
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return False
