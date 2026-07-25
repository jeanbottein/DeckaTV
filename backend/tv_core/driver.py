"""Brand-agnostic TV driver contract and registry.

The core never imports a concrete driver. The plugin (composition root) builds
the registry from injected drivers, so adding a brand never touches this module.
"""


class TvDriver:
    name = ""  # stable brand id stored on each TV record
    label = ""  # human-readable brand name shown in the UI

    async def pair(self, host, secret=""):
        """Pair with the TV at `host` and return opaque, JSON-serializable creds.

        `secret` is an optional, brand-specific second factor entered by the user (e.g. a
        PIN shown on a Sony TV). Brands that pair by an on-TV prompt alone (like LG) ignore
        it. A driver may raise to signal it needs the secret: a driver whose error message is
        the agreed sentinel (see the Sony driver's SONY_PIN_REQUIRED) tells the UI to collect
        the secret and call pair again with it.
        """
        raise NotImplementedError

    async def list_inputs(self, host, creds):
        """Return [{id, label}] of selectable inputs."""
        raise NotImplementedError

    async def set_input(self, host, creds, input_id):
        """Switch the TV to `input_id`. Return True if the input actually changed, or False if
        the TV was already on it, so callers can skip a redundant "switched" notification."""
        raise NotImplementedError

    async def reachable(self, host):
        """Return True if the TV at `host` answers on the network."""
        return False

    # Optional commands. Unlike the optional *queries* below — which answer honestly with
    # "unreachable" / "found nothing" — a command has no such answer, so an unimplemented one
    # raises. Returning quietly would report success for an action that never happened: the
    # plugin logs "powered off <tv>" and the panel toasts it.

    async def power_off(self, host, creds):
        """Power the TV off (standby). Optional; raises if the brand can't."""
        raise NotImplementedError(f"{self.label or self.name} cannot be powered off")

    async def volume_up(self, host, creds):
        """Nudge the TV volume up one step. Optional; raises if the brand can't."""
        raise NotImplementedError(f"{self.label or self.name} has no volume control")

    async def volume_down(self, host, creds):
        """Nudge the TV volume down one step. Optional; raises if the brand can't."""
        raise NotImplementedError(f"{self.label or self.name} has no volume control")

    async def discover(self):
        """Return [{host, name}] of TVs found on the LAN for this brand.

        Optional: brands that can't (or don't yet) auto-discover return []. The
        core never knows *how* a driver finds TVs — only that it may return some.
        """
        return []


def build_registry(drivers):
    return {driver.name: driver for driver in drivers}


def list_brands(registry):
    return [{"id": driver.name, "label": driver.label} for driver in registry.values()]


def select_driver(registry, brand):
    driver = registry.get(brand)
    if driver is None:
        raise ValueError(f"unsupported brand: {brand}")
    return driver
