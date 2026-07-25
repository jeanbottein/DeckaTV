"""Minimal Sony BRAVIA (Scalar Web API) client over HTTP. Sony-specific.

Sony Android/Google TVs expose a JSON control API at ``http://<host>/sony/<service>``.
Authentication uses Sony's official ``actRegister`` PIN flow: the first,
unauthenticated register makes the TV display a 4-digit PIN; re-registering with
that PIN as HTTP Basic auth returns a long-lived ``auth`` cookie, which we persist
as the TV's opaque creds and replay on every later control call.

No third-party dependency: requests go through the stdlib ``urllib`` on a worker
thread (``asyncio.to_thread``), so the plugin's event loop never blocks and nothing
needs vendoring the way the LG driver vendors ``websockets``.
"""

import asyncio
import base64
import json
import logging
import time
import urllib.error
import urllib.request
from http.cookies import SimpleCookie

logger = logging.getLogger(__name__)

PORT = 80
REQUEST_TIMEOUT = 10
REACH_TIMEOUT = 2
# After asking a standby TV to power on, wait this long for avContent to accept a switch.
POWER_ON_TIMEOUT = 15
POWER_ON_POLL = 1.5

# Identifies this client in the TV's "Registered devices" list. Fixed (not random) so a
# re-pair maps back to the same entry instead of piling up duplicates. `function: WOL`
# asks the TV to allow waking this client over the network.
CLIENT_ID = "DeckaTV:00000000-0000-0000-0000-0000deckatv01"
NICKNAME = "DeckaTV (Steam Deck)"
REGISTER_PARAMS = [
    {"clientid": CLIENT_ID, "nickname": NICKNAME, "level": "private"},
    [{"clientid": CLIENT_ID, "value": "yes", "nickname": NICKNAME, "function": "WOL"}],
]

# Surfaced verbatim to the UI so the Add-TV form knows to reveal the PIN field. Keep in
# sync with the check in src/components/AddTv.tsx.
PIN_REQUIRED = "SONY_PIN_REQUIRED"


class BraviaError(Exception):
    pass


class PinRequired(BraviaError):
    """pair() step 1: the TV is now showing a PIN; call pair() again with it as `secret`."""

    def __init__(self):
        super().__init__(PIN_REQUIRED)


def _cookie(creds):
    """Pull the stored `auth=…` cookie out of a TV's opaque creds."""
    return creds.get("cookie", "") if isinstance(creds, dict) else ""


def _rpc(method, params=None, version="1.0"):
    return {"method": method, "params": params or [], "id": 1, "version": version}


def _extract_auth_cookie(set_cookies):
    """Return the `auth=<token>` name/value pair from any of the Set-Cookie headers, or ""."""
    for raw in set_cookies:
        jar = SimpleCookie()
        try:
            jar.load(raw)
        except Exception:  # noqa: BLE001 - a malformed header just means "no cookie here"
            continue
        morsel = jar.get("auth")
        if morsel and morsel.value:
            return f"auth={morsel.value}"
    return ""


def _post_sync(host, service, payload, pin, cookie, timeout):
    """Blocking POST to /sony/<service>. Returns (status, set_cookie_headers, body_text).

    An HTTP error status (401 for the PIN challenge, 403 when IP control is off) is a normal
    part of the protocol, so we return it rather than raising; only transport failures raise.
    """
    url = f"http://{host}:{PORT}/sony/{service}"
    headers = {"Content-Type": "application/json"}
    if pin is not None:
        headers["Authorization"] = "Basic " + base64.b64encode(f":{pin}".encode()).decode()
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, resp.headers.get_all("Set-Cookie") or [], body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace") if error.fp else ""
        cookies = error.headers.get_all("Set-Cookie") if error.headers else []
        return error.code, cookies or [], body


async def _post(host, service, payload, pin=None, cookie="", timeout=REQUEST_TIMEOUT):
    return await asyncio.to_thread(_post_sync, host, service, payload, pin, cookie, timeout)


