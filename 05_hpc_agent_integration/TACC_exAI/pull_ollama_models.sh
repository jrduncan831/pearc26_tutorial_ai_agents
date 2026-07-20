#!/bin/bash

# List of models to pull
models=("qwen3:1.7b" "qwen3:4b" "qwen3-coder:30b" "qwen3:30b")

# Loop through and pull each one
for model in "${models[@]}"; do
    echo "Pulling $model ..."
    ollama pull "$model"
done

echo "All models pulled successfully."
