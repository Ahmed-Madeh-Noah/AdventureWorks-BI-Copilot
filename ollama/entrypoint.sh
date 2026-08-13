#!/bin/bash

ollama serve &
pid=$!

OLLAMA_MODELS_DIR="/usr/share/ollama/.ollama/models"
MODEL_NAME="${MODEL%%:*}"
MODEL_TAG="${MODEL#*:}"
MODEL_FILE="$OLLAMA_MODELS_DIR/manifests/registry.ollama.ai/library/$MODEL_NAME/$MODEL_TAG"

if [ ! -f "$MODEL_FILE" ]; then
    
    OLLAMASTATUS=1
    ERRCODE=1
    i=0
    
    until [[ "$OLLAMASTATUS" -eq 0 && "$ERRCODE" -eq 0 ]] || [[ "$i" -ge 120 ]]; do
        ((i++))
        ollama list > /dev/null 2>&1
        ERRCODE=$?
        if [[ "$ERRCODE" -eq 0 ]]; then
            OLLAMASTATUS=0
        else
            OLLAMASTATUS=1
        fi
        sleep 1
    done
    
    if [ "$OLLAMASTATUS" -ne 0 ] || [ "$ERRCODE" -ne 0 ]; then
        echo "Ollama took more than 120 seconds to start up"
        exit 1
    fi
    
    echo "Downloading $MODEL..."
    ollama pull $MODEL
fi

wait $pid