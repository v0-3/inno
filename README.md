## Inno

Lightweight OpenCV webcam viewer managed with `uv`.

### Requirements

- Python `>=3.10`
- A working camera source (default: `0`)

### Setup

```bash
uv sync
```

### Run

Default source:

```bash
uv run inno
```

Custom source examples:

```bash
uv run inno --camera-source 1
uv run inno --camera-source 2
```

### Controls

- Press `q` to quit.

### Runtime Defaults

- Camera source: `0`
- Capture width: `1920`
- Capture height: `1080`
- Capture FPS: `30`
- Capture pixel format: `MJPG`
- Window default size: `1280x720`

If reading an initial frame fails with requested capture defaults, the app retries with driver defaults before exiting.
