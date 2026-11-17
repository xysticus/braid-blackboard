(* Exemple qui NE COMPILE PAS, exprès : une tresse passée là où l'on attend un mot de F_n.
   Pas de fichier dune dans ce répertoire : dune ne le construit pas. Pour voir l'erreur, depuis ocaml/ :
     dune build && ocamlfind ocamlc -c -I _build/default/lib/.ardoise.objs/byte -open Ardoise exemples/confusion.ml *)

open Tresses

let t : tresse = tresse_de_entiers [ 1; -2 ]
let _ = Reduit.simplifie t
