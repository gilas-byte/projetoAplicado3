#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../data/raw"

# Gera hashes na primeira execução; verifica nas seguintes.
if [[ -f hashes.sha256 ]]; then
  sha256sum -c hashes.sha256
else
  sha256sum microdados_enem_20*.zip > hashes.sha256
  echo "hashes.sha256 gerado com $(wc -l < hashes.sha256) arquivos"
fi
