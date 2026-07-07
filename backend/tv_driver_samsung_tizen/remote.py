"""Minimal Samsung Tizen remote client over WebSocket. Samsung-specific.

Speaks the same local protocol as samsungtvws / Home Assistant: wss on 8002 with
a token the TV hands out after the user accepts an on-screen prompt; early Tizen
firmware exposes the same channel unauthenticated over plain ws on 8001.
"""

import asyncio
import base64
import json
import ssl
import urllib.request

from tv_core.net import any_tcp_port_open

APP_NAME = "DeckaTV"  # shown in the TV's authorization prompt and device-manager list
SECURE_PORT = 8002  # wss + token (2016+ firmware)
OPEN_PORT = 8001  # plain ws, no token (early Tizen firmware); also serves the REST API
CONNECT_TIMEOUT = 6
PAIR_TIMEOUT = 60  # the user has to walk to the TV and accept the prompt
HANDSHAKE_TIMEOUT = 10  # with a stored token the TV confirms right away
# The TV processes a key only after the channel settles; closing the socket the
# instant the frame is sent makes some models drop the key on the floor.
KEY_SETTLE_SECONDS = 1
REACH_TIMEOUT = 2
DEVICE_INFO_TIMEOUT = 3

EVENT_CONNECTED = "ms.channel.connect"
EVENT_UNAUTHORIZED = "ms.channel.unauthorized"


class TizenError(Exception):
    pass


def ws_url(host, port, token):
    name = base64.b64encode(APP_NAME.encode()).decode()
    scheme = "wss" if port == SECURE_PORT else "ws"
    url = f"{scheme}://{host}:{port}/api/v2/channels/samsung.remote.control?name={name}"
    return f"{url}&token={token}" if token else url


def key_message(key):
    return {
        "method": "ms.remote.control",
        "params": {
            "Cmd": "Click",
            "DataOfCmd": key,
            "Option": "false",
            "TypeOfRemote": "SendRemoteKey",
        },
    }


def token_from_event(message):
    """Extract the auth token from the TV's handshake event; raise if it isn't a connect."""
    event = message.get("event", "")
    if event == EVENT_UNAUTHORIZED:
        raise TizenError("pairing rejected on the TV")
    if event != EVENT_CONNECTED:
        raise TizenError(f"unexpected handshake event: {event or message}")
    return message.get("data", {}).get("token", "")


def name_from_device_info(info):
    return info.get("device", {}).get("name", "")


def _insecure_ssl():
    # The TV's certificate is self-signed, so verification can never pass.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


class TizenClient:
    def __init__(self, host, port, token=""):
        self._host = host
        self._port = port
        self._token = token
        self._socket = None

    async def __aenter__(self):
        self._socket = await self._open()
        return self

    async def __aexit__(self, *_):
        if self._socket is not None:
            await self._socket.close()

    async def _open(self):
        # Imported lazily so the package is importable (e.g. under unit tests) without the
        # vendored `websockets`, which only `main.py` puts on sys.path at runtime.
        from websockets.asyncio.client import connect

        url = ws_url(self._host, self._port, self._token)
        context = _insecure_ssl() if self._port == SECURE_PORT else None
        return await asyncio.wait_for(connect(url, ssl=context), CONNECT_TIMEOUT)

    async def handshake(self, timeout):
        """Wait for the TV's connect event and return the token it granted ("" on 8001)."""
        message = json.loads(await asyncio.wait_for(self._socket.recv(), timeout))
        return token_from_event(message)

    async def send_key(self, key):
        await self._socket.send(json.dumps(key_message(key)))
        await asyncio.sleep(KEY_SETTLE_SECONDS)


async def pair(host):
    """Pair with the TV (the user accepts an on-screen prompt) and return creds.

    Tries the tokened wss endpoint first; TVs on early Tizen firmware only expose the
    open ws endpoint, where the connect event carries no token. The port that worked is
    stored in the creds so later connects don't re-probe.
    """
    last_error = None
    for port in (SECURE_PORT, OPEN_PORT):
        try:
            async with TizenClient(host, port) as client:
                token = await client.handshake(PAIR_TIMEOUT)
                return {"token": token, "port": port}
        except TizenError:
            raise  # the TV answered and denied us — the other port won't change its mind
        except Exception as error:  # noqa: BLE001 - connection failure; try the open port
            last_error = error
    raise TizenError(f"cannot reach {host}: {last_error}")


async def send_key(host, creds, key):
    port = creds.get("port", SECURE_PORT)
    async with TizenClient(host, port, creds.get("token", "")) as client:
        # The TV may hand back a refreshed token here; Samsung keeps tokens stable in
        # practice, and the driver contract has no channel to persist creds, so ignore it.
        await client.handshake(HANDSHAKE_TIMEOUT)
        await client.send_key(key)


async def reachable(host):
    """Quick TCP probe of the Tizen remote-control ports; no pairing or handshake."""
    return await any_tcp_port_open(host, (SECURE_PORT, OPEN_PORT), REACH_TIMEOUT)


def _fetch_device_info(host):
    url = f"http://{host}:{OPEN_PORT}/api/v2/"
    with urllib.request.urlopen(url, timeout=DEVICE_INFO_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


async def device_name(host):
    """The TV's configured name via the Tizen REST API, or None when it doesn't answer.

    Only Tizen sets serve this API, so None also means "not a Tizen TV" — discovery
    uses that to filter out older Samsung (Orsay) sets answering the same SSDP query.
    """
    try:
        info = await asyncio.to_thread(_fetch_device_info, host)
    except Exception:  # noqa: BLE001 - unreachable or not Tizen
        return None
    return name_from_device_info(info)
