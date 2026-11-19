#!/bin/sh
# Pousse (git push : le hook pre-push reconstruit ardoise_lib.js, le workflow publie sur GitHub Pages) puis déploie sur le serveur
# personnel (deploie.sh). S'arrête si le push échoue. Arguments : passés à git push.
# Alias conseillé, à refaire après un clone : git config alias.publie '!sh web/publie.sh'   puis   git publie
set -e
cd "$(dirname "$0")/.."
git push "$@"
web/deploie.sh
