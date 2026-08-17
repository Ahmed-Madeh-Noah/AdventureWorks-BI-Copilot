#!/bin/bash

ollama serve &
pid=$!

MODEL_NAME="${MODEL%%:*}"
MODEL_TAG="${MODEL#*:}"
OLLAMA_MODELS_DIR="/usr/share/ollama/.ollama/models/manifests/registry.ollama.ai/library"
MODEL_FILE="$OLLAMA_MODELS_DIR/$MODEL_NAME/$MODEL_TAG"
if [ ! -f "$MODEL_FILE" ]; then
    ERRCODE=1
    until [[ "$ERRCODE" -eq 0 ]]; do
        sleep 1
        ollama list > /dev/null 2>&1
        ERRCODE=$?
    done
    
    echo "Downloading $MODEL..."
    mkdir --parents "$OLLAMA_MODELS_DIR"
    ollama pull $MODEL
fi

wait $pid