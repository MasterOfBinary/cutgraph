from cutgraph.binaries import BinaryInfo, MissingBinaryError, require_binary


def test_require_binary_returns_path_from_locator() -> None:
    info = require_binary("ffmpeg", locator=lambda _name: "/usr/bin/ffmpeg")

    assert info == BinaryInfo(name="ffmpeg", path="/usr/bin/ffmpeg", available=True)


def test_require_binary_reports_actionable_missing_binary() -> None:
    try:
        require_binary("ffprobe", locator=lambda _name: None)
    except MissingBinaryError as exc:
        assert "Install FFmpeg/ffprobe" in str(exc)
    else:
        raise AssertionError("Expected MissingBinaryError")
