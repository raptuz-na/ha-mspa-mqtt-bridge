#!/usr/bin/env bash

# Environment variables from config
export MQTT_BROKER="${MQTT_BROKER}"
export MQTT_USER="${MQTT_USER}"
export MQTT_PASS="${MQTT_PASS}"
export APP_EMAIL="${APP_EMAIL}"
export APP_PASS="${APP_PASS}"
export APP_ID="${APP_ID}"
export APP_SECRET="${APP_SECRET}"
export POLL_INTERVAL="${POLL_INTERVAL}"

# Run Python script
python3 /app/mspa_mqtt_bridge.py
