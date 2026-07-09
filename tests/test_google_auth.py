"""Tests for Google Sign-In helpers."""

import hashlib

from services.google_auth import google_telegram_id


def test_google_telegram_id_is_stable_and_negative():
    sub = "google-oauth2|123456789"
    a = google_telegram_id(sub)
    b = google_telegram_id(sub)
    assert a == b
    assert a < 0
    assert abs(a) > 9_000_000_000_000_000
