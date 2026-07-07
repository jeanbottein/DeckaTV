from tv_driver_samsung_tizen import inputs


def test_selectable_inputs_expose_id_and_label_only():
    listed = inputs.selectable_inputs()
    assert listed == [
        {"id": "HDMI1", "label": "HDMI 1"},
        {"id": "HDMI2", "label": "HDMI 2"},
        {"id": "HDMI3", "label": "HDMI 3"},
        {"id": "HDMI4", "label": "HDMI 4"},
    ]


def test_key_for_maps_input_id_to_remote_key():
    assert inputs.key_for("HDMI1") == "KEY_HDMI1"
    assert inputs.key_for("HDMI4") == "KEY_HDMI4"


def test_key_for_unknown_input_returns_none():
    assert inputs.key_for("SCART") is None
