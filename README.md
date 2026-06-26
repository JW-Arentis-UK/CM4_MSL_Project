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

The current build is exposed in the UI and through `GET /api/version`.

## Configuration

By default the app stores configuration in `config/cameras.json`.

Override the config path with:

```bash
set CM4_V3LINK_CONFIG=C:\path\to\cameras.json
```

## systemd

For the quickest single-install setup, clone the repo into your home folder and keep the app, venv, config, and service all in one place.

```bash
cd ~
git clone https://github.com/JW-Arentis-UK/CM4_MSL_Project.git cm4-v3link
cd cm4-v3link
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then install the systemd unit from [`systemd/cm4-v3link.service`](./systemd/cm4-v3link.service):

```bash
sudo cp systemd/cm4-v3link.service /etc/systemd/system/cm4-v3link.service
sudo cp systemd/cm4-v3link-healthcheck.service /etc/systemd/system/cm4-v3link-healthcheck.service
sudo cp systemd/cm4-v3link-healthcheck.timer /etc/systemd/system/cm4-v3link-healthcheck.timer
sudo systemctl daemon-reload
sudo systemctl enable --now cm4-v3link
sudo systemctl enable --now cm4-v3link-healthcheck.timer
sudo systemctl status cm4-v3link
```

You can also run the installer script instead of typing those steps by hand:

```bash
bash install.sh
```

Logs go to the journal:

```bash
journalctl -u cm4-v3link -f
```

The service is configured to restart automatically and uses the repo-local `config/cameras.json` file for persistent settings.

If your CM4 login user is not `cm4`, edit the `User=`, `Group=`, `WorkingDirectory=`, and `ExecStart=` lines in the unit to match your home folder.

## Monitoring

- `GET /api/health` returns a simple remote health summary
- `GET /api/discovery` returns the exact detected camera list
- `GET /api/version` returns the build label and git sha
- The home page footer also shows the current build
- `cm4-v3link-healthcheck` exits non-zero if the API health check fails
- `cm4-v3link-healthcheck.timer` runs the health check every 5 minutes
- `cm4-v3link-update` does `git pull`, reinstalls, and restarts the service
