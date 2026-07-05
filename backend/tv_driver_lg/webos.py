"""Minimal LG webOS (SSAP) client over WebSocket. LG-specific."""

import asyncio
import json
import logging
import ssl

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 6
PAIR_TIMEOUT = 60
REQUEST_TIMEOUT = 10
REACH_TIMEOUT = 2
REACH_PORTS = (3001, 3000)

REGISTER_MANIFEST = {
    "manifestVersion": 1,
    "permissions": [
        "LAUNCH",
        "CONTROL_INPUT_TV",
        "READ_INPUT_DEVICE_LIST",
        "READ_TV_CURRENT_CHANNEL",
        # Needed for getForegroundAppInfo (reading the current input) — without it the TV
        # rejects the request with "401 insufficient permissions".
        "READ_RUNNING_APPS",
        "READ_APP_STATUS",
        "WRITE_SETTINGS",
    ],
}


class WebOSError(Exception):
    pass


def _insecure_ssl():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


class WebOSClient:
    def __init__(self, host):
        self._host = host
        self._socket = None
        self._counter = 0

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

        endpoints = [
            (f"wss://{self._host}:3001", _insecure_ssl()),
            (f"ws://{self._host}:3000", None),
        ]
        last_error = None
        for url, context in endpoints:
            try:
                return await asyncio.wait_for(connect(url, ssl=context), CONNECT_TIMEOUT)
            except Exception as error:  # noqa: BLE001 - report any connection failure
                last_error = error
        raise WebOSError(f"cannot reach {self._host}: {last_error}")

    async def _send(self, message):
        await self._socket.send(json.dumps(message))

    async def _receive(self, timeout):
        return json.loads(await asyncio.wait_for(self._socket.recv(), timeout))

    async def register(self, key):
        payload = {"forcePairing": False, "pairingType": "PROMPT", "manifest": REGISTER_MANIFEST}
        if key:
            payload["client-key"] = key
        await self._send({"type": "register", "id": "register", "payload": payload})
        while True:
            message = await self._receive(PAIR_TIMEOUT)
            if message.get("type") == "registered":
                return message["payload"]["client-key"]
            if message.get("type") == "error":
                raise WebOSError(message.get("error", "registration rejected"))

    async def _request(self, uri, payload=None):
        self._counter += 1
        message_id = f"req-{self._counter}"
        await self._send({"type": "request", "id": message_id, "uri": uri, "payload": payload or {}})
        while True:
            message = await self._receive(REQUEST_TIMEOUT)
            if message.get("id") != message_id:
                continue
            if message.get("type") == "error":
                raise WebOSError(message.get("error", uri))
            return message.get("payload", {})

    async def list_inputs(self):
        payload = await self._request("ssap://tv/getExternalInputList")
        return [
            {"id": device["id"], "label": device.get("label", device["id"])}
            for device in payload.get("devices", [])
        ]

    async def switch_input(self, input_id):
        await self._request("ssap://tv/switchInput", {"inputId": input_id})

    async def current_input(self):
        """Return the id of the external input currently on screen, or None.

        Maps the foreground app id (e.g. "com.webos.app.hdmi1") back to an external input's
        id (e.g. "HDMI_1"); returns None when the TV isn't on an external input.
        """
        foreground = await self._request("ssap://com.webos.applicationManager/getForegroundAppInfo")
        app_id = foreground.get("appId") or ""
        if not app_id:
            return None
        devices = (await self._request("ssap://tv/getExternalInputList")).get("devices", [])
        for device in devices:
            if device.get("appId") == app_id:
                return device["id"]
        # Some TVs' input list omits appId — fall back to matching the app id's compact suffix
        # to an input id ("com.webos.app.hdmi1" ↔ "HDMI_1").
        compact = app_id.lower().replace("_", "")
        for device in devices:
            input_id = device.get("id", "")
            if input_id and compact.endswith(input_id.lower().replace("_", "")):
                return input_id
        return None


async def reachable(host):
    """Quick TCP probe of the webOS SSAP ports; no pairing or handshake."""
    for port in REACH_PORTS:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), REACH_TIMEOUT
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001 - closing is best-effort
                pass
            return True
        except Exception:  # noqa: BLE001 - try the next port, then report unreachable
            continue
    return False


async def pair(host, key=""):
    async with WebOSClient(host) as client:
        return await client.register(key)


async def fetch_inputs(host, key):
    async with WebOSClient(host) as client:
        await client.register(key)
        return await client.list_inputs()


async def set_input(host, key, input_id):
    """Switch the TV to `input_id`; return True if it switched, False if already there."""
    async with WebOSClient(host) as client:
        await client.register(key)
        # Skip the switch (and its HDMI renegotiation) if we're already on this input.
        try:
            current = await client.current_input()
        except Exception as error:  # noqa: BLE001 - if the check fails, fall back to switching
            logger.info("current_input check failed for %s: %r", host, error)
            current = None
        logger.debug("set_input %s: target=%r current=%r", host, input_id, current)
        if current == input_id:
            return False
        await client.switch_input(input_id)
        return True
