"""Samsung Tizen driver package. All Samsung-Tizen-specific code lives here.

[BETA]: written against the documented samsungtvws/samsungctl protocol but not yet
verified on real hardware — the label says so until someone with a Tizen set confirms.
"""

from tv_core.driver import TvDriver

from . import discover, inputs, remote


class SamsungTizenDriver(TvDriver):
    name = "samsung-tizen"
    label = "Samsung (Tizen) [BETA]"

    async def discover(self):
        return await discover.discover()

    async def pair(self, host):
        return await remote.pair(host)

    async def list_inputs(self, host, creds):
        return inputs.selectable_inputs()

    async def set_input(self, host, creds, input_id):
        key = inputs.key_for(input_id)
        if key is None:
            raise ValueError(f"unknown input: {input_id}")
        await remote.send_key(host, creds, key)
        # Tizen has no local "current source" query, so we can't detect "already there";
        # report a change so callers announce the switch.
        return True

    async def reachable(self, host):
        return await remote.reachable(host)
