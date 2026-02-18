from types import SimpleNamespace

from inno.main import CameraError, open_capture


class FakeCapture:
    def __init__(self, opened: bool) -> None:
        self._opened = opened
        self.released = False

    def isOpened(self) -> bool:
        return self._opened

    def release(self) -> None:
        self.released = True


class FakeCV2:
    def __init__(self, success_target: tuple[object, int | None]) -> None:
        self.success_target = success_target
        self.calls: list[tuple[object, int | None]] = []

    def VideoCapture(self, source: object, backend: int | None = None) -> FakeCapture:
        self.calls.append((source, backend))
        return FakeCapture((source, backend) == self.success_target)


def test_open_capture_uses_default_backend() -> None:
    cv2 = FakeCV2(success_target=(0, None))

    capture = open_capture(0, cv2)

    assert capture.isOpened()
    assert cv2.calls == [(0, None)]


def test_open_capture_index_falls_back_to_dev_path() -> None:
    cv2 = FakeCV2(success_target=("/dev/video0", None))

    capture = open_capture(0, cv2)

    assert capture.isOpened()
    assert cv2.calls == [(0, None), ("/dev/video0", None)]


def test_open_capture_raises_with_attempt_list() -> None:
    cv2 = FakeCV2(success_target=("never", None))

    try:
        open_capture("/dev/video9", cv2)
    except CameraError as exc:
        message = str(exc)
        assert "Tried:" in message
        assert "default" in message
    else:
        raise AssertionError("Expected CameraError")
