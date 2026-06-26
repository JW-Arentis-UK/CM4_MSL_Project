# CM4 V3Link Camera Control Tool Plan

## Purpose
Build a Raspberry Pi CM4 tool for Arducam V3Link cameras used alongside Videosoft software.

Videosoft owns the main VMS and streaming workflow. This tool focuses on:

- Camera access and discovery
- Camera setup and tuning
- Health checks and availability monitoring
- Snapshot and preview control
- Persisting camera configuration

The implementation should support the current single-camera setup and the planned two-camera layout without hard-coding a one-camera design.

## Target Hardware

Current:

- Raspberry Pi CM4
- Arducam V3Link receiver
- One fitted camera
- IMX219 currently working
- USB microphone may be added later

Planned:

- Two Arducam V3Link cameras
- `camera_0` enabled by default
- `camera_1` present in the model but disabled by default until installed and configured

## Core Design Principles

1. Use a camera slot model from day one.
2. Keep the first implementation Python-first for speed of testing.
3. Prefer FastAPI for the web UI and REST API.
4. Use `libcamera`, `rpicam`, or `Picamera2` where practical.
5. Keep the camera control layer modular so GStreamer or C++ can replace parts later.
6. Treat Videosoft as external to this tool, not something to re-implement.

## Camera Slot Model

The system should represent each camera as a slot, not as a single global camera.

Slots:

- `camera_0`
- `camera_1`

Each slot should track:

- `enabled` / `disabled`
- detected libcamera ID
- name
- resolution
- FPS
- bitrate
- exposure
- gain
- EV compensation
- white balance
- brightness
- contrast
- saturation
- sharpness
- image flip/rotate
- snapshot support
- preview support
- health status

## Phase 1 Scope

Phase 1 is about stable camera access, control, and visibility.

### Required capabilities

- Detect available libcamera cameras
- Map detected cameras into the slot model
- Show `camera_0` as active when detected
- Show `camera_1` as missing or disabled by default
- Start and stop preview for `camera_0`
- Capture snapshots for `camera_0`
- Support manual tuning of exposure, gain, and EV compensation
- Save settings to JSON config
- Expose a web UI on the CM4
- Expose REST API endpoints for status, config, and snapshot capture
- Run as a `systemd` service

### Non-goals for Phase 1

- Full dual-camera capture pipeline
- ONVIF integration
- Videosoft-specific integration logic
- MSL Red/Amber/Green color detection
- ROI-based exposure control
- USB mic/audio detection
- ONVIF events for alarms
- WebRTC/RTSP helper stream

## Suggested Architecture

### 1. Python application layer

Use a small FastAPI service that exposes:

- REST endpoints for camera status and config
- snapshot capture endpoints
- preview control endpoints
- web UI pages
- static assets for the browser interface

### 2. Camera service layer

Create a dedicated camera abstraction for:

- device discovery
- slot assignment
- camera lifecycle
- parameter application
- snapshot capture
- preview lifecycle
- health checks

This layer should hide the specific backend details so the implementation can swap between Picamera2, `libcamera`, or another backend later.

### 3. Configuration layer

Store the current configuration in JSON.

Responsibilities:

- load config at boot
- validate slot definitions
- persist tuning settings
- remember enabled/disabled state
- keep runtime values separate from saved defaults where needed

### 4. UI layer

Use a simple web UI served by the same FastAPI app.

UI should include:

- camera list
- camera status
- preview window
- snapshot button
- exposure/gain/EV controls
- resolution/FPS controls
- save/apply config actions
- basic logs

## REST API Outline

Suggested endpoints:

- `GET /api/status` - overall system and camera health
- `GET /api/cameras` - slot list, detected IDs, enabled state, status
- `GET /api/cameras/{slot}` - details for one camera slot
- `POST /api/cameras/{slot}/apply` - apply current settings
- `POST /api/cameras/{slot}/snapshot` - capture a snapshot
- `POST /api/cameras/{slot}/preview/start` - start preview
- `POST /api/cameras/{slot}/preview/stop` - stop preview
- `GET /api/config` - read saved configuration
- `POST /api/config` - save configuration
- `GET /api/logs` - basic recent logs

