"""Live TLS and rate-limit checks against a running nginx.

Skipped unless GATEWAY_URL is set. `make test` starts the gateway and
points this at https://nginx.
"""

from __future__ import annotations

import os
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import pytest
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pytestmark = [
    pytest.mark.gateway,
    pytest.mark.filterwarnings(
        "ignore:Unverified HTTPS request is being made:urllib3.exceptions.InsecureRequestWarning"
    ),
]

GATEWAY_URL = os.environ.get("GATEWAY_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def gateway_url() -> str:
    if not GATEWAY_URL:
        pytest.skip("Set GATEWAY_URL to run live nginx tests (`make test-gateway`).")

    parsed = urlparse(GATEWAY_URL)
    host = parsed.hostname or "nginx"
    port = parsed.port or 443
    deadline = time.time() + 30
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return GATEWAY_URL
        except OSError as exc:
            last_error = exc
            time.sleep(1)
    raise AssertionError(f"nginx did not accept TLS on {host}:{port}: {last_error}")


@pytest.fixture(scope="module")
def gateway_ready(gateway_url: str) -> str:
    deadline = time.time() + 45
    last: object = None
    while time.time() < deadline:
        try:
            response = requests.get(gateway_url + "/health", verify=False, timeout=5)
            if response.status_code == 200:
                return gateway_url
            last = response.status_code
        except requests.RequestException as exc:
            last = exc
        time.sleep(1)
    raise AssertionError(f"/health through nginx never returned 200: {last}")


def test_http_redirects_to_https(gateway_url: str) -> None:
    http_url = gateway_url.replace("https://", "http://", 1) + "/health"
    response = requests.get(http_url, allow_redirects=False, timeout=5)

    assert response.status_code == 301
    assert response.headers["Location"].startswith("https://")


def test_https_handshake_is_tls_1_2_or_1_3(gateway_url: str) -> None:
    parsed = urlparse(gateway_url)
    host = parsed.hostname or "nginx"
    port = parsed.port or 443
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.create_connection((host, port), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            assert tls.version() in {"TLSv1.2", "TLSv1.3"}


def test_https_sets_hsts(gateway_url: str) -> None:
    response = requests.get(gateway_url + "/", verify=False, timeout=5)

    assert "strict-transport-security" in {key.lower() for key in response.headers}


def test_health_through_gateway(gateway_ready: str) -> None:
    response = requests.get(gateway_ready + "/health", verify=False, timeout=5)
    body = response.json()

    assert response.status_code == 200
    assert "status" in body


def test_predict_without_auth_is_401(gateway_ready: str) -> None:
    response = requests.post(
        gateway_ready + "/predict",
        json={
            "location": "Sydney",
            "rainfall": 0.0,
            "humidity_3pm": 30.0,
            "pressure_3pm": 1015.0,
        },
        verify=False,
        timeout=10,
    )

    assert response.status_code == 401


def test_burst_returns_429(gateway_url: str) -> None:
    url = gateway_url + "/"

    def hit() -> int:
        return requests.get(url, verify=False, timeout=5).status_code

    with ThreadPoolExecutor(max_workers=32) as pool:
        statuses = [future.result() for future in [pool.submit(hit) for _ in range(60)]]

    assert 429 in statuses, f"expected a 429 from the rate limiter, got {sorted(set(statuses))}"
