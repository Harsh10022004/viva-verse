#!/bin/bash

URL="https://viva-verse.onrender.com/health"

while true
do
    if curl -sf "$URL" > /dev/null; then
        echo "$(date): Health check OK"
    else
        echo "$(date): Health check FAILED"
    fi

    sleep 30
done
