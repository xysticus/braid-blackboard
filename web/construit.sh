#!/bin/sh
# Compile la bibliothèque OCaml en JavaScript (web/ardoise_lib.js). À lancer depuis n'importe où ; demande le switch
# opam de ocaml/ (js_of_ocaml) : eval $(opam env --switch=ocaml) si besoin.
set -e
cd "$(dirname "$0")/../ocaml"
command -v dune >/dev/null 2>&1 || eval "$(opam env --switch=.)"
dune build --profile release web/ardoise_web.bc.js
cp -f _build/default/web/ardoise_web.bc.js ../web/ardoise_lib.js
chmod u+w ../web/ardoise_lib.js
echo "web/ardoise_lib.js : $(wc -c < ../web/ardoise_lib.js) octets"
