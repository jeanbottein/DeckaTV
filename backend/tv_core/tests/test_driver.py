import asyncio

import pytest

from tv_core.driver import TvDriver, build_registry, list_brands, select_driver


class _StubDriver:
    def __init__(self, name, label):
        self.name = name
        self.label = label


def _run(coro):
    return asyncio.run(coro)


def test_build_registry_keys_drivers_by_name():
    driver = _StubDriver("lg", "LG (webOS)")
    assert build_registry([driver]) == {"lg": driver}


def test_list_brands_exposes_id_and_label():
    registry = build_registry([_StubDriver("lg", "LG (webOS)")])
    assert list_brands(registry) == [{"id": "lg", "label": "LG (webOS)"}]


def test_select_driver_returns_registered_driver():
    driver = _StubDriver("lg", "LG (webOS)")
    assert select_driver(build_registry([driver]), "lg") is driver


def test_select_driver_rejects_unknown_brand():
    with pytest.raises(ValueError):
        select_driver({}, "samsung")


# A driver that omits an optional command must say so rather than return quietly: the caller
# logs "powered off <tv>" and the panel toasts success on a silent return, reporting an action
# that never happened. The genuinely optional *queries* below stay honest by answering instead.


def test_power_off_reports_that_it_is_unsupported():
    with pytest.raises(NotImplementedError):
        _run(TvDriver().power_off("tv.lan", {}))


def test_volume_up_reports_that_it_is_unsupported():
    with pytest.raises(NotImplementedError):
        _run(TvDriver().volume_up("tv.lan", {}))


def test_volume_down_reports_that_it_is_unsupported():
    with pytest.raises(NotImplementedError):
        _run(TvDriver().volume_down("tv.lan", {}))


def test_reachable_defaults_to_not_reachable():
    assert _run(TvDriver().reachable("tv.lan")) is False


def test_discover_defaults_to_finding_nothing():
    assert _run(TvDriver().discover()) == []
