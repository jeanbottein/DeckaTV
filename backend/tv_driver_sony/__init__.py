"""Sony BRAVIA driver package. All Sony-specific code lives here."""

from tv_core.driver import TvDriver

from . import bravia, discover


class SonyDriver(TvDriver):
    name = "sony"
    label = "Sony (BRAVIA)"

    async def discover(self):
        return await discover.discover()

    async def pair(self, host, secret=""):
        # `secret` is the on-screen PIN. Empty on the first press: bravia.pair raises
        # PinRequired (surfaced as SONY_PIN_REQUIRED) so the UI reveals the PIN field.
        return await bravia.pair(host, secret)

    async def list_inputs(self, host, creds):
        return await bravia.fetch_inputs(host, creds)

    async def set_input(self, host, creds, input_id):
        return await bravia.set_input(host, creds, input_id)

    async def reachable(self, host):
        return await bravia.reachable(host)
