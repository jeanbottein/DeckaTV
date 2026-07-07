import base64

import pytest

from tv_driver_samsung_tizen import remote


def test_ws_url_secure_port_uses_wss_and_base64_name():
    url = remote.ws_url("192.168.1.20", remote.SECURE_PORT, "")
    name = base64.b64encode(remote.APP_NAME.encode()).decode()
    assert url == f"wss://192.168.1.20:8002/api/v2/channels/samsung.remote.control?name={name}"


def test_ws_url_appends_token_when_present():
    url = remote.ws_url("192.168.1.20", remote.SECURE_PORT, "12345678")
    assert url.endswith("&token=12345678")


def test_ws_url_open_port_uses_plain_ws_without_token():
    url = remote.ws_url("192.168.1.20", remote.OPEN_PORT, "")
    assert url.startswith("ws://192.168.1.20:8001/")


def test_key_message_wraps_key_in_remote_control_click():
    message = remote.key_message("KEY_HDMI1")
    assert message == {
        "method": "ms.remote.control",
        "params": {
            "Cmd": "Click",
            "DataOfCmd": "KEY_HDMI1",
            "Option": "false",
            "TypeOfRemote": "SendRemoteKey",
        },
    }


def test_token_from_event_returns_token_on_connect():
    event = {"event": "ms.channel.connect", "data": {"token": "12345678"}}
    assert remote.token_from_event(event) == "12345678"


def test_token_from_event_tolerates_missing_token():
    assert remote.token_from_event({"event": "ms.channel.connect", "data": {}}) == ""


def test_token_from_event_raises_when_tv_denies_pairing():
    with pytest.raises(remote.TizenError):
        remote.token_from_event({"event": "ms.channel.unauthorized"})


def test_token_from_event_raises_on_unexpected_event():
    with pytest.raises(remote.TizenError):
        remote.token_from_event({"event": "ms.channel.timeOut"})
