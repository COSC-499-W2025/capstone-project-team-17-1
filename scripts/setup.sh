#!/usr/bin/env bash
# Install LaTeX dependencies required for PDF resume export.
# Supports: macOS (Homebrew) and Linux (apt / dnf).
set -euo pipefail

OS="$(uname -s)"

# ── macOS ────────────────────────────────────────────────────────────────────
if [[ "$OS" == "Darwin" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install it from https://brew.sh first."
    exit 1
  fi
  echo "macOS detected — installing tectonic via Homebrew..."
  brew install tectonic
  echo "Done. 'tectonic' is now available for PDF export."

# ── Linux (Debian / Ubuntu) ──────────────────────────────────────────────────
elif [[ "$OS" == "Linux" ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "Debian/Ubuntu detected — installing texlive-xetex via apt..."
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
      texlive-xetex \
      texlive-fonts-recommended \
      texlive-latex-extra
    echo "Done. 'xelatex' is now available for PDF export."

  elif command -v dnf >/dev/null 2>&1; then
    echo "Fedora/RHEL detected — installing texlive-xetex via dnf..."
    sudo dnf install -y texlive-xetex texlive-collection-fontsrecommended
    echo "Done. 'xelatex' is now available for PDF export."

  else
    echo "Unsupported Linux package manager."
    echo "Please install xelatex manually (e.g. texlive-xetex) and re-run."
    exit 1
  fi

else
  echo "Unsupported OS: $OS"
  echo "For Windows, run: scripts/setup.ps1"
  exit 1
fi
