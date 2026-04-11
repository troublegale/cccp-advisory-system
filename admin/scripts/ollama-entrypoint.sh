#!/bin/bash
set -e

# Start Ollama server in background
ollama serve &

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
until ollama list > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama is ready."

# Pull required models
echo "Pulling embedding model: bge-m3..."
ollama pull bge-m3

echo "Pulling LLM model: qwen2.5:7b..."
ollama pull qwen2.5:7b

echo "All models are ready."

# Keep the container alive
wait
