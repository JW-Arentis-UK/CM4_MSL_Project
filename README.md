# CM4 V3Link Camera Control Tool

Phase 1 scaffold for a Raspberry Pi CM4 tool that manages Arducam V3Link cameras.

## What is included

- Slot-based camera model for `camera_0` and `camera_1`
- JSON config load/save
- FastAPI REST API
- Basic browser UI
- Snapshot and preview polling flow
- In-memory recent logs
- systemd service unit example

## Run locally

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .
cm4-v3link
```

The app listens on `http://127.0.0.1:8000` by default.

## Configuration

By default the app stores configuration in `config/cameras.json`.

Override the config path with:

```bash
set CM4_V3LINK_CONFIG=C:\path\to\cameras.json
```

## systemd

Install the unit from [`systemd/cm4-v3link.service`](./systemd/cm4-v3link.service) and set `CM4_V3LINK_CONFIG` to a writable path such as `/var/lib/cm4-v3link/cameras.json`.

