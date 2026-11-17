(* Le film de l'escargot, comme le __main__ de python/Escargot.py. Depuis ocaml/ :
     dune exec bin/escargot.exe
   écrit ../imgs/escargot/film_ocaml.mp4. ffmpeg doit être dans le PATH, ou donné par FFMPEG. *)

open Ardoise

let () =
  let ffmpeg = Option.value (Sys.getenv_opt "FFMPEG") ~default:"ffmpeg" in
  let dossier = "../imgs/escargot" in
  if not (Sys.file_exists dossier) then Sys.mkdir dossier 0o755;
  let debut = Unix.gettimeofday () in
  Dessin.film_escargot ~ffmpeg (Escargot.cree ()) (Filename.concat dossier "film_ocaml.mp4");
  Printf.printf "escargot fait (%.1f s)\n%!" (Unix.gettimeofday () -. debut)
