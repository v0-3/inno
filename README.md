## Inno

Simple Python OpenCV app managed with `uv`.  
It opens a webcam/video source with fixed capture defaults.

### Install dependencies

```bash
uv sync
```

### Run

```bash
uv run inno
```

With a custom source:

```bash
uv run inno --camera-source 1
```

### Controls

- Press `q` to quit.

### Defaults

- Camera source: `/dev/video0`
- Frame width: `1920`
- Frame height: `1080`
- FPS: `30`
- Pixel format: `MJPG`