If the preview is browser-based, define whether it is delivered as:

- a generated JPEG stream
- an MJPEG endpoint
- a simple polling snapshot panel

Pick the simplest stable option first.

## Configuration Shape

Keep config explicit and slot-based.

Example structure:

```json
{
  "cameras": {
    "camera_0": {
      "enabled": true,
      "name": "Front Camera",
      "resolution": "1920x1080",
      "fps": 30,
      "bitrate": 8000000,
      "exposure": "auto",
      "gain": "auto",
      "ev_compensation": 0,
      "white_balance": "auto",
      "brightness": 0.0,
      "contrast": 1.0,
      "saturation": 1.0,
      "sharpness": 1.0,
      "flip": false,
      "rotate": 0
    },
    "camera_1": {
      "enabled": false,
      "name": "Spare Camera",
      "resolution": "1920x1080",
      "fps": 30,
      "bitrate": 8000000,
      "exposure": "auto",
      "gain": "auto",
      "ev_compensation": 0,
      "white_balance": "auto",
      "brightness": 0.0,
      "contrast": 1.0,
      "saturation": 1.0,
      "sharpness": 1.0,
      "flip": false,
      "rotate": 0
    }
  }
}
```

## Health Model

Each slot should surface a health summary such as:

- detected
- missing
- disabled
- previewing
- snapshot-ready
- error state with message

Useful health signals:

- camera present or absent
- backend initialization success
- current streaming/preview state
- last snapshot result
- recent capture failures
- stale or disconnected camera ID

## Systemd Service Plan

Run the application as a `systemd` service on the CM4.

Service responsibilities:

- start on boot
- restart on failure
- load JSON config
- expose the web UI/API on a fixed port
- write logs to the journal

Deliverables should include:

- service unit file
- install/start instructions
- log location guidance

## Suggested Implementation Phases

### Phase 1

- Repo scaffold
- FastAPI service
- slot-based camera discovery
- config load/save
- snapshot endpoint
- preview control
- web UI
- logging
- `systemd` unit

### Phase 2

- Full dual-camera support
- richer camera state transitions
- more robust parameter validation
- better preview handling
- live status refresh in UI

### Phase 3

- Videosoft integration helpers if needed
- ONVIF support if required
- event hooks
- audio input support
- alarm logic

### Phase 4

- advanced exposure/tone tuning
- ROI controls
- helper streams for downstream tools
- backend swap options for performance or packaging

## Acceptance Criteria for Phase 1

Phase 1 is done when:

- The service detects available libcamera devices
- `camera_0` is shown as active when present
- `camera_1` exists in config even if disabled or missing
- preview can be started and stopped for `camera_0`
- a snapshot can be captured for `camera_0`
- exposure, gain, and EV can be adjusted manually
- settings persist to JSON and reload on restart
- the web UI shows status, controls, and logs
- the app can run under `systemd`

## Risks And Notes

- Picamera2 and libcamera behavior can differ by OS image and camera module, so discovery and parameter mapping should be tested early on the real CM4.
- Preview delivery needs to stay simple at first to avoid fighting browser compatibility.
- Camera parameter names can vary between backends, so the code should translate from UI/config terms into backend-specific calls in one place.
- The planned dual-camera setup should stay dormant in config until the second camera is actually installed and verified.

## Recommended Next Build Order

1. Create the Python project scaffold.
2. Implement config loading/saving and slot validation.
3. Add camera discovery and status reporting.
4. Add snapshot capture.
5. Add preview start/stop.
6. Build the web UI.
7. Add the REST API.
8. Add the `systemd` service.
9. Test on the CM4 with the actual V3Link receiver and IMX219.

