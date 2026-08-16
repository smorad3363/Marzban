from scripts.healthcheck import health_targets


def test_internal_health_uses_configured_uvicorn_port():
    internal, public = health_targets({"UVICORN_PORT": "9123"})
    assert internal == "http://127.0.0.1:9123/api/marzhelp/compatibility"
    assert public is None


def test_internal_health_uses_https_when_uvicorn_tls_is_configured():
    internal, public = health_targets(
        {
            "UVICORN_PORT": "443",
            "UVICORN_SSL_CERTFILE": "/certs/fullchain.pem",
            "UVICORN_SSL_KEYFILE": "/certs/key.pem",
        }
    )
    assert internal == "https://127.0.0.1:443/api/marzhelp/compatibility"
    assert public is None


def test_public_https_health_is_derived_from_subscription_prefix():
    internal, public = health_targets(
        {
            "UVICORN_PORT": "8000",
            "XRAY_SUBSCRIPTION_URL_PREFIX": "https://panel.example.com:443/marzban",
        }
    )
    assert internal == "http://127.0.0.1:8000/api/marzhelp/compatibility"
    assert public == "https://panel.example.com:443/marzban/api/marzhelp/compatibility"


def test_explicit_public_health_target_wins():
    _, public = health_targets(
        {
            "XRAY_SUBSCRIPTION_URL_PREFIX": "https://wrong.example.com",
            "HEISENBERG_PUBLIC_HEALTH_URL": "https://right.example.com/health",
        }
    )
    assert public == "https://right.example.com/health"
