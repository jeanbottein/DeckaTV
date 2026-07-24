from tv_core import wol


def _neigh_output(monkeypatch, table):
    """Stand in for `ip neigh show <ip>`, keyed by address."""
    monkeypatch.setattr(wol, "_run_neigh", lambda ip: table.get(ip, ""))


def _resolves_to(monkeypatch, addresses):
    monkeypatch.setattr(wol, "_addresses", lambda host: addresses)


def test_valid_mac_accepts_colon_and_dash_forms():
    assert wol.is_valid_mac("aa:bb:cc:dd:ee:ff")
    assert wol.is_valid_mac("AA-BB-CC-DD-EE-FF")


def test_valid_mac_rejects_the_null_mac():
    # An incomplete neighbor entry reports 00:00:00:00:00:00; storing it would poison the
    # cached MAC forever, since the backfill only runs while no MAC is recorded.
    assert wol.is_valid_mac("00:00:00:00:00:00") is False


def test_valid_mac_rejects_malformed_input():
    assert wol.is_valid_mac("nope") is False
    assert wol.is_valid_mac("aa:bb:cc:dd:ee") is False


def test_neigh_mac_reads_the_lladdr_field(monkeypatch):
    _neigh_output(monkeypatch, {"10.0.0.5": "10.0.0.5 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE"})
    assert wol._neigh_mac("10.0.0.5") == "aa:bb:cc:dd:ee:ff"


def test_neigh_mac_is_none_without_an_lladdr(monkeypatch):
    _neigh_output(monkeypatch, {"10.0.0.5": "10.0.0.5 dev wlan0 FAILED"})
    assert wol._neigh_mac("10.0.0.5") is None


def test_neigh_mac_survives_a_truncated_lladdr_line(monkeypatch):
    _neigh_output(monkeypatch, {"10.0.0.5": "10.0.0.5 dev wlan0 lladdr"})
    assert wol._neigh_mac("10.0.0.5") is None


def test_resolve_mac_falls_back_to_the_next_address(monkeypatch):
    _resolves_to(monkeypatch, ["fe80::1", "10.0.0.5"])
    _neigh_output(monkeypatch, {"10.0.0.5": "10.0.0.5 lladdr aa:bb:cc:dd:ee:ff REACHABLE"})
    assert wol.resolve_mac("tv.lan") == "aa:bb:cc:dd:ee:ff"


def test_resolve_mac_skips_a_null_mac_entry(monkeypatch):
    _resolves_to(monkeypatch, ["fe80::1", "10.0.0.5"])
    _neigh_output(
        monkeypatch,
        {
            "fe80::1": "fe80::1 lladdr 00:00:00:00:00:00 INCOMPLETE",
            "10.0.0.5": "10.0.0.5 lladdr aa:bb:cc:dd:ee:ff REACHABLE",
        },
    )
    assert wol.resolve_mac("tv.lan") == "aa:bb:cc:dd:ee:ff"


def test_resolve_mac_is_none_when_nothing_is_in_the_table(monkeypatch):
    _resolves_to(monkeypatch, ["10.0.0.5"])
    _neigh_output(monkeypatch, {})
    assert wol.resolve_mac("tv.lan") is None


def test_resolve_mac_is_none_when_the_host_does_not_resolve(monkeypatch):
    _resolves_to(monkeypatch, [])
    assert wol.resolve_mac("nowhere.lan") is None


def test_send_magic_packet_rejects_a_malformed_mac():
    assert wol.send_magic_packet("nope") is False


def test_send_magic_packet_rejects_the_null_mac():
    assert wol.send_magic_packet("00:00:00:00:00:00") is False
