#!/usr/bin/env bash
# Install Ollama and pull the default local model for the evaluation suite.
set -euo pipefail

MODEL="${1:-llama3.1:8b}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Installing Ollama via Homebrew..."
  if command -v brew >/dev/null 2>&1; then
    brew install ollama
  else
    echo "Homebrew not found. Install Ollama from https://ollama.com/download" >&2
    exit 1
  fi
fi

# Start the server (idempotent).
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Starting Ollama service..."
  brew services start ollama 2>/dev/null || (ollama serve >/tmp/ollama-serve.log 2>&1 &)
  sleep 6
fi

echo "Pulling model: $MODEL"
ollama pull "$MODEL"
echo "Done. Available models:"
ollama list
