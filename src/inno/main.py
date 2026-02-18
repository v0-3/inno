from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

WINDOW_NAME = "Webcam Feed"
CAPTURE_WIDTH = 1920
CAPTURE_HEIGHT = 1080
CAPTURE_FPS = 30
WINDOW_DEFAULT_WIDTH = 1280
WINDOW_DEFAULT_HEIGHT = 720
STARTUP_READ_ATTEMPTS = 10
STARTUP_READ_DELAY_SECONDS = 0.02


class CameraError(Exception):
    """Raised when the camera cannot be started or read."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open a webcam/video source.")
    parser.add_argument(
        "--camera-source",
        default="/dev/video0",
        help="Camera source index (e.g. 0) or video path/URL.",
    )
    return parser.parse_args(argv)


def normalize_camera_source(camera_source: str | int) -> int | str:
    if isinstance(camera_source, int):
        return camera_source
    stripped = camera_source.strip()
    if stripped.startswith("/dev/video"):
        suffix = stripped.removeprefix("/dev/video")
        if suffix.isdigit():
            return int(suffix)
    if stripped.isdigit():
        return int(stripped)
    return stripped


def open_capture(source: int | str, cv2_module: Any) -> Any:
    attempts: list[tuple[int | str, int | None, str]] = [(source, None, "default")]
    if isinstance(source, int):
        attempts.append((f"/dev/video{source}", None, "dev-path"))

    seen: set[tuple[str, int | None]] = set()
    attempted_labels: list[str] = []
    for candidate_source, backend, label in attempts:
        dedupe_key = (repr(candidate_source), backend)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        attempted_labels.append(label)

        capture = (
            cv2_module.VideoCapture(candidate_source)
            if backend is None
            else cv2_module.VideoCapture(candidate_source, backend)
        )
        if capture and capture.isOpened():
            return capture
        if capture:
            capture.release()

    extra_hint = ""
    if isinstance(source, str) and source.startswith("/dev/video"):
        if not Path(source).exists():
            extra_hint = " Device path does not exist."
        elif not os.access(source, os.R_OK | os.W_OK):
            extra_hint = " Permission denied for camera device."

    raise CameraError(
        f"Unable to open camera source: {source}. "
        f"Tried: {', '.join(attempted_labels)}.{extra_hint}"
    )


def read_initial_frame(capture: Any) -> tuple[bool, Any]:
    for attempt in range(STARTUP_READ_ATTEMPTS):
        ok, frame = capture.read()
        if ok:
            return True, frame
        if attempt < STARTUP_READ_ATTEMPTS - 1:
            time.sleep(STARTUP_READ_DELAY_SECONDS)
    return False, None


def set_capture_property(
    capture: Any, cv2_module: Any, property_name: str, property_value: float
) -> None:
    if not hasattr(cv2_module, property_name):
        return

    property_id = int(getattr(cv2_module, property_name))
    set_ok = bool(capture.set(property_id, property_value))
    if set_ok:
        return

    actual_value: float | None = None
    if hasattr(capture, "get"):
        try:
            raw_value = capture.get(property_id)
            if isinstance(raw_value, (int, float)):
                actual_value = float(raw_value)
        except Exception:
            actual_value = None

    matches_requested = False
    if actual_value is not None:
        if property_name == "CAP_PROP_FOURCC":
            matches_requested = int(actual_value) == int(property_value)
        else:
            matches_requested = abs(actual_value - property_value) <= 0.5

    if matches_requested:
        return

    actual_suffix = f" (actual={actual_value})" if actual_value is not None else ""
    print(
        (
            "Warning: OpenCV ignored default capture setting "
            f"{property_name}={property_value}.{actual_suffix}"
        ),
        file=sys.stderr,
    )


def apply_capture_defaults(capture: Any, cv2_module: Any) -> None:
    set_capture_property(
        capture, cv2_module, "CAP_PROP_FRAME_WIDTH", float(CAPTURE_WIDTH)
    )
    set_capture_property(
        capture, cv2_module, "CAP_PROP_FRAME_HEIGHT", float(CAPTURE_HEIGHT)
    )
    set_capture_property(capture, cv2_module, "CAP_PROP_FPS", float(CAPTURE_FPS))

    if hasattr(cv2_module, "CAP_PROP_FOURCC") and hasattr(
        cv2_module, "VideoWriter_fourcc"
    ):
        default_fourcc = cv2_module.VideoWriter_fourcc("M", "J", "P", "G")
        set_capture_property(
            capture, cv2_module, "CAP_PROP_FOURCC", float(default_fourcc)
        )


def run(
    args: argparse.Namespace,
    cv2_module: Any,
) -> None:
    source = normalize_camera_source(args.camera_source)
    capture = None
    first_frame = None
    failure_reasons: list[str] = []
    mode_specs = [
        ("requested defaults", True),
        ("driver defaults", False),
    ]

    for mode_name, apply_defaults in mode_specs:
        candidate_capture = open_capture(source, cv2_module)
        try:
            if apply_defaults:
                apply_capture_defaults(candidate_capture, cv2_module)

            ok, frame = read_initial_frame(candidate_capture)
            if ok:
                capture = candidate_capture
                first_frame = frame
                break

            failure_reasons.append(
                (
                    f"{mode_name}: failed to read initial frame after "
                    f"{STARTUP_READ_ATTEMPTS} attempts"
                )
            )
            print(
                f"Warning: {mode_name} failed to read an initial frame; retrying.",
                file=sys.stderr,
            )
        finally:
            if capture is not candidate_capture:
                candidate_capture.release()

    if capture is None or first_frame is None:
        details = f" ({'; '.join(failure_reasons)})" if failure_reasons else ""
        raise CameraError(f"Failed to read frame from camera source.{details}")

    try:
        window_flags = getattr(cv2_module, "WINDOW_NORMAL", 0)
        cv2_module.namedWindow(WINDOW_NAME, window_flags)
        if hasattr(cv2_module, "resizeWindow"):
            cv2_module.resizeWindow(
                WINDOW_NAME,
                WINDOW_DEFAULT_WIDTH,
                WINDOW_DEFAULT_HEIGHT,
            )

        frame = first_frame
        while True:
            cv2_module.imshow(WINDOW_NAME, frame)

            key = cv2_module.waitKey(1) & 0xFF
            if key == ord("q"):
                break

            ok, frame = capture.read()
            if not ok:
                raise CameraError("Failed to read frame from camera source.")
    finally:
        capture.release()
        cv2_module.destroyAllWindows()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        import cv2

        run(args, cv2)
    except CameraError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
