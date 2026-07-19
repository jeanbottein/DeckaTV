import asyncio

from tv_driver_sony import bravia
from tv_driver_sony.bravia import PIN_REQUIRED, PinRequired, _cookie, _extract_auth_cookie, _rpc


def test_extract_auth_cookie_handles_expires_comma():
    # A real Set-Cookie carries an Expires date whose comma must not break parsing.
    headers = [
        "auth=ABC123DEF; Path=/sony/; Max-Age=1209600; "
        "Expires=Wed, 09-Jun-2027 10:18:14 GMT; Secure; HttpOnly",
    ]
    assert _extract_auth_cookie(headers) == "auth=ABC123DEF"


def test_extract_auth_cookie_scans_all_headers():
    headers = ["other=x; Path=/", "auth=TOK; Path=/sony/"]
    assert _extract_auth_cookie(headers) == "auth=TOK"


def test_extract_auth_cookie_absent_returns_empty():
    assert _extract_auth_cookie(["session=1; Path=/"]) == ""
    assert _extract_auth_cookie([]) == ""


def test_cookie_reads_from_creds_dict():
    assert _cookie({"cookie": "auth=TOK"}) == "auth=TOK"
    assert _cookie({}) == ""
    assert _cookie(None) == ""
    assert _cookie("nope") == ""


def test_rpc_shape():
    assert _rpc("getPowerStatus") == {
        "method": "getPowerStatus",
        "params": [],
        "id": 1,
        "version": "1.0",
    }
    assert _rpc("setPlayContent", [{"uri": "x"}], "1.1") == {
        "method": "setPlayContent",
        "params": [{"uri": "x"}],
        "id": 1,
        "version": "1.1",
    }


def test_pin_required_carries_the_sentinel_message():
    assert str(PinRequired()) == PIN_REQUIRED


def test_fetch_inputs_maps_uri_and_prefers_label(monkeypatch):
    devices = [
        {"uri": "extInput:hdmi?port=1", "title": "HDMI 1/eARC", "label": "PlayStation"},
        {"uri": "extInput:hdmi?port=2", "title": "HDMI 2", "label": ""},
        {"title": "no uri — skipped", "label": "x"},
    ]

    async def fake_call(host, cookie, service, method, params=None, version="1.0"):
        assert service == "avContent" and method == "getCurrentExternalInputsStatus"
        return [devices]

    monkeypatch.setattr(bravia, "_call", fake_call)
    result = asyncio.run(bravia.fetch_inputs("1.2.3.4", {"cookie": "auth=T"}))
    assert result == [
        {"id": "extInput:hdmi?port=1", "label": "PlayStation"},  # label wins over title
        {"id": "extInput:hdmi?port=2", "label": "HDMI 2"},  # falls back to title
    ]


def test_set_input_skips_when_already_on_target(monkeypatch):
    calls = []

    async def fake_ensure_on(host, cookie):
        return None

    async def fake_call(host, cookie, service, method, params=None, version="1.0"):
        calls.append(method)
        if method == "getPlayingContentInfo":
            return [{"uri": "extInput:hdmi?port=1"}]
        return []

    monkeypatch.setattr(bravia, "_ensure_on", fake_ensure_on)
    monkeypatch.setattr(bravia, "_call", fake_call)
    changed = asyncio.run(bravia.set_input("h", {"cookie": "c"}, "extInput:hdmi?port=1"))
    assert changed is False
    assert "setPlayContent" not in calls


def test_set_input_switches_when_on_other_input(monkeypatch):
    sent = {}

    async def fake_ensure_on(host, cookie):
        return None

    async def fake_call(host, cookie, service, method, params=None, version="1.0"):
        if method == "getPlayingContentInfo":
            return [{"uri": "extInput:hdmi?port=2"}]
        if method == "setPlayContent":
            sent["params"] = params
        return []

    monkeypatch.setattr(bravia, "_ensure_on", fake_ensure_on)
    monkeypatch.setattr(bravia, "_call", fake_call)
    changed = asyncio.run(bravia.set_input("h", {"cookie": "c"}, "extInput:hdmi?port=1"))
    assert changed is True
    assert sent["params"] == [{"uri": "extInput:hdmi?port=1"}]
