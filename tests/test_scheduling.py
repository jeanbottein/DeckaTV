"""Unit tests for the auto-switch queue: which displays get queued, when an attempt may
run, and the post-switch debounce. Pure bookkeeping — no store, driver, or network."""

import asyncio

import pytest

import main
from main import APPLY_BUDGET_SECONDS, COOLDOWN_SECONDS


class FakeStore:
    def __init__(self, rules, pause_when_streaming=True, triggers=()):
        self.rules = rules
        self.pause_when_streaming = pause_when_streaming
        self._triggers = dict(triggers)

    def trigger_enabled(self, name):
        return self._triggers.get(name, True)


def _rule(display_id, enabled=True):
    return {"display_id": display_id, "host": "tv.lan", "input_id": "HDMI_1", "enabled": enabled}


@pytest.fixture
def plugin():
    instance = main.Plugin()
    instance.pending = {}
    instance.last_success = {}
    instance.seen = set()
    instance.inflight = set()
    instance.streaming = False
    instance._resumed = False
    instance.store = FakeStore([])
    return instance


@pytest.fixture
def one_connected_display(monkeypatch):
    monkeypatch.setattr(main, "connected_displays", lambda: [{"id": "HDMI-1"}])


def test_queue_records_the_requested_time_and_a_budget_deadline(plugin):
    plugin._queue("HDMI-1", after=100, now=90)
    assert plugin.pending["HDMI-1"] == {"after": 100, "deadline": 90 + APPLY_BUDGET_SECONDS}


def test_queue_never_pulls_an_existing_attempt_earlier(plugin):
    plugin._queue("HDMI-1", after=100, now=90)
    plugin._queue("HDMI-1", after=95, now=90)
    assert plugin.pending["HDMI-1"]["after"] == 100


def test_queue_defers_an_existing_attempt_when_asked_to_wait_longer(plugin):
    plugin._queue("HDMI-1", after=100, now=90)
    plugin._queue("HDMI-1", after=120, now=90)
    assert plugin.pending["HDMI-1"]["after"] == 120


def test_queue_extends_the_deadline_on_requeue(plugin):
    plugin._queue("HDMI-1", after=100, now=90)
    plugin._queue("HDMI-1", after=100, now=150)
    assert plugin.pending["HDMI-1"]["deadline"] == 150 + APPLY_BUDGET_SECONDS


def test_a_display_never_switched_is_not_in_cooldown(plugin):
    assert plugin._in_cooldown("HDMI-1", now=0) is False


def test_a_display_switched_just_now_is_in_cooldown(plugin):
    plugin.last_success["HDMI-1"] = 100
    assert plugin._in_cooldown("HDMI-1", now=100 + COOLDOWN_SECONDS - 1) is True


def test_cooldown_expires_after_the_full_window(plugin):
    plugin.last_success["HDMI-1"] = 100
    assert plugin._in_cooldown("HDMI-1", now=100 + COOLDOWN_SECONDS) is False


def test_enabled_displays_returns_connected_displays_with_an_enabled_rule(plugin):
    plugin.store = FakeStore([_rule("HDMI-1"), _rule("HDMI-2")])
    assert plugin._enabled_displays({"HDMI-1", "HDMI-2"}) == ["HDMI-1", "HDMI-2"]


def test_enabled_displays_skips_a_disabled_rule(plugin):
    plugin.store = FakeStore([_rule("HDMI-1", enabled=False), _rule("HDMI-2")])
    assert plugin._enabled_displays({"HDMI-1", "HDMI-2"}) == ["HDMI-2"]


def test_enabled_displays_skips_a_disconnected_display(plugin):
    plugin.store = FakeStore([_rule("HDMI-1"), _rule("HDMI-2")])
    assert plugin._enabled_displays({"HDMI-2"}) == ["HDMI-2"]


def test_enabled_displays_is_empty_without_rules(plugin):
    assert plugin._enabled_displays({"HDMI-1"}) == []


def test_not_paused_while_nothing_is_streaming(plugin):
    assert plugin._paused_by_streaming() is False


def test_paused_while_a_session_streams_from_this_machine(plugin):
    asyncio.run(plugin.set_streaming(True))
    assert plugin._paused_by_streaming() is True


def test_the_session_ending_resumes_auto_switch(plugin):
    asyncio.run(plugin.set_streaming(True))
    asyncio.run(plugin.set_streaming(False))
    assert plugin._paused_by_streaming() is False


def test_never_paused_when_the_setting_is_off(plugin):
    plugin.store = FakeStore([], pause_when_streaming=False)
    asyncio.run(plugin.set_streaming(True))
    assert plugin._paused_by_streaming() is False


