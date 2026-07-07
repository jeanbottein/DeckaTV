"""The selectable inputs and their remote keys.

Tizen has no local "list sources" or "current source" API, so the driver offers a
fixed HDMI list and switches by sending the matching direct-select remote key
(KEY_HDMI1..KEY_HDMI4 — the same keys samsungctl documents; per-model support is
one reason this driver is [BETA]).
"""

_INPUT_KEYS = {
    "HDMI1": "KEY_HDMI1",
    "HDMI2": "KEY_HDMI2",
    "HDMI3": "KEY_HDMI3",
    "HDMI4": "KEY_HDMI4",
}


def selectable_inputs():
    return [{"id": input_id, "label": f"HDMI {input_id[-1]}"} for input_id in _INPUT_KEYS]


def key_for(input_id):
    return _INPUT_KEYS.get(input_id)
