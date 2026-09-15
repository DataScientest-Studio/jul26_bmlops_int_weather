from weather_mlops.api.http import tls_verify


def test_tls_verify_skips_only_local_https_hosts() -> None:
    assert tls_verify("https://nginx/predict") is False
    assert tls_verify("https://localhost/docs") is False
    assert tls_verify("https://127.0.0.1/health") is False
    assert tls_verify("http://nginx/health") is True


def test_tls_verify_keeps_remote_https() -> None:
    assert tls_verify("https://mlflow.example.com") is True
    assert tls_verify("https://api.supabase.co") is True
