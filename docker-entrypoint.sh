#!/usr/bin/env bash
# Starts the FastAPI backend (:8000) and the Next.js frontend (:3000) together.
# Before starting it frees those two ports so nothing else can hold them, and it
# tears both processes down together if either one exits.
set -euo pipefail

FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "▶ Ensuring ports ${FRONTEND_PORT} and ${BACKEND_PORT} are free…"
for port in "${FRONTEND_PORT}" "${BACKEND_PORT}"; do
  # fuser (from psmisc) kills whatever is bound to the TCP port. Harmless if free.
  fuser -k "${port}/tcp" >/dev/null 2>&1 || true
done
sleep 1

echo "▶ Starting backend on :${BACKEND_PORT}…"
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

echo "▶ Starting frontend on :${FRONTEND_PORT}…"
cd /app/frontend
node_modules/.bin/next start -p "${FRONTEND_PORT}" -H 0.0.0.0 &
FRONTEND_PID=$!

# Forward termination signals to both children.
term() {
  echo "▶ Shutting down…"
  kill "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
}
trap term SIGINT SIGTERM

# If either process exits, bring the whole container down.
wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
EXIT_CODE=$?
echo "▶ A service exited (code ${EXIT_CODE}); stopping the other."
kill "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
exit "${EXIT_CODE}"
