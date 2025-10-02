#!/bin/sh

QUEUE_NAME=${1:-default}
CONCURRENCY=${2:-2}

export LOCAL_DEBUGGER_RUN=False
export DJANGO_SETTINGS_MODULE=medical_mvp.settings

if echo "$CONCURRENCY" | grep -q ","; then
    exec celery -A medical_mvp worker \
        -Q "$QUEUE_NAME" \
        -l WARNING \
        --autoscale="$CONCURRENCY" \
        -n "${QUEUE_NAME}@%h"
else
    exec celery -A medical_mvp worker \
        -Q "$QUEUE_NAME" \
        -l WARNING \
        --concurrency="$CONCURRENCY" \
        -n "${QUEUE_NAME}@%h"
fi