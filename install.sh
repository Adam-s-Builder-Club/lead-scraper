#!/usr/bin/env bash
# One-time setup for the no-key (gosom) engine. Needs Go installed.
# The Places API engine needs no install — just set GOOGLE_MAPS_API_KEY.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HERE/bin"

if [ -x "$BIN_DIR/google-maps-scraper" ]; then
  echo "✓ gosom scraper already installed at $BIN_DIR/google-maps-scraper"
  exit 0
fi

if ! command -v go >/dev/null 2>&1; then
  cat <<'MSG'
Go is not installed (needed for the free, no-key engine).

  - macOS:   brew install go
  - other:   https://go.dev/doc/install

Or skip Go entirely and use the Places API engine instead:
  1. Get a free key (see README.md, ~5 min).
  2. export GOOGLE_MAPS_API_KEY=your_key
Then this skill works with no Go install.
MSG
  exit 1
fi

echo "Installing gosom/google-maps-scraper (compiles from source, ~1-2 min)..."
mkdir -p "$BIN_DIR"
GOBIN="$BIN_DIR" go install github.com/gosom/google-maps-scraper@latest
echo "✓ installed -> $BIN_DIR/google-maps-scraper"
echo "Try:  python3 scripts/leads.py --query \"coffee shops in Austin TX\""
