from services.url_utils import (
    is_valid_webapp_url,
    safe_button_url,
    safe_webapp_url,
)


def test_railway_app_url_rejected_for_webapp():
    url = "https://lumo-bot-production-9903.up.railway.app/app"
    assert is_valid_webapp_url(url) is False
    assert safe_webapp_url(url) == ""


def test_vercel_webapp_accepted():
    url = "https://lumo-mini.vercel.app"
    assert safe_webapp_url(url) == url


def test_placeholder_checkout_rejected():
    assert safe_button_url("https://startify.example/lumo/checkout") == ""


def test_tme_community_link_ok():
    url = "https://t.me/+hA0CwgbStLI0MGRi"
    assert safe_button_url(url) == url
