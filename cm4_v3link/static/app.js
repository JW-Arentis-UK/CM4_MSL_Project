const state = {
  config: null,
  status: null,
  previewSlot: "camera_0",
  settingsSlot: "camera_0",
  previewTimer: null,
  build: null,
};

const el = (id) => document.getElementById(id);

function cameraList() {
  return state.status?.cameras ?? [];
}

function slotToState(slot) {
  return cameraList().find((camera) => camera.slot === slot);
}

function previewPlaceholder(message) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">
      <defs>
        <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="#0b1624" />
          <stop offset="100%" stop-color="#121f31" />
        </linearGradient>
      </defs>
      <rect width="1600" height="900" rx="28" fill="url(#g)" />
      <rect x="110" y="120" width="1380" height="660" rx="24" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="4" />
      <text x="800" y="430" fill="#ecf4ff" font-family="Segoe UI, Arial, sans-serif" font-size="58" text-anchor="middle">${message}</text>
    </svg>
  `.trim();
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function setPreviewStatus(message) {
  el("preview-status").textContent = message;
}

function setPreviewImage(src, statusMessage = "loading preview frame...") {
  setPreviewStatus(statusMessage);
  el("preview-image").src = src;
}

function showPreviewPlaceholder(message) {
  el("preview-image").src = previewPlaceholder(message);
}

function renderSlots() {
  const slots = cameraList();
  const previewSelect = el("preview-slot");
  const settingsSelect = el("settings-slot");
  previewSelect.innerHTML = "";
  settingsSelect.innerHTML = "";

  for (const slot of slots) {
    const optionA = document.createElement("option");
    optionA.value = slot.slot;
    optionA.textContent = `${slot.slot} - ${slot.detected_name ?? "not detected"}`;
    previewSelect.appendChild(optionA);

    const optionB = optionA.cloneNode(true);
    settingsSelect.appendChild(optionB);
  }

  previewSelect.value = state.previewSlot;
  settingsSelect.value = state.settingsSlot;

  renderCameraCards();
  fillSettingsForm();
}

function statusClass(status) {
  if (status === "previewing") return "status-previewing";
  if (status === "ready") return "status-ok";
  if (status === "missing") return "status-missing";
  if (status === "disabled") return "status-disabled";
  if (status === "error") return "status-error";
  return "status-unknown";
}

function renderCameraCards() {
  const root = el("camera-list");
  root.innerHTML = "";
  for (const camera of cameraList()) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <header>
        <strong>${camera.slot}</strong>
        <span class="${statusClass(camera.status)}">${camera.status}</span>
      </header>
      <div>${camera.detected_name ?? "No camera detected"}</div>
      <div class="muted">${camera.message ?? ""}</div>
      <div class="muted">ID: ${camera.detected_id ?? "n/a"}</div>
    `;
    root.appendChild(card);
  }
}

function renderHealthSummary(health) {
  const detected = health?.detected_cameras?.length ?? 0;
  const backend = health?.backend ?? "unknown";
  const configPath = health?.config_path ?? "unknown";
  const camera0 = health?.camera_statuses?.camera_0 ?? "unknown";
  el("health-summary").textContent = `backend ${backend}, ${detected} detected, camera_0 ${camera0}`;
  el("status-summary").textContent = `${cameraList()
    .map((camera) => `${camera.slot}: ${camera.status}`)
    .join(" | ")} | config ${configPath}`;
}

function fillSettingsForm() {
  const camera = slotToState(state.settingsSlot);
  if (!camera) return;
  const settings = camera.settings ?? {};
  const form = el("settings-form");
  for (const field of [
    "name",
    "resolution",
    "fps",
    "exposure",
    "gain",
    "ev_compensation",
    "brightness",
    "contrast",
    "saturation",
    "sharpness",
    "rotate",
  ]) {
    if (form.elements[field]) {
      form.elements[field].value = settings[field] ?? "";
    }
  }
  form.elements.enabled.checked = !!settings.enabled;
  form.elements.flip.checked = !!settings.flip;
}

async function fetchJson(url, options) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response;
}

async function loadStatus() {
  state.status = await fetchJson("/api/status");
  state.build = state.status.build ?? state.build;
  if (state.build?.label) {
    el("build-version").textContent = state.build.label;
    el("footer-build").textContent = state.build.label;
  }
  const cameras = cameraList();
  if (!cameras.length) return;
  state.previewSlot = state.previewSlot || cameras[0].slot;
  state.settingsSlot = state.settingsSlot || cameras[0].slot;
  renderSlots();
  const overall = cameras.some((camera) => camera.status === "previewing")
    ? "Previewing"
    : cameras.some((camera) => camera.detected)
      ? "Ready"
      : "Waiting for camera";
  el("overall-status").textContent = overall;
  renderHealthSummary(state.status);
}

async function loadLogs() {
  const data = await fetchJson("/api/logs");
  const root = el("log-list");
  root.innerHTML = "";
  for (const entry of data.entries || []) {
    const row = document.createElement("div");
    row.className = "card";
    row.textContent = `[${entry.level}] ${entry.timestamp} ${entry.message}`;
    root.appendChild(row);
  }
}

