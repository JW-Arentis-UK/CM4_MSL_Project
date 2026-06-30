#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  echo "Run install.sh first so the virtualenv exists."
  exit 1
fi

"${ROOT_DIR}/.venv/bin/python" -m cm4_v3link.update
