"""LG webOS LAN discovery via SSDP (UPnP M-SEARCH). LG-specific.

mDNS is a poor fit here: every webOS TV advertises the *same* `lgwebostv.local`
hostname, so a second TV renames itself to `lgwebostv-2.local` and you can't tell
which physical set is which. SSDP instead has each TV reply from its own IP, so
multiple TVs come back as distinct entries — and it needs no extra dependency,
just a few UDP datagrams. A TV in standby won't answer, so this complements (not
replaces) manual IP entry.
"""

import asyncio
from urllib.parse import urlparse

from tv_core.ssdp import parse_headers, search  # noqa: F401 - parse_headers re-exported

# The search target webOS TVs answer to (same one Home Assistant's webostv uses).
SSDP_ST = "urn:lge-com:service:webos-second-screen:1"
DESC_TIMEOUT = 2  # per-TV budget to fetch its description XML for a friendly name


def extract_tag(xml, tag):
    """Pull the text of the first <tag>…</tag> out of `xml`, or "" if absent."""
    open_tag, close_tag = f"<{tag}>", f"</{tag}>"
    start = xml.find(open_tag)
    if start == -1:
        return ""
    start += len(open_tag)
    end = xml.find(close_tag, start)
    return xml[start:end].strip() if end != -1 else ""


async def _friendly_name(location):
    """Best-effort fetch of the TV's UPnP <friendlyName>; "" on any failure."""
    if not location:
        return ""
    parsed = urlparse(location)
    if not parsed.hostname:
        return ""
    target = f"{parsed.path or '/'}{'?' + parsed.query if parsed.query else ''}"
    writer = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(parsed.hostname, parsed.port or 80), DESC_TIMEOUT
        )
        request = (
            f"GET {target} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}\r\nConnection: close\r\n\r\n"
        )
        writer.write(request.encode())
        await writer.drain()
        body = await asyncio.wait_for(reader.read(), DESC_TIMEOUT)
        return extract_tag(body.decode("utf-8", "replace"), "friendlyName")
    except Exception:  # noqa: BLE001 - a missing name just means we fall back to the host
        return ""
    finally:
        if writer is not None:
            writer.close()


async def discover():
    locations = await search(SSDP_ST)
    # Resolve names concurrently: one slow/filtered description host shouldn't stall the
    # rest, so the whole phase is bounded by a single DESC_TIMEOUT, not the sum.
    hosts = list(locations.items())
    names = await asyncio.gather(*(_friendly_name(location) for _, location in hosts))
    return [{"host": host, "name": name} for (host, _), name in zip(hosts, names)]