async function loadVersion() {
  const version = await fetchJson("/api/version");
  state.build = version;
  if (version?.label) {
    el("build-version").textContent = version.label;
    el("footer-build").textContent = version.label;
  }
}

async function loadHealth() {
  const health = await fetchJson("/api/health");
  renderHealthSummary({
    ...health,
    detected_cameras: health.detected_cameras ?? [],
  });
}

function wirePreviewEvents() {
  const preview = el("preview-image");
  preview.addEventListener("load", () => {
    const slot = el("preview-slot").value;
    const camera = slotToState(slot);
    const label = camera?.detected_name ?? slot ?? "camera";
    setPreviewStatus(`frame loaded from ${label}`);
  });
  preview.addEventListener("error", () => {
    setPreviewStatus("preview frame failed to load");
    showPreviewPlaceholder("Preview unavailable");
  });
}

function startPreviewTimer() {
  stopPreviewTimer();
  state.previewTimer = window.setInterval(() => {
    const slot = el("preview-slot").value;
    if (!slot) return;
    setPreviewImage(`/api/cameras/${slot}/preview/frame?ts=${Date.now()}`);
  }, 4000);
}

function stopPreviewTimer() {
  if (state.previewTimer) {
    window.clearInterval(state.previewTimer);
    state.previewTimer = null;
  }
}

async function startPreview() {
  const slot = el("preview-slot").value;
  state.previewSlot = slot;
  setPreviewStatus(`starting preview for ${slot}...`);
  showPreviewPlaceholder("Loading preview...");
  await fetchJson(`/api/cameras/${slot}/preview/start`, { method: "POST" });
  setPreviewImage(`/api/cameras/${slot}/preview/frame?ts=${Date.now()}`);
  startPreviewTimer();
  await loadStatus();
}

async function stopPreview() {
  const slot = el("preview-slot").value;
  state.previewSlot = slot;
  await fetchJson(`/api/cameras/${slot}/preview/stop`, { method: "POST" });
  stopPreviewTimer();
  setPreviewStatus("preview stopped");
  showPreviewPlaceholder("Preview stopped");
  await loadStatus();
}

async function takeSnapshot() {
  const slot = el("preview-slot").value;
  state.previewSlot = slot;
  setPreviewStatus(`capturing snapshot from ${slot}...`);
  showPreviewPlaceholder("Capturing snapshot...");
  const response = await fetch(`/api/cameras/${slot}/snapshot`, { method: "POST" });
  if (!response.ok) {
    setPreviewStatus("snapshot failed");
    showPreviewPlaceholder("Snapshot failed");
    throw new Error(await response.text());
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  setPreviewImage(url, `snapshot loaded from ${slot}`);
  setPreviewStatus(`snapshot loaded from ${slot}`);
}

async function applySettings() {
  const slot = el("settings-slot").value;
  state.settingsSlot = slot;
  const form = el("settings-form");
  const payload = {
    name: form.elements.name.value,
    enabled: form.elements.enabled.checked,
    resolution: form.elements.resolution.value,
    fps: Number(form.elements.fps.value || 30),
    exposure: form.elements.exposure.value,
    gain: form.elements.gain.value,
    ev_compensation: Number(form.elements.ev_compensation.value || 0),
    brightness: Number(form.elements.brightness.value || 0),
    contrast: Number(form.elements.contrast.value || 1),
    saturation: Number(form.elements.saturation.value || 1),
    sharpness: Number(form.elements.sharpness.value || 1),
    flip: form.elements.flip.checked,
    rotate: Number(form.elements.rotate.value || 0),
  };
  await fetchJson(`/api/cameras/${slot}/settings`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await loadStatus();
}

async function saveConfig() {
  const config = await fetchJson("/api/config");
  await fetchJson("/api/config", {
    method: "POST",
    body: JSON.stringify(config),
  });
  await loadLogs();
}

function wireEvents() {
  el("preview-slot").addEventListener("change", (event) => {
    state.previewSlot = event.target.value;
  });
  el("settings-slot").addEventListener("change", (event) => {
    state.settingsSlot = event.target.value;
    fillSettingsForm();
  });
  el("start-preview").addEventListener("click", () => startPreview().catch(alert));
  el("stop-preview").addEventListener("click", () => stopPreview().catch(alert));
  el("snapshot").addEventListener("click", () => takeSnapshot().catch(alert));
  el("apply-settings").addEventListener("click", (event) => {
    event.preventDefault();
    applySettings().catch(alert);
  });
  el("save-config").addEventListener("click", () => saveConfig().catch(alert));
  el("refresh-logs").addEventListener("click", () => loadLogs().catch(alert));
}

async function boot() {
  wirePreviewEvents();
  wireEvents();
  showPreviewPlaceholder("Waiting for preview...");
  await loadVersion();
  await loadStatus();
  await loadHealth();
  await loadLogs();
  startPreviewTimer();
  window.setInterval(() => {
    loadStatus().catch(console.error);
    loadHealth().catch(console.error);
    loadLogs().catch(console.error);
  }, 5000);
}

boot().catch((error) => {
  console.error(error);
  el("overall-status").textContent = "Error";
  el("status-summary").textContent = String(error);
});
