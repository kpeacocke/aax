"""Guard the external EDA callback and token-refresh reverse-proxy routes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gateway_maps_eda_generated_paths_to_the_correct_services() -> None:
    config = (ROOT / "images/gateway/nginx.conf").read_text()

    assert "location ^~ /eda/ws/api/eda/ws/" in config
    assert "rewrite ^/eda/ws(/api/eda/ws/.*)$ $1 break;" in config
    assert "set $upstream_eda_ws http://eda-ws:8000;" in config
    assert config.index("set $upstream_eda_ws") < config.index(
        "rewrite ^/eda/ws(/api/eda/ws/.*)$"
    )
    assert "location ^~ /eda/ws/api/eda/v1/" in config
    assert "rewrite ^/eda/ws(/api/eda/v1/.*)$ $1 break;" in config
    assert "set $upstream_eda_api http://eda-controller:5000;" in config
    assert config.index("set $upstream_eda_api") < config.index(
        "rewrite ^/eda/ws(/api/eda/v1/.*)$"
    )
