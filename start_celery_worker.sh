#!/bin/bash

QUEUE_NAME=$1
CONCURRENCY=$2

#mkdir -p /opt/prometheus/

export LOCAL_DEBUGGER_RUN=False
export DJANGO_SETTINGS_MODULE=medical_mvp.settings

if [[ "$CONCURRENCY" =~ "," ]]; then
    # If concurrency is a range (for autoscaling)
    uv run celery -A medical_mvp worker -Q $QUEUE_NAME -l WARNING --autoscale=$CONCURRENCY -n ${QUEUE_NAME}@%h
else
    # For fixed concurrency
    uv run celery -A medical_mvp worker -Q $QUEUE_NAME -l WARNING --concurrency=$CONCURRENCY -n ${QUEUE_NAME}@%h
fi