async def _call(host, cookie, service, method, params=None, version="1.0"):
    """Authenticated RPC that returns the JSON `result` list, raising BraviaError on API error."""
    status, _set_cookies, body = await _post(host, service, _rpc(method, params, version), cookie=cookie)
    try:
        data = json.loads(body) if body else {}
    except ValueError:
        raise BraviaError(f"{service}.{method}: non-JSON response (HTTP {status})")
    if not isinstance(data, dict):
        raise BraviaError(f"{service}.{method}: unexpected response (HTTP {status})")
    if data.get("error"):
        raise BraviaError(f"{service}.{method}: {data['error']}")
    return data.get("result", [])


async def pair(host, secret=""):
    """actRegister PIN flow.

    With no `secret`: register unauthenticated. A 401 means the TV is now showing a PIN —
    raise PinRequired so the UI collects it. With a `secret` (the PIN): register with it as
    Basic auth and persist the returned `auth` cookie as creds. A TV that already trusts this
    client (or has open control) returns 200 immediately; then the cookie may be empty.
    """
    pin = secret or None
    status, set_cookies, _body = await _post(host, "accessControl", _rpc("actRegister", REGISTER_PARAMS), pin=pin)
    if status == 200:
        return {"cookie": _extract_auth_cookie(set_cookies)}
    if status == 401:
        if pin is None:
            raise PinRequired()
        raise BraviaError("PIN rejected — re-check the code shown on the TV and try again")
    if status == 403:
        raise BraviaError(
            "IP control is disabled on the TV. Enable it under "
            "Settings → Network → Home network → IP control → Authentication."
        )
    raise BraviaError(f"pairing failed (HTTP {status})")


async def reachable(host):
    """Quick TCP probe of the Scalar API port; no auth or handshake. True in networked
    standby too (Remote Start keeps the HTTP server up) — set_input powers the panel on."""
    writer = None
    try:
        _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, PORT), REACH_TIMEOUT)
        return True
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return False
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001 - closing is best-effort
                pass


async def _power_status(host, cookie):
    try:
        result = await _call(host, cookie, "system", "getPowerStatus")
    except BraviaError:
        return ""
    return (result[0].get("status") if result else "") or ""


async def _ensure_on(host, cookie):
    """Power the TV on if it's in networked standby; no-op when it's already active.

    Sony rejects setPlayContent while the panel is off, so unlike LG (where Wake-on-LAN
    alone suffices) the switch must first bring the display up over the REST API and wait
    for it to settle before selecting the input.
    """
    if await _power_status(host, cookie) == "active":
        return
    try:
        await _call(host, cookie, "system", "setPowerStatus", [{"status": True}])
    except BraviaError as error:
        logger.info("setPowerStatus for %s failed: %s", host, error)
    deadline = time.monotonic() + POWER_ON_TIMEOUT
    while time.monotonic() < deadline:
        await asyncio.sleep(POWER_ON_POLL)
        if await _power_status(host, cookie) == "active":
            return


async def fetch_inputs(host, creds):
    """Return [{id, label}] of external inputs, id being the Sony input uri used to switch."""
    cookie = _cookie(creds)
    result = await _call(host, cookie, "avContent", "getCurrentExternalInputsStatus")
    devices = result[0] if result else []
    inputs = []
    for device in devices:
        uri = device.get("uri")
        if not uri:
            continue
        label = device.get("label") or device.get("title") or uri
        inputs.append({"id": uri, "label": label})
    return inputs


async def set_input(host, creds, input_id):
    """Switch the TV to `input_id` (a Sony uri like ``extInput:hdmi?port=1``).

    Returns True if it switched, False if the TV was already on that input, so callers can
    skip a redundant "switched" notification — matching the LG driver's contract.
    """
    cookie = _cookie(creds)
    await _ensure_on(host, cookie)
    try:
        playing = await _call(host, cookie, "avContent", "getPlayingContentInfo")
        current = playing[0].get("uri") if playing else None
    except BraviaError as error:
        # e.g. 40005 "Display Is Turned off", or an app (not an external input) is on screen.
        logger.info("getPlayingContentInfo for %s failed: %s", host, error)
        current = None
    if current and current == input_id:
        return False
    await _call(host, cookie, "avContent", "setPlayContent", [{"uri": input_id}])
    return True
