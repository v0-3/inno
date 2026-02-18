import pytest

from inno.main import normalize_camera_source, parse_args


def test_camera_source_numeric_string_to_int() -> None:
    assert normalize_camera_source("2") == 2


def test_camera_source_dev_video_path_to_index() -> None:
    source = "/dev/video0"
    assert normalize_camera_source(source) == 0


def test_parse_args_custom_source() -> None:
    args = parse_args(["--camera-source", "1"])
    assert args.camera_source == "1"


def test_parse_args_default_source_is_index_0() -> None:
    args = parse_args([])
    assert args.camera_source == "0"


def test_parse_args_rejects_unknown_flag() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--unsupported-flag", "123"])
