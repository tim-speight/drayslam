#!/bin/bash

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo
echo "=========================================="
echo "DraySLAM"
echo "=========================================="
echo

cd "$BASE_DIR"

if [ ! -f ".env" ]; then
    echo "ERROR: .env not found"
    exit 1
fi

echo "Loading environment"

set -a
source .env
set +a

echo
echo "Configuration"
echo "-------------"

echo "DSLAM_IP      : ${DSLAM_IP}"
echo "INFLUX_ORG    : ${INFLUX_ORG}"
echo "INFLUX_BUCKET : ${INFLUX_BUCKET}"

echo
echo "Starting..."

exec "$BASE_DIR/bin/python" "$BASE_DIR/main.py"
