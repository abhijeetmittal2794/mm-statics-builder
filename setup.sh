#!/usr/bin/env bash
# One-shot setup: venv, deps, fonts, env template.
# Run: bash setup.sh
set -euo pipefail

cd "$(dirname "$0")"

echo "▸ Creating Python venv (.venv)…"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "▸ Upgrading pip…"
python -m pip install --upgrade pip >/dev/null

echo "▸ Installing dependencies (this may take a minute)…"
pip install -r requirements.txt

echo "▸ Installing Inter fonts (free, closest to MM headline/body stack)…"
FONTS_DIR="src/fonts"
mkdir -p "$FONTS_DIR"

NEEDED=(Inter-Black.ttf Inter-Bold.ttf Inter-Medium.ttf Inter-Regular.ttf)
missing=0
for f in "${NEEDED[@]}"; do
  if [ ! -s "$FONTS_DIR/$f" ] || ! file "$FONTS_DIR/$f" | grep -q "TrueType"; then
    missing=1
  fi
done

if [ "$missing" = "1" ]; then
  TMPDIR="$(mktemp -d)"
  echo "   ↓ downloading Inter v4.1 release zip…"
  curl -sSL "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip" -o "$TMPDIR/inter.zip"
  unzip -q -o "$TMPDIR/inter.zip" -d "$TMPDIR/extract"
  for f in "${NEEDED[@]}"; do
    cp "$TMPDIR/extract/extras/ttf/$f" "$FONTS_DIR/$f"
    echo "   ✓ $f"
  done
  rm -rf "$TMPDIR"
else
  echo "   ✓ all Inter TTFs already present"
fi

if [ ! -f .env ]; then
  echo "▸ Creating .env from .env.example (fill in your API keys next)…"
  cp .env.example .env
fi

echo ""
echo "✅ Setup complete."
echo ""
echo "Next steps:"
echo "  1. Open .env and add your ANTHROPIC_API_KEY and GOOGLE_API_KEY"
echo "  2. source .venv/bin/activate"
echo "  3. python cli.py demo"
