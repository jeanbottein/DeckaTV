"""Wake-on-LAN: learn a host's MAC from the local neighbor table and send magic packets.

Brand-agnostic. The MAC is captured while the TV is awake (at pairing, or whenever
it is reachable) so we can later wake it from standby the way Google Home does.
"""

import socket
import string
import subprocess

NEIGH_TIMEOUT = 2


def _neigh_mac(ip):
    """MAC for `ip` from the kernel neighbor table (ARP for IPv4, NDP for IPv6) —
    populated as a side effect of any traffic already exchanged with that address."""
    try:
        output = subprocess.run(
            ["ip", "neigh", "show", ip],
            capture_output=True, text=True, timeout=NEIGH_TIMEOUT, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        fields = line.split()
        if "lladdr" in fields:
            return fields[fields.index("lladdr") + 1]
    return None


def resolve_mac(host):
    """Best-effort MAC for a host already seen on the local network.

    Resolves both IPv4 and IPv6 addresses (matching how the actual TV connections
    resolve `host`) since a hostname-only entry may only be reachable over one family.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return None
    seen = set()
    for info in infos:
        ip = info[4][0]
        if ip in seen:
            continue
        seen.add(ip)
        mac = _neigh_mac(ip)
        if mac and is_valid_mac(mac):
            return mac
    return None


def _hex_digits(mac):
    return mac.replace(":", "").replace("-", "").strip()


def is_valid_mac(mac):
    digits = _hex_digits(mac)
    return len(digits) == 12 and all(char in string.hexdigits for char in digits)


def send_magic_packet(mac, port=9):
    """Broadcast a Wake-on-LAN magic packet for `mac`. Returns False if mac is malformed."""
    if not is_valid_mac(mac):
        return False
    payload = b"\xff" * 6 + bytes.fromhex(_hex_digits(mac)) * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(payload, ("255.255.255.255", port))
    return True
