from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NGINX_CONF = (PROJECT_ROOT / "docker" / "nginx" / "nginx.conf").read_text()


def test_nginx_redirects_http_to_https() -> None:
    assert "listen 80;" in NGINX_CONF
    assert "return 301 https://$host$request_uri;" in NGINX_CONF


def test_nginx_terminates_tls_and_proxies_the_api() -> None:
    assert "listen 443 ssl;" in NGINX_CONF
    assert "proxy_pass http://api_upstream;" in NGINX_CONF
    assert "server api:8000;" in NGINX_CONF


def test_nginx_sets_security_headers_and_rate_limits() -> None:
    assert "limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;" in NGINX_CONF
    assert "limit_req_zone $binary_remote_addr zone=train:10m rate=1r/s;" in NGINX_CONF
    assert "Strict-Transport-Security" in NGINX_CONF
    assert "X-Content-Type-Options nosniff" in NGINX_CONF
    assert "client_max_body_size 2m;" in NGINX_CONF
    assert "limit_req_status 429;" in NGINX_CONF


def test_nginx_allows_swagger_assets_on_docs() -> None:
    assert "location /docs" in NGINX_CONF
    assert "cdn.jsdelivr.net" in NGINX_CONF


def test_nginx_does_not_expose_mlflow_or_airflow() -> None:
    assert "5000" not in NGINX_CONF
    assert "airflow" not in NGINX_CONF.lower()
