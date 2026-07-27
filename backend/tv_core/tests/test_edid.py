from tv_core import edid


def test_connected_displays_returns_empty_when_drm_path_missing(monkeypatch, tmp_path):
    missing_path = tmp_path / "nonexistent_drm"
    monkeypatch.setattr(edid, "DRM_PATH", str(missing_path))
    assert edid.connected_displays() == []
