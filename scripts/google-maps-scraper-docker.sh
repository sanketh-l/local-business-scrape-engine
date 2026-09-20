#!/usr/bin/env bash
set -euo pipefail

workspace="${GITHUB_WORKSPACE:-$(pwd)}"

docker run --rm \
  -v gmaps-playwright-cache:/opt \
  -v "${workspace}:${workspace}" \
  -w "${workspace}" \
  gosom/google-maps-scraper "$@"
