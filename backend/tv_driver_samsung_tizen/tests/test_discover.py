from tv_driver_samsung_tizen.remote import name_from_device_info


def test_name_from_device_info_reads_configured_tv_name():
    info = {"device": {"name": "[TV] Living Room", "type": "Samsung SmartTV"}}
    assert name_from_device_info(info) == "[TV] Living Room"


def test_name_from_device_info_missing_fields_returns_empty():
    assert name_from_device_info({}) == ""
    assert name_from_device_info({"device": {}}) == ""
