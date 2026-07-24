"""Unit tests for the SSAP request/power-off flow, driven against a fake socket.

No `websockets` and no pytest-asyncio in the test env, so the client's socket is injected
directly and coroutines are driven with asyncio.run.
"""

import asyncio
import json
import time

import pytest

from tv_driver_lg import webos
from tv_driver_lg.webos import WebOSClient, WebOSError


class FakeSocket:
    """Replays queued replies; a queued exception is raised instead of returning."""

    def __init__(self, replies=()):
        self.sent = []
        self._replies = list(replies)

    async def send(self, text):
        self.sent.append(json.loads(text))

    async def recv(self):
        if not self._replies:
            await asyncio.sleep(3600)  # the TV died mid-command and will never answer
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply)

    async def close(self):
        return None


def _client(replies=()):
    client = WebOSClient("tv.lan")
    client._socket = FakeSocket(replies)
    return client


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _fast_ack(monkeypatch):
    monkeypatch.setattr(webos, "POWER_OFF_ACK_TIMEOUT", 0.01)


def test_power_off_sends_the_turn_off_request():
    client = _client([{"id": "req-1", "type": "response", "payload": {}}])
    _run(client.power_off())
    assert client._socket.sent[0]["uri"] == "ssap://system/turnOff"


def test_power_off_succeeds_when_the_tv_acknowledges():
    client = _client([{"id": "req-1", "type": "response", "payload": {}}])
    _run(client.power_off())


def test_power_off_succeeds_when_the_tv_dies_without_replying():
    # The usual case: the TV powers off mid-command, so no ack ever arrives.
    _run(_client().power_off())


def test_power_off_succeeds_when_the_tv_drops_the_socket():
    _run(_client([OSError("connection reset")]).power_off())


def test_power_off_gives_up_on_the_ack_well_before_the_request_timeout():
    # The silent case must not block the UI for the full REQUEST_TIMEOUT.
    start = time.monotonic()
    _run(_client().power_off())
    assert time.monotonic() - start < webos.REQUEST_TIMEOUT


def test_power_off_propagates_a_protocol_error():
    # e.g. CONTROL_POWER missing because the TV was paired before that permission existed.
    client = _client([{"id": "req-1", "type": "error", "error": "401 insufficient permissions"}])
    with pytest.raises(WebOSError):
        _run(client.power_off())


def test_power_off_propagates_an_unexpected_error():
    # A bug in our own code must not masquerade as a successful power-off.
    with pytest.raises(TypeError):
        _run(_client([TypeError("boom")]).power_off())


def test_volume_up_sends_the_volume_up_request():
    client = _client([{"id": "req-1", "type": "response", "payload": {}}])
    _run(client.volume_up())
    assert client._socket.sent[0]["uri"] == "ssap://audio/volumeUp"


def test_volume_down_sends_the_volume_down_request():
    client = _client([{"id": "req-1", "type": "response", "payload": {}}])
    _run(client.volume_down())
    assert client._socket.sent[0]["uri"] == "ssap://audio/volumeDown"


def test_request_ignores_replies_for_another_id():
    client = _client([
        {"id": "other", "type": "response", "payload": {"ignored": True}},
        {"id": "req-1", "type": "response", "payload": {"ok": True}},
    ])
    assert _run(client._request("ssap://test")) == {"ok": True}
