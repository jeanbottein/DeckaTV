"""Generic SSDP (UPnP M-SEARCH) discovery. Brand-agnostic: each driver supplies
the search target its TVs answer to and interprets the replies itself."""

import asyncio
import socket

SSDP_ADDR = ("239.255.255.250", 1900)
SSDP_MX = 2  # max seconds a device may wait before replying (advertised in the query)
COLLECT_SECONDS = 3  # how long we listen for unicast replies after searching
SEND_BURST = 3  # multicast can be lossy; send the query a few times


def build_msearch(search_target):
    return (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR[0]}:{SSDP_ADDR[1]}\r\n"
        'MAN: "ssdp:discover"\r\n'
        f"MX: {SSDP_MX}\r\n"
        f"ST: {search_target}\r\n"
        "\r\n"
    ).encode()


def parse_headers(data):
    """Parse an SSDP/HTTP response into an upper-cased header dict (ignores the status line)."""
    headers = {}
    for line in data.decode("utf-8", "replace").split("\r\n")[1:]:
        key, sep, value = line.partition(":")
        if sep:
            headers[key.strip().upper()] = value.strip()
    return headers


class _Collector(asyncio.DatagramProtocol):
    def __init__(self):
        self.locations = {}  # host -> LOCATION url (first reply per host wins)

    def datagram_received(self, data, addr):
        location = parse_headers(data).get("LOCATION", "")
        self.locations.setdefault(addr[0], location)


async def search(search_target):
    """Multicast an M-SEARCH for `search_target` and return {host: LOCATION url}."""
    loop = asyncio.get_event_loop()
    transport, collector = await loop.create_datagram_endpoint(
        _Collector, family=socket.AF_INET, local_addr=("0.0.0.0", 0), allow_broadcast=True
    )
    try:
        for _ in range(SEND_BURST):
            transport.sendto(build_msearch(search_target), SSDP_ADDR)
        await asyncio.sleep(COLLECT_SECONDS)
    finally:
        transport.close()
    return dict(collector.locations)
