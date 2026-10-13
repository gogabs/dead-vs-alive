#!/bin/bash
# Empacota o jogo com a biblioteca Python do SDK e instala no console.
#
#   ./instalar.sh [host-ssh] [pasta-do-sdk]
#   padrão: r36s e ../r36s-a11y-sdk (clone de github.com/gogabs/r36s-a11y-sdk)
#
# Não reinicia nada: a galeria percebe o jogo novo sozinha. Com o jogo aberto,
# não instala, porque ele carrega os sons sob demanda da pasta instalada.
set -euo pipefail
HOST=${1:-r36s}
HERE=$(cd "$(dirname "$0")" && pwd)
SDK=${2:-$HERE/../r36s-a11y-sdk}
SDK_PY="$HERE/r36s_a11y"
[ -d "$SDK_PY" ] || SDK_PY="$SDK/python/r36s_a11y"
[ -d "$SDK_PY" ] || { echo "SDK não encontrado."; exit 1; }

if ssh "$HOST" 'for p in /proc/[0-9]*; do readlink "$p/cwd"; done 2>/dev/null | grep -q "^/opt/a11y/games/dead-vs-alive"'; then
  echo "O Dead vs. Alive está aberto no console. Feche o jogo e rode de novo."
  exit 1
fi

PKG=$(mktemp -d)
trap 'rm -rf "$PKG"' EXIT
mkdir -p "$PKG/dead-vs-alive"
cp -r "$HERE/game.json" "$HERE/main.py" "$HERE/dva" "$HERE/graphics" "$HERE/sounds" "$SDK_PY" "$PKG/dead-vs-alive/"
find "$PKG" -name __pycache__ -prune -exec rm -rf {} +

tar -C "$PKG" -czf - dead-vs-alive | ssh "$HOST" '
  set -e; cd /opt/a11y/games
  rm -rf .dead-vs-alive.novo && mkdir .dead-vs-alive.novo
  tar -xzf - -C .dead-vs-alive.novo
  rm -rf dead-vs-alive && mv .dead-vs-alive.novo/dead-vs-alive . && rmdir .dead-vs-alive.novo
  echo "instalado: $(ls dead-vs-alive/sounds | wc -l) sons"; df -h /opt/a11y | tail -1'
