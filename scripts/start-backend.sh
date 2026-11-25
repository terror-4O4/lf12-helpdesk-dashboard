#!/usr/bin/env bash
# Startet das Backend auf macOS/Linux. Aufruf aus dem Repo-Hauptordner:
#   ./scripts/start-backend.sh
set -e

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Fehlt: .env  ->  cp .env.example .env"
  exit 1
fi

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

# Python 3.11 oder neuer nötig
if ! python -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  echo "Python zu alt oder nicht gefunden. Benötigt wird 3.11 oder neuer."
  echo "macOS: brew install python@3.13, dann .venv löschen und mit python3.13 -m venv .venv neu anlegen."
  exit 1
fi

# Host und Port aus der .env lesen (Standard: nur lokal erreichbar)
APP_HOST=$(grep -E '^APP_HOST=' .env | cut -d= -f2)
APP_PORT=$(grep -E '^APP_PORT=' .env | cut -d= -f2)

exec python -m uvicorn backend.app:app --reload --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}"
