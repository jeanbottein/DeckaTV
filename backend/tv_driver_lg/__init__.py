"""LG webOS driver package. All LG-specific code lives here."""

from tv_core.driver import TvDriver

from . import discover, webos


class LgDriver(TvDriver):
    name = "lg"
    label = "LG (webOS)"

    async def discover(self):
        return await discover.discover()

    async def pair(self, host, secret=""):
        # LG pairs by an on-TV prompt, so there's no secret to enter; accept and ignore it
        # to keep a single generic pair(host, secret) call site across all brands.
        return await webos.pair(host)

    async def list_inputs(self, host, creds):
        return await webos.fetch_inputs(host, creds)

    async def set_input(self, host, creds, input_id):
        return await webos.set_input(host, creds, input_id)

    async def power_off(self, host, creds):
        return await webos.power_off(host, creds)

    async def volume_up(self, host, creds):
        return await webos.volume_up(host, creds)

    async def volume_down(self, host, creds):
        return await webos.volume_down(host, creds)

    async def reachable(self, host):
        return await webos.reachable(host)
