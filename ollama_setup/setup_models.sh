#!/bin/bash

if [ -z "$MODELS" ]; then
    exit 0
fi

IFS=',' read -ra MODEL_ARRAY <<< "$MODELS"
for model in "${MODEL_ARRAY[@]}"; do
    if [ -n "$model" ]; then
        ollama pull "$model"
    fi
done