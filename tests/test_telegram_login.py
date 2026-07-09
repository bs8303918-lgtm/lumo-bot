import hashlib
import hmac
import json
import time

from services.telegram_login import parse_login_user, verify_login_payload


def test_verify_login_payload_valid():
    bot_token = "123456:ABC-DEF"
    auth_date = int(time.time())
    data = {
        "id": 424242,
        "first_name": "Test",
        "username": "tester",
        "auth_date": auth_date,
    }
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    data["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    assert verify_login_payload(data, bot_token) == 424242
    user = parse_login_user(json.dumps(data), bot_token)
    assert user is not None
    assert user.id == 424242
    assert user.username == "tester"


def test_verify_login_payload_rejects_tampered_hash():
    bot_token = "123456:ABC-DEF"
    data = {
        "id": 1,
        "auth_date": int(time.time()),
        "hash": "deadbeef",
    }
    assert verify_login_payload(data, bot_token) is None
