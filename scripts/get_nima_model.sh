#!/usr/bin/env bash
# Descarca modelul NIMA (ONNX) la models/nima.onnx.
# Foloseste un URL valid din variabila NIMA_URL.
#
#   NIMA_URL="https://.../nima.onnx" ./scripts/get_nima_model.sh
#
# Daca nu pui modelul, scorer-ul cade automat pe euristica (vezi models/README.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/models/nima.onnx"
mkdir -p "$ROOT/models"

URL="${NIMA_URL:-}"
if [ -z "$URL" ]; then
  echo "Eroare: seteaza NIMA_URL spre un model NIMA aesthetic ONNX"
  echo "        (input 224x224, output 10 clase)."
  echo "Exemplu: NIMA_URL=https://exemplu/nima.onnx $0"
  exit 1
fi

echo "Descarc modelul: $URL"
curl -fL "$URL" -o "$DEST"
echo "Salvat la: $DEST"
echo "Reporneste API-ul: sudo systemctl restart photobackup-api"
