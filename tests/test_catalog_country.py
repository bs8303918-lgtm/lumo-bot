"""Tests for catalog country normalization."""

from services.catalog_country import (
    DEFAULT_COUNTRY,
    normalize_country,
    resolve_catalog_country,
)


def test_normalize_global_variants():
    assert normalize_country("global") == DEFAULT_COUNTRY
    assert normalize_country("для всех") == DEFAULT_COUNTRY
    assert normalize_country("Worldwide") == DEFAULT_COUNTRY
    assert normalize_country(None) == DEFAULT_COUNTRY


def test_normalize_known_countries():
    assert normalize_country("KZ") == "Казахстан"
    assert normalize_country("Kazakhstan") == "Казахстан"
    assert normalize_country("кыргызстан") == "Кыргызстан"
    assert normalize_country("Uzbekistan residents") == "Узбекистан"


def test_resolve_prefers_llm():
    assert (
        resolve_catalog_country(
            "Корея",
            channel_identifier="myextrakz",
            title="SNU scholarship",
        )
        == "Корея"
    )


def test_resolve_falls_back_to_channel():
    assert (
        resolve_catalog_country(
            None,
            channel_identifier="kgworkzone",
            title="Job post",
        )
        == "Кыргызстан"
    )


def test_resolve_defaults_global():
    assert resolve_catalog_country(None, channel_identifier="random_channel") == DEFAULT_COUNTRY
