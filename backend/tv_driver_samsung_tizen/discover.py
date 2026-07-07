"""Samsung Tizen LAN discovery: SSDP, then a Tizen REST probe. Samsung-specific.

Both Tizen and older Samsung (Orsay) sets answer the RemoteControlReceiver SSDP
search, but only Tizen serves the :8001 REST API — so the probe doubles as the
per-OS filter, keeping non-Tizen sets out of this driver's results.
"""

import asyncio

from tv_core.ssdp import search

from . import remote

SSDP_ST = "urn:samsung.com:device:RemoteControlReceiver:1"


async def discover():
    hosts = list(await search(SSDP_ST))
    names = await asyncio.gather(*(remote.device_name(host) for host in hosts))
    return [{"host": host, "name": name} for host, name in zip(hosts, names) if name is not None]
