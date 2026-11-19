#!/bin/sh
# Déploie la page sur un serveur personnel : construit ardoise_lib.js (construit.sh), puis copie les fichiers de la page par rsync.
#   web/deploie.sh        compile et copie
#   web/deploie.sh -n     essai à blanc : montre ce qui serait copié, n'écrit rien sur le serveur
# La cible vient de la variable CIBLE (utilisateur@machine:dossier/) ou du fichier web/deploie.conf, local et non suivi par
# git (lignes CIBLE="..." et, au choix, URL="..." pour l'adresse affichée à la fin). Pas de sudo.
set -e
cd "$(dirname "$0")"
[ -f deploie.conf ] && . ./deploie.conf
if [ -z "$CIBLE" ]; then
  echo "CIBLE non définie : l'écrire dans web/deploie.conf (CIBLE=\"utilisateur@machine:dossier/\") ou dans l'environnement" >&2
  exit 1
fi
./construit.sh

# seulement les fichiers de la page, dans un dossier à part : --delete retire du serveur ce qui n'y est plus
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp index.html ardoise.css ardoise.js travail.js ardoise_lib.js favicon.svg "$STAGE/"

HOTE="${CIBLE%%:*}"
DOSSIER="${CIBLE#*:}"
if [ "$1" != "-n" ]; then ssh "$HOTE" "mkdir -p '$DOSSIER'"; fi
rsync -av --delete --chmod=D755,F644 "$@" "$STAGE/" "$CIBLE"
[ -n "$URL" ] && echo "page : $URL"
true
