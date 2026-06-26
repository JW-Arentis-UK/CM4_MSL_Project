#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="/etc/systemd/system/cm4-v3link.service"

if [[ ! -d "${ROOT_DIR}/.git" ]]; then
  echo "Run this from the cloned cm4-v3link repo."
  exit 1
fi

python3 -m venv "${ROOT_DIR}/.venv"
source "${ROOT_DIR}/.venv/bin/activate"
pip install -e "${ROOT_DIR}"

sudo install -m 0644 "${ROOT_DIR}/systemd/cm4-v3link.service" "${SERVICE_FILE}"
sudo systemctl daemon-reload
sudo systemctl enable --now cm4-v3link
sudo systemctl status --no-pager cm4-v3link

