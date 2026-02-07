#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This setup script currently supports macOS (Homebrew)."
  echo "Install pandoc and tectonic manually on your OS."
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Install it from https://brew.sh first."
  exit 1
fi

echo "Installing PDF dependencies: pandoc, tectonic"
brew install pandoc tectonic

echo "Done. You can now export PDFs from the CLI."
