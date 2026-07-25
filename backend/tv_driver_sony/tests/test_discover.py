from tv_driver_sony.discover import extract_tag, parse_headers

SAMPLE_RESPONSE = (
    "HTTP/1.1 200 OK\r\n"
    "CACHE-CONTROL: max-age=1800\r\n"
    "LOCATION: http://192.168.1.50:52323/dmr.xml\r\n"
    "SERVER: BRAVIA/1.0 UPnP/1.0\r\n"
    "ST: urn:schemas-sony-com:service:ScalarWebAPI:1\r\n"
    "\r\n"
).encode()


def test_parse_headers_upper_cases_keys_and_skips_status_line():
    headers = parse_headers(SAMPLE_RESPONSE)
    assert headers["LOCATION"] == "http://192.168.1.50:52323/dmr.xml"
    assert headers["SERVER"] == "BRAVIA/1.0 UPnP/1.0"
    assert "HTTP/1.1 200 OK" not in headers


def test_extract_tag_pulls_friendly_name():
    xml = "<root><friendlyName>BRAVIA 4K (KD-55X80J)</friendlyName><modelName>KD-55X80J</modelName></root>"
    assert extract_tag(xml, "friendlyName") == "BRAVIA 4K (KD-55X80J)"
    assert extract_tag(xml, "modelName") == "KD-55X80J"


def test_extract_tag_missing_returns_empty():
    assert extract_tag("<root></root>", "friendlyName") == ""
    assert extract_tag("<friendlyName>unterminated", "friendlyName") == ""
