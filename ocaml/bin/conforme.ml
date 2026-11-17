(* Les films conformes, comme le __main__ de python/Conforme.py. Depuis ocaml/ :
     dune exec bin/conforme.exe
   écrit ../imgs/conforme/film_{43m1m12m41,charge}_ocaml.mp4 (800 × 800, marges de 60 pixels), avec vérification.
   ffmpeg doit être dans le PATH, ou donné par FFMPEG. *)

open Ardoise

let () =
  let ffmpeg = Option.value (Sys.getenv_opt "FFMPEG") ~default:"ffmpeg" in
  let dossier = "../imgs/conforme" in
  if not (Sys.file_exists dossier) then Sys.mkdir dossier 0o755;
  List.iter
    (fun (entiers, nom, brin) ->
      let debut = Unix.gettimeofday () in
      let fichier = Filename.concat dossier (Printf.sprintf "film_%s_ocaml.mp4" nom) in
      let anomalies =
        Dessin.film_conforme ~ffmpeg ~hauteur:800 ~largeur:800 ~marge:60 ~largeur_brin:brin ~verifie:true
          (Tresses.tresse_de_entiers entiers) fichier
      in
      Printf.printf "%s : %d anomalies (%.1f s)\n%!" fichier (List.length anomalies) (Unix.gettimeofday () -. debut);
      List.iter (fun (a : Film_conforme.anomalie) -> Printf.printf "  lettre %d, image %d : %s\n" a.lettre a.image a.detail) anomalies)
    [ ([ 4; 3; -1; -1; 2; -4; 1 ], "43m1m12m41", 3.); ([ 1; -2; 1; -2; 1; -2; 3; -1; 2 ], "charge", 2.) ]
