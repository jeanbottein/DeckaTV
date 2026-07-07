"""Small brand-agnostic network probes."""

import asyncio


async def any_tcp_port_open(host, ports, timeout):
    """Return True if `host` accepts a TCP connection on any of `ports`."""
    for port in ports:
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        except Exception:  # noqa: BLE001 - try the next port, then report unreachable
            continue
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001 - closing is best-effort
            pass
        return True
    return False
