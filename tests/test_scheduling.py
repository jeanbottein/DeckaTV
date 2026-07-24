"""Unit tests for the auto-switch queue: which displays get queued, when an attempt may
run, and the post-switch debounce. Pure bookkeeping — no store, driver, or network."""

import pytest

import main
from main import APPLY_BUDGET_SECONDS, COOLDOWN_SECONDS


class FakeStore:
    def __init__(self, rules):
        self.rules = rules


def _rule(display_id, enabled=True):
    return {"display_id": display_id, "host": "tv.lan", "input_id": "HDMI_1", "enabled": enabled}


@pytest.fixture
def plugin():
    instance = main.Plugin()
    instance.pending = {}
    instance.last_success = {}
    instance.store = FakeStore([])
    return instance


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
