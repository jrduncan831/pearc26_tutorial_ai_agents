#!/usr/bin/env bash
set -euo pipefail

########################################
# Configuration
########################################

# Default Ollama models directory if OLLAMA_MODELS is not set on host
DEFAULT_OLLAMA_MODELS="$HOME/.ollama/models"  # typical on macOS/Linux

# Default Hugging Face cache directory if HF_HOME is not set on host
DEFAULT_HF_HOME="$HOME/.cache/huggingface"    # typical HF cache root on macOS/Linux [web:11][web:17][web:20]

# Docker image
BOOTCAMP_IMAGE="gjaffe/bootcamp_container:0.79"

# Container name for the running environment
CONTAINER_NAME="bootcamp_jupyter"

# Jupyter port on host
HOST_PORT=8888

# Optional log file on host
LOG_FILE="${HOME}/.bootcamp_jupyter.log"

########################################
# Resolve paths and environment
########################################

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

# Ensure OLLAMA_MODELS is set on host
if [[ -z "${OLLAMA_MODELS:-}" ]]; then
  echo "Host OLLAMA_MODELS is not set. Using default: $DEFAULT_OLLAMA_MODELS"
  export OLLAMA_MODELS="$DEFAULT_OLLAMA_MODELS"
fi

# Create models directory if it does not exist
if [[ ! -d "$OLLAMA_MODELS" ]]; then
  echo "Creating Ollama models directory at: $OLLAMA_MODELS"
  mkdir -p "$OLLAMA_MODELS"
fi

# Ensure HF_HOME is set on host
if [[ -z "${HF_HOME:-}" ]]; then
  echo "Host HF_HOME is not set. Using default: $DEFAULT_HF_HOME"
  export HF_HOME="$DEFAULT_HF_HOME"
fi

# Create HF_HOME directory if it does not exist
if [[ ! -d "$HF_HOME" ]]; then
  echo "Creating Hugging Face cache directory at: $HF_HOME"
  mkdir -p "$HF_HOME"
fi

########################################
# Helpers
########################################

open_browser() {
  local url="$1"

  case "$OSTYPE" in
    darwin*) open "$url" ;;          # macOS default browser
    linux*)  xdg-open "$url" ;;      # Linux default browser
    *)       python3 -c "import webbrowser; webbrowser.open('$url')" ;;
  esac
}

# Ask Jupyter inside the container for the running server list and pull the first URL.
get_jupyter_url() {
  local container="$1"

  docker exec "$container" bash -lc \
    "jupyter lab list 2>/dev/null | awk '/http.*token/ {print \$1; exit}'"
}

wait_for_token_url() {
  local container="$1"
  local timeout="${2:-180}"
  local start_ts now
  local url=""

  echo "Waiting for Jupyter token URL via 'jupyter lab list' inside container..."

  start_ts=$(date +%s)

  while true; do
    # Try to get the URL from Jupyter itself
    url="$(get_jupyter_url "$container" | head -n1 || true)"

    if [[ -n "$url" ]]; then
      echo "Found Jupyter token URL: $url"
      open_browser "$url"
      return 0
    fi

    now=$(date +%s)
    if (( now - start_ts >= timeout )); then
      echo "Timed out waiting for token URL; you can copy it manually from logs."
      return 1
    fi

    sleep 1
  done
}

cleanup() {
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

########################################
# Cleanup any existing container
########################################

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "Removing existing container '${CONTAINER_NAME}'..."
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

########################################
# Launch container with Jupyter Lab
########################################

echo "Starting container '$CONTAINER_NAME' from image '$BOOTCAMP_IMAGE'..."
echo "Using OLLAMA_MODELS=$OLLAMA_MODELS"
echo "Using HF_HOME=$HF_HOME"
echo "Mounting:"
echo "  - Models: $OLLAMA_MODELS"
echo "  - HF cache: $HF_HOME"
echo "  - Script dir: $SCRIPT_DIR"
echo "Exposing Jupyter Lab on host port $HOST_PORT"

docker run --rm -d \
  --name "$CONTAINER_NAME" \
  -e OLLAMA_MODELS="$OLLAMA_MODELS" \
  -e HF_HOME="$HF_HOME" \
  -v "$OLLAMA_MODELS":"$OLLAMA_MODELS" \
  -v "$HF_HOME":"$HF_HOME" \
  -v "$SCRIPT_DIR":"$SCRIPT_DIR" \
  -p "$HOST_PORT:8888" \
  "$BOOTCAMP_IMAGE" \
  bash -lc "
    set -euo pipefail
    cd \"$SCRIPT_DIR\"
    echo \"Launching Jupyter Lab in \$(pwd) with OLLAMA_MODELS=\$OLLAMA_MODELS and HF_HOME=\$HF_HOME\"
    exec jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
  "

########################################
# Logs + token watcher
########################################

# Stream logs into your terminal; optionally tee to a file.
if [[ -n "${LOG_FILE:-}" ]]; then
  docker logs -f "$CONTAINER_NAME" | tee "$LOG_FILE" &
else
  docker logs -f "$CONTAINER_NAME" &
fi
LOGS_PID=$!

# In parallel, wait for the token URL via jupyter lab list and open it.
wait_for_token_url "$CONTAINER_NAME" 180 &
TOKEN_PID=$!

# Wait for token watcher to complete (success or timeout)
wait "$TOKEN_PID" || true

# Keep logs visible until container exits
wait "$LOGS_PID"