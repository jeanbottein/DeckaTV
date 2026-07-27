"""Wake-on-LAN: learn a host's MAC from the local neighbor table and send magic packets.

Brand-agnostic. The MAC is captured while the TV is awake (at pairing, or whenever
it is reachable) so we can later wake it from standby the way Google Home does.
"""

import socket
import string
import subprocess

NEIGH_TIMEOUT = 2
NULL_MAC_DIGITS = "0" * 12


def _run_neigh(ip):
    """Raw `ip neigh show <ip>` output, or "" if the command is unavailable or times out."""
    try:
        return subprocess.run(
            ["ip", "neigh", "show", ip],
            capture_output=True, text=True, timeout=NEIGH_TIMEOUT, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _lladdr(line):
    """The value after the `lladdr` keyword of one `ip neigh` row, or None.

    An entry in an INCOMPLETE/FAILED state has no address after the keyword, so the
    index is bounds-checked rather than assumed.
    """
    fields = line.split()
    if "lladdr" not in fields:
        return None
    value = fields.index("lladdr") + 1
    return fields[value] if value < len(fields) else None


def _neigh_mac(ip):
    """MAC for `ip` from the kernel neighbor table (ARP for IPv4, NDP for IPv6) —
    populated as a side effect of any traffic already exchanged with that address."""
    candidates = map(_lladdr, _run_neigh(ip).splitlines())
    return next((mac for mac in candidates if mac), None)


def _addresses(host):
    """Every address `host` resolves to, deduplicated, in resolution order."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return []
    return list(dict.fromkeys(info[4][0] for info in infos))


def resolve_mac(host):
    """Best-effort MAC for a host already seen on the local network.

    Resolves both IPv4 and IPv6 addresses (matching how the actual TV connections
    resolve `host`) since a hostname-only entry may only be reachable over one family.
    """
    macs = map(_neigh_mac, _addresses(host))
    return next((mac for mac in macs if mac and is_valid_mac(mac)), None)


def _hex_digits(mac):
    return mac.replace(":", "").replace("-", "").strip()


def is_valid_mac(mac):
    """True for a MAC we could actually wake. The all-zero address is rejected: an
    incomplete neighbor entry reports it, and caching it as the TV's MAC is permanent
    (the backfill only runs while no MAC is recorded), leaving the TV unwakeable."""
    digits = _hex_digits(mac)
    if digits == NULL_MAC_DIGITS:
        return False
    return len(digits) == 12 and all(char in string.hexdigits for char in digits)


def send_magic_packet(mac, port=9):
    """Broadcast a Wake-on-LAN magic packet for `mac`. Returns False if mac is malformed or send fails."""
    if not is_valid_mac(mac):
        return False
    payload = b"\xff" * 6 + bytes.fromhex(_hex_digits(mac)) * 16
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(payload, ("255.255.255.255", port))
        return True
    except OSError:
        return False
