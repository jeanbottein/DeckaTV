"""Make `main.py` importable off-device.

Decky injects its `decky` module into the plugin process at runtime; it does not exist
here. Everything main.py needs from it at import time is the module itself, so a stub is
enough to unlock testing the scheduling logic (the part with the real hardware hazards).
"""

import logging
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(__file__))


def _stub_decky():
    module = types.ModuleType("decky")
    module.logger = logging.getLogger("deckatv-tests")
    module.DECKY_PLUGIN_LOG_DIR = ""
    module.DECKY_PLUGIN_SETTINGS_DIR = ""

    async def emit(*_args, **_kwargs):
        return None

    module.emit = emit
    return module


sys.modules.setdefault("decky", _stub_decky())
sys.path.insert(0, ROOT)
