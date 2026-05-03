#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

load_env() {
  if [[ ! -f ".env" ]]; then
    return
  fi

  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
}

run_proxy() {
  load_env

  local python_exe="$SCRIPT_DIR/.venv/bin/python"
  if [[ ! -x "$python_exe" ]]; then
    echo "Python in .venv wurde nicht gefunden. Erwartet: $python_exe" >&2
    echo "Einmalig ausfuehren: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
    return 1
  fi

  "$python_exe" "$SCRIPT_DIR/mqtt-proxy.py" "$@"
}

while true; do
  set +e
  run_proxy "$@"
  exit_code=$?
  set -e

  if [[ "$exit_code" != "75" ]]; then
    exit "$exit_code"
  fi

  echo ".env geaendert - starte Proxy mit neuer Konfiguration neu..."
done
