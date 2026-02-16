import os

from packages.address_core.trusted_fengtu import FengtuTrustedClient


def test_fengtu_client_disabled_by_default() -> None:
    os.environ.pop("ADDRESS_TRUSTED_FENGTU_ENABLED", None)
    client = FengtuTrustedClient()
    assert client.enabled() is True


def test_fengtu_client_can_be_disabled_explicitly() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "0"
    client = FengtuTrustedClient()
    assert client.enabled() is False
    assert client.standardize("上海市浦东新区世纪大道8号") is None


def test_fengtu_client_disabled_returns_none_on_real_check() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "0"
    client = FengtuTrustedClient()
    assert client.is_real_address("广东省深圳市罗湖区不存在路64号") is None


def test_fengtu_network_error_requires_user_confirmation() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "1"
    os.environ.pop("ADDRESS_TRUSTED_FENGTU_NETWORK_CONFIRM", None)
    FengtuTrustedClient._network_confirmation_required = True
    FengtuTrustedClient._last_network_error = "TimeoutError"
    FengtuTrustedClient._network_confirmed_once = False
    FengtuTrustedClient._last_confirm_by = ""

    client = FengtuTrustedClient()
    blocked = client.call("address_real_check", {"address": "上海市浦东新区世纪大道8号"})
    assert blocked.get("ok") is False
    assert str(blocked.get("reason", "")).startswith("await_user_confirmation")

    os.environ["ADDRESS_TRUSTED_FENGTU_NETWORK_CONFIRM"] = "1"
    resumed = client.call("address_real_check", {"address": "上海市浦东新区世纪大道8号"})
    assert str(resumed.get("reason", "")).startswith("await_user_confirmation") is False