def test_the_indicator_reports_the_pause(plugin, one_connected_display):
    plugin.store = FakeStore([_rule("HDMI-1")])
    asyncio.run(plugin.set_streaming(True))
    assert asyncio.run(plugin.auto_switch_paused()) is True


def test_the_indicator_stays_quiet_when_no_display_is_connected(plugin, monkeypatch):
    monkeypatch.setattr(main, "connected_displays", lambda: [])
    plugin.store = FakeStore([_rule("HDMI-1")])
    asyncio.run(plugin.set_streaming(True))
    assert asyncio.run(plugin.auto_switch_paused()) is False


def test_the_indicator_stays_quiet_when_no_rule_could_have_fired(plugin):
    asyncio.run(plugin.set_streaming(True))
    assert asyncio.run(plugin.auto_switch_paused()) is False


def test_the_indicator_stays_quiet_when_every_rule_is_disabled(plugin):
    plugin.store = FakeStore([_rule("HDMI-1", enabled=False)])
    asyncio.run(plugin.set_streaming(True))
    assert asyncio.run(plugin.auto_switch_paused()) is False


def test_the_first_poll_after_a_resume_reads_as_the_wake_trigger(plugin):
    plugin._resumed = True
    assert plugin._consume_trigger_reason() == "wake"


def test_the_resume_flag_is_consumed_once(plugin):
    plugin._resumed = True
    plugin._consume_trigger_reason()
    assert plugin._consume_trigger_reason() == "connect"


def test_an_appearing_display_is_queued_when_nothing_is_streaming(plugin, one_connected_display):
    plugin.store = FakeStore([_rule("HDMI-1")])
    asyncio.run(plugin._apply_rules())
    assert "HDMI-1" in plugin.pending


def test_a_streaming_session_drops_the_queue_instead_of_switching(plugin, one_connected_display):
    plugin.store = FakeStore([_rule("HDMI-1")])
    plugin.pending = {"HDMI-1": {"after": 0, "deadline": 1e9}}
    asyncio.run(plugin.set_streaming(True))
    asyncio.run(plugin._apply_rules())
    assert plugin.pending == {}


@pytest.fixture
def switched(plugin, monkeypatch):
    """Make _attempt runnable off-device: a paired TV, no network, and a record of every
    set_input that actually reached a driver."""
    calls = []

    class FakeDriver:
        async def set_input(self, host, creds, input_id):
            calls.append(input_id)
            return True

    plugin.store.find_tv = lambda host: {"host": host, "name": "TV", "brand": "lg", "creds": {}}
    monkeypatch.setattr(main, "select_driver", lambda registry, brand: FakeDriver())
    return calls


def test_an_attempt_switches_when_nothing_is_streaming(plugin, switched):
    plugin.pending = {"HDMI-1": {"after": 0, "deadline": 1e9}}
    plugin._wake = _always_wakes
    asyncio.run(plugin._attempt(_rule("HDMI-1"), "HDMI-1"))
    assert switched == ["HDMI_1"]


def test_a_session_starting_mid_attempt_stops_the_switch_before_it_lands(plugin, switched):
    """_wake can hold an attempt for WAKE_TIMEOUT. A session starting inside that window clears
    the queue, but cannot cancel the already-spawned task — so the attempt must re-check."""
    plugin.pending = {"HDMI-1": {"after": 0, "deadline": 1e9}}

    async def wake_then_stream(tv):
        await plugin.set_streaming(True)  # the session starts while we wait on the TV
        return True

    plugin._wake = wake_then_stream
    asyncio.run(plugin._attempt(_rule("HDMI-1"), "HDMI-1"))
    assert switched == []
    assert plugin.pending == {}  # dropped, not deferred


async def _always_wakes(tv):
    return True


def test_a_paused_poll_clears_the_resume_flag_cleanly(plugin, one_connected_display):
    plugin._resumed = True
    asyncio.run(plugin.set_streaming(True))
    asyncio.run(plugin._apply_rules())
    assert plugin._resumed is False


def test_ending_streaming_resumes_normal_polling_for_new_appearances(plugin, monkeypatch):
    monkeypatch.setattr(main, "connected_displays", lambda: [])
    plugin.store = FakeStore([_rule("HDMI-1")])
    asyncio.run(plugin.set_streaming(True))
    asyncio.run(plugin._apply_rules())  # poll while streaming (no displays connected)

    # Streaming ends and a new display connects
    asyncio.run(plugin.set_streaming(False))
    monkeypatch.setattr(main, "connected_displays", lambda: [{"id": "HDMI-1"}])
    asyncio.run(plugin._apply_rules())
    assert "HDMI-1" in plugin.pending
