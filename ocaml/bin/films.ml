(* Les films de la triangulation mobile, comme le __main__ de python/Triangulation.py. Depuis ocaml/ :
     dune exec bin/films.exe                         les deux tresses d'essai, dans ../imgs/
     dune exec bin/films.exe -- f.mp4 1 2 -1         une autre tresse
   ffmpeg doit être dans le PATH (celui de l'environnement conda braid-blackboard), ou donné par FFMPEG. *)

open Ardoise

let ffmpeg = Option.value (Sys.getenv_opt "FFMPEG") ~default:"ffmpeg"

let film entiers fichier =
  let debut = Unix.gettimeofday () in
  Dessin.film_triangule ~ffmpeg (Tresses.tresse_de_entiers entiers) fichier;
  Printf.printf "%s : %.1f s\n%!" fichier (Unix.gettimeofday () -. debut)

let () =
  match Array.to_list Sys.argv with
  | _ :: fichier :: (_ :: _ as lettres) -> film (List.map int_of_string lettres) fichier
  | [ _ ] ->
    film [ 4; 3; -1; -1; 2; -4; 1 ] "../imgs/film_triangule_43m1m12m41_ocaml.mp4";
    film [ 1; -2; 1; -2; 1; -2; 3; -1; 2 ] "../imgs/film_triangule_charge_ocaml.mp4"
  | _ -> prerr_endline "usage : films.exe [fichier.mp4 lettre lettre ...]"
