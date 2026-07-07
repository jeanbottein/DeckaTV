from tv_core.ssdp import _Collector, build_msearch, parse_headers


def test_build_msearch_advertises_the_search_target():
    query = build_msearch("urn:samsung.com:device:RemoteControlReceiver:1").decode()
    assert query.startswith("M-SEARCH * HTTP/1.1\r\n")
    assert "ST: urn:samsung.com:device:RemoteControlReceiver:1\r\n" in query
    assert query.endswith("\r\n\r\n")


def test_parse_headers_upper_cases_keys_and_skips_status_line():
    response = b"HTTP/1.1 200 OK\r\nLocation: http://192.168.1.40:1754/\r\n\r\n"
    assert parse_headers(response) == {"LOCATION": "http://192.168.1.40:1754/"}


def test_collector_keeps_first_reply_per_host():
    collector = _Collector()
    collector.datagram_received(b"HTTP/1.1 200 OK\r\nLOCATION: http://a/\r\n\r\n", ("10.0.0.2", 1900))
    collector.datagram_received(b"HTTP/1.1 200 OK\r\nLOCATION: http://b/\r\n\r\n", ("10.0.0.2", 1900))
    assert collector.locations == {"10.0.0.2": "http://a/"}
