#!/usr/bin/env bash
set -euo pipefail


########################################
# Configuration
########################################


# Required space in GB for LLM storage
REQUIRED_SPACE_GB=33

# Default Ollama models directory if OLLAMA_MODELS is not set on host
DEFAULT_OLLAMA_MODELS="$HOME/.ollama/models"  # typical on macOS/Linux

# Default Hugging Face cache directory if HF_HOME is not set on host
# On macOS/Linux, Hugging Face Hub defaults to ~/.cache/huggingface when HF_HOME is unset.
DEFAULT_HF_HOME="$HOME/.cache/huggingface"

# Docker image used to perform downloads / builds
BOOTCAMP_IMAGE="gjaffe/bootcamp_container:0.79"

# Models to pull (space-separated string for simple expansion inside container)
MODELS="gemma3:27b qwen3:8b"

# Apptainer configuration
APPTAINER_IMAGE_NAME="python_3.10-slim.sif"
APPTAINER_DOCKER_URI="docker://python:3.10-slim"

# Directory where the .sif should live (relative to repo root on host)
HPC_AGENT_DIR_NAME="05_hpc_agent_integration"


########################################
# Resolve paths and environment
########################################


SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Absolute path to 05_hpc_agent_integration on host
HPC_AGENT_DIR="$PARENT_DIR/$HPC_AGENT_DIR_NAME"


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

# Ensure Apptainer target directory exists on host
if [[ ! -d "$HPC_AGENT_DIR" ]]; then
  echo "Creating Apptainer target directory at: $HPC_AGENT_DIR"
  mkdir -p "$HPC_AGENT_DIR"
fi


########################################
# Confirm disk usage
########################################


echo "The container and selected models will require approximately ${REQUIRED_SPACE_GB} GB of disk space."
echo "Models to be downloaded (Ollama):"
for m in $MODELS; do
  echo "  - $m"
done
echo "Hugging Face cache directory: $HF_HOME (for all-MiniLM-L6-v2)"
echo "Apptainer .sif image will be written to: $HPC_AGENT_DIR/$APPTAINER_IMAGE_NAME"
echo "  (source Docker image: $APPTAINER_DOCKER_URI)"

read -r -p "Do you want to continue? [y/N]: " CONFIRM
CONFIRM="${CONFIRM:-N}"

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Aborting model installation."
  exit 1
fi


########################################
# Pull container image (only if missing)
########################################


if ! docker image inspect "$BOOTCAMP_IMAGE" >/dev/null 2>&1; then
  echo "Image $BOOTCAMP_IMAGE not found locally, pulling from registry..."
  docker pull "$BOOTCAMP_IMAGE"
else
  echo "Image $BOOTCAMP_IMAGE already present locally; skipping docker pull."
fi


########################################
# Run container, build Apptainer image, and download models
########################################


echo "Starting temporary container to build Apptainer image and download Ollama + HF models..."

docker run --rm \
  -e OLLAMA_MODELS="$OLLAMA_MODELS" \
  -e MODELS="$MODELS" \
  -e HF_HOME="$HF_HOME" \
  -e APPTAINER_IMAGE_NAME="$APPTAINER_IMAGE_NAME" \
  -e APPTAINER_DOCKER_URI="$APPTAINER_DOCKER_URI" \
  -e HPC_AGENT_DIR="$HPC_AGENT_DIR" \
  -v "$OLLAMA_MODELS":"$OLLAMA_MODELS" \
  -v "$HF_HOME":"$HF_HOME" \
  -v "$PARENT_DIR":"$PARENT_DIR" \
  -v "$HPC_AGENT_DIR":"$HPC_AGENT_DIR" \
  "$BOOTCAMP_IMAGE" \
  bash -lc '
    set -euo pipefail
    echo "Using OLLAMA_MODELS=$OLLAMA_MODELS"
    echo "Using HF_HOME=$HF_HOME"
    echo "Ollama models to pull: $MODELS"
    echo "HPC agent directory (Apptainer target)=$HPC_AGENT_DIR"
    echo "Apptainer Docker URI=$APPTAINER_DOCKER_URI"
    echo "Apptainer SIF name=$APPTAINER_IMAGE_NAME"

    cd "'"$PARENT_DIR"'"

    ########################################
    # Build Apptainer image from Docker URI
    ########################################

    # Ensure apptainer is installed inside this container image.
    # Using apptainer build to convert docker://python:3.10-slim into a SIF file.
    # Typical pattern: apptainer build <output.sif> docker://<image> [web:4][web:8][web:9]
    echo "Building Apptainer image $APPTAINER_IMAGE_NAME from $APPTAINER_DOCKER_URI..."
    apptainer build "$HPC_AGENT_DIR/$APPTAINER_IMAGE_NAME" "$APPTAINER_DOCKER_URI"
    echo "Apptainer image built at: $HPC_AGENT_DIR/$APPTAINER_IMAGE_NAME"

    ########################################
    # Download Ollama models
    ########################################

    echo "Starting ollama serve..."
    ollama serve &

    # Give the server a moment to come up
    sleep 3

    for model in $MODELS; do
      echo "Pulling Ollama model: $model"
      ollama pull "$model"
    done

    echo "All requested Ollama models have been downloaded."

    ########################################
    # Download SentenceTransformer all-MiniLM-L6-v2 into HF_HOME cache
    ########################################

    echo "Downloading SentenceTransformer all-MiniLM-L6-v2 into HF_HOME cache..."
    python - << "PY"
from sentence_transformers import SentenceTransformer

# This will download/cache the model into the HF_HOME/hub directory
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_ = model.encode(["test load"])
print("Downloaded and cached all-MiniLM-L6-v2.")
PY

    echo "\n========\nAll requested models have been downloaded."
  '

echo "Launch jupyter lab with ./launch.sh"