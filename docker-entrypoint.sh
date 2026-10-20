#!/bin/sh
set -eu

scrapyd &
SCRAPYD_PID=$!

cleanup() {
    kill "$SCRAPYD_PID" 2>/dev/null || true
    wait "$SCRAPYD_PID" 2>/dev/null || true
}

trap cleanup INT TERM

echo "Waiting for Scrapyd..."

attempt=0
until curl -fsS http://localhost:6800/daemonstatus.json >/dev/null; do
    attempt=$((attempt + 1))

    if [ "$attempt" -ge 30 ]; then
        echo "Scrapyd failed to start."
        exit 1
    fi

    sleep 1
done

echo "Deploying project..."
scrapyd-deploy

echo "Scrapyd is ready on port 6800. Run your Scrapy spiders using the Scrapyd API."
wait "$SCRAPYD_PID"
