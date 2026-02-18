import argparse
import importlib

app_main = importlib.import_module("inno.main")


class FakeCapture:
    def __init__(self, first_read_ok: bool = True, fail_reads: int = 0) -> None:
        self.set_calls: list[tuple[int, float]] = []
        self.released = False
        self._first_read_ok = first_read_ok
        self._fail_reads = fail_reads
        self._read_count = 0

    def set(self, prop_id: int, prop_value: float) -> bool:
        self.set_calls.append((prop_id, prop_value))
        return True

    def read(self) -> tuple[bool, object]:
        self._read_count += 1
        if self._read_count <= self._fail_reads:
            return False, object()
        if self._read_count == 1 and not self._first_read_ok:
            return False, object()
        return True, object()

    def release(self) -> None:
        self.released = True


class FakeCV2:
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5
    CAP_PROP_FOURCC = 6
    WINDOW_NORMAL = 0
    WINDOW_AUTOSIZE = 1

    def __init__(self) -> None:
        self.capture = FakeCapture()
        self.named_window_calls: list[tuple[str, int]] = []
        self.resize_calls: list[tuple[str, int, int]] = []

    def VideoWriter_fourcc(self, *chars: str) -> int:
        assert chars == tuple("MJPG")
        return 1196444237

    def namedWindow(self, name: str, flags: int) -> None:
        self.named_window_calls.append((name, flags))

    def resizeWindow(self, name: str, width: int, height: int) -> None:
        self.resize_calls.append((name, width, height))

    def imshow(self, _name: str, _frame: object) -> None:
        return None

    def waitKey(self, _delay: int) -> int:
        return ord("q")

    def destroyAllWindows(self) -> None:
        return None


def test_run_sets_fixed_capture_defaults(monkeypatch) -> None:
    args = argparse.Namespace(camera_source="0")
    cv2 = FakeCV2()
    monkeypatch.setattr(app_main, "open_capture", lambda _source, _cv2: cv2.capture)

    app_main.run(args, cv2)

    assert cv2.capture.set_calls == [
        (cv2.CAP_PROP_FRAME_WIDTH, 1920.0),
        (cv2.CAP_PROP_FRAME_HEIGHT, 1080.0),
        (cv2.CAP_PROP_FPS, 30.0),
        (cv2.CAP_PROP_FOURCC, 1196444237.0),
    ]
    assert cv2.named_window_calls == [(app_main.WINDOW_NAME, cv2.WINDOW_NORMAL)]
    assert cv2.resize_calls == [(app_main.WINDOW_NAME, 1280, 720)]
    assert cv2.capture.released


def test_run_retries_with_driver_defaults_when_initial_read_fails(monkeypatch) -> None:
    args = argparse.Namespace(camera_source="0")
    cv2 = FakeCV2()
    monkeypatch.setattr(app_main, "STARTUP_READ_ATTEMPTS", 3)
    monkeypatch.setattr(app_main, "STARTUP_READ_DELAY_SECONDS", 0.0)
    capture_with_defaults = FakeCapture(fail_reads=3)
    capture_with_driver_defaults = FakeCapture(first_read_ok=True)
    captures = iter([capture_with_defaults, capture_with_driver_defaults])
    monkeypatch.setattr(app_main, "open_capture", lambda _source, _cv2: next(captures))

    app_main.run(args, cv2)

    assert capture_with_defaults.set_calls == [
        (cv2.CAP_PROP_FRAME_WIDTH, 1920.0),
        (cv2.CAP_PROP_FRAME_HEIGHT, 1080.0),
        (cv2.CAP_PROP_FPS, 30.0),
        (cv2.CAP_PROP_FOURCC, 1196444237.0),
    ]
    assert cv2.named_window_calls == [(app_main.WINDOW_NAME, cv2.WINDOW_NORMAL)]
    assert cv2.resize_calls == [(app_main.WINDOW_NAME, 1280, 720)]
    assert capture_with_driver_defaults.set_calls == []
    assert capture_with_defaults.released
    assert capture_with_driver_defaults.released
