from tv_core.store import Store


def _store(tmp_path):
    return Store(str(tmp_path / "store.json"))


def test_selected_defaults_to_empty(tmp_path):
    assert _store(tmp_path).selected == ""


def test_set_selected_persists_across_instances(tmp_path):
    path = tmp_path / "store.json"
    Store(str(path)).set_selected("10.0.0.5")
    assert Store(str(path)).selected == "10.0.0.5"


def test_removing_selected_tv_clears_selection(tmp_path):
    store = _store(tmp_path)
    store.upsert_tv("10.0.0.5", "Living room", "lg", "key")
    store.set_selected("10.0.0.5")
    store.remove_tv("10.0.0.5")
    assert store.selected == ""


def test_removing_other_tv_keeps_selection(tmp_path):
    store = _store(tmp_path)
    store.upsert_tv("10.0.0.5", "Living room", "lg", "key")
    store.upsert_tv("10.0.0.6", "Bedroom", "lg", "key")
    store.set_selected("10.0.0.5")
    store.remove_tv("10.0.0.6")
    assert store.selected == "10.0.0.5"


def test_triggers_default_to_enabled(tmp_path):
    store = _store(tmp_path)
    assert store.trigger_enabled("connect")
    assert store.trigger_enabled("wake")
    assert store.trigger_enabled("never-set")


def test_set_trigger_persists_across_instances(tmp_path):
    path = tmp_path / "store.json"
    Store(str(path)).set_trigger("wake", False)
    reloaded = Store(str(path))
    assert reloaded.trigger_enabled("wake") is False
    assert reloaded.trigger_enabled("connect") is True


def test_notifications_default_to_enabled(tmp_path):
    assert _store(tmp_path).notifications is True


def test_set_notifications_persists_across_instances(tmp_path):
    path = tmp_path / "store.json"
    Store(str(path)).set_notifications(False)
    assert Store(str(path)).notifications is False


def test_pause_when_streaming_defaults_to_enabled(tmp_path):
    assert _store(tmp_path).pause_when_streaming is True


def test_pause_when_streaming_defaults_to_enabled_for_an_existing_install(tmp_path):
    """A store written before the setting existed must still read as enabled."""
    path = tmp_path / "store.json"
    path.write_text('{"tvs": [], "rules": [], "selected": ""}', encoding="utf-8")
    assert Store(str(path)).pause_when_streaming is True


def test_set_pause_when_streaming_persists_across_instances(tmp_path):
    path = tmp_path / "store.json"
    Store(str(path)).set_pause_when_streaming(False)
    assert Store(str(path)).pause_when_streaming is False